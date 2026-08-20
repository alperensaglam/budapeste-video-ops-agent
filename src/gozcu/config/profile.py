"""Donanım profili sistemi — tek kod tabanı, üç ortam.

Ekibin şu an GPU'su yok; yarışma donanımı (H200) ileride gelebilir. Bu modül, aynı
kodun üç ortamda da çalışmasını sağlar::

    cpu-dev     Herkesin dizüstü. VLM = kaset replay. Algı = ONNX CPU, düşük fps.
    colab-t4    Kaggle 2xT4 (ücretsiz). VLM = Qwen3-VL-4B/8B AWQ, fp16.
    h200-prod   Resmi H200 altyapısı. VLM = Slot B'deki ``vlm`` hizmeti (BF16).

Kullanım::

    from gozcu.config import load_profile
    p = load_profile()              # GOZCU_PROFILE ortam değişkeni veya cpu-dev
    p = load_profile("colab-t4")    # açıkça
"""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field

from gozcu.contracts.common import GozcuModel

#: Repo kökü — config/ ve data/ buradan çözülür.
REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILE_DIR = REPO_ROOT / "config" / "profiles"

ENV_VAR = "GOZCU_PROFILE"
DEFAULT_PROFILE = "cpu-dev"


class VLMBackend(StrEnum):
    CASSETTE = "cassette"  # kayıttan oynatma (CPU, deterministik, testler)
    VLLM = "vllm"  # yerel veya resmi OpenAI-uyumlu vLLM endpoint'i
    LLAMACPP = "llamacpp"  # CPU'da gerçek küçük model (GGUF)
    SCRIPTED = "scripted"  # birim testlerde sabit yanıt


class SamplingConfig(GozcuModel):
    """L0 uyarlanabilir örnekleme bütçesi."""

    base_fps: float = Field(default=1.0, gt=0, description="Taban örnekleme hızı")
    max_frames_per_segment: int = Field(default=8, gt=0)
    max_frames_total: int = Field(default=64, gt=0, description="VLM'e giden toplam kare tavanı")
    zoom_fps: float = Field(default=5.0, gt=0, description="Kaba-ince döngüde yakınlaşma hızı")
    segment_seconds: float = Field(default=10.0, gt=0)
    adaptive: bool = Field(default=True, description="False = sabit örnekleme (ablation için)")


class VLMConfig(GozcuModel):
    backend: VLMBackend = VLMBackend.CASSETTE
    model: str = Field(default="cassette", description="Model kimliği veya HF repo adı")
    base_url: str = Field(
        default="http://localhost:8000/v1", description="OpenAI-uyumlu vLLM endpoint'i"
    )
    base_url_env: str | None = Field(
        default=None,
        description="Verildiyse endpoint bu ortam değişkeninden okunur (sırlar YAML'a girmez)",
    )
    api_key: str = Field(
        default="EMPTY",
        description="Yerel vLLM varsayılanı; resmi anahtar için api_key_env kullanılır",
    )
    api_key_env: str | None = Field(
        default=None,
        description="Takıma özel erişim anahtarını taşıyan ortam değişkeninin adı",
    )
    max_model_len: int = Field(default=32768, gt=0)
    dtype: str = Field(default="auto", description="auto | half (T4) | bfloat16 | fp8 (H200)")
    temperature: float = Field(default=0.0, ge=0.0)
    max_tokens: int = Field(default=2048, gt=0)
    guided_json: bool = Field(
        default=True, description="vLLM xgrammar ile şema zorlaması (Geçerli JSON = 1.00)"
    )
    enable_prefix_caching: bool = Field(
        default=True, description="Uzun video bağlamı prefix'i turlar arası yeniden kullanılır"
    )
    request_timeout_s: float = Field(default=120.0, gt=0)
    max_concurrency: int = Field(default=2, ge=1, description="Eşzamanlı VLM çağrısı tavanı")

    def resolved_base_url(self) -> str:
        """Endpoint'i güvenli biçimde çöz; gerekli ortam değişkeni yoksa erken hata ver."""
        if self.base_url_env:
            value = os.environ.get(self.base_url_env, "").strip()
            if not value:
                raise RuntimeError(
                    f"VLM endpoint ortam değişkeni tanımlı değil: {self.base_url_env}"
                )
            return value.rstrip("/")
        if not self.base_url.strip():
            raise RuntimeError("VLM endpoint'i boş")
        return self.base_url.rstrip("/")

    def resolved_api_key(self) -> str:
        """API anahtarını YAML'a yazmadan ortamdan çöz."""
        if self.api_key_env:
            value = os.environ.get(self.api_key_env, "").strip()
            if not value:
                raise RuntimeError(
                    f"VLM erişim anahtarı ortam değişkeni tanımlı değil: {self.api_key_env}"
                )
            return value
        return self.api_key


class PlannerConfig(GozcuModel):
    """Ajanın planlama/yönlendirme modeli. Küçük ve hızlı olmalı."""

    backend: VLMBackend = VLMBackend.CASSETTE
    model: str = "cassette"
    base_url: str = "http://localhost:8001/v1"
    max_tokens: int = Field(default=1024, gt=0)


class PerceptionConfig(GozcuModel):
    """L1 algı katmanı ayarları."""

    device: str = Field(default="cpu", description="cpu | cuda")
    detector: str = Field(default="rtdetrv2_r18", description="Apache-2.0 — YOLO/AGPL DEĞİL")
    detector_conf: float = Field(default=0.35, ge=0.0, le=1.0)
    enable_pose: bool = True
    enable_asr: bool = True
    asr_model: str = Field(default="small", description="faster-whisper boyutu")
    asr_compute_type: str = Field(default="int8", description="CPU'da int8, GPU'da float16")
    enable_audio_events: bool = True
    max_video_seconds: float = Field(
        default=120.0, gt=0, description="cpu-dev'de uzun videoyu kesip geliştirmeyi hızlandırır"
    )


class AgentConfig(GozcuModel):
    """L4 ajan davranış eşikleri. Ablation çalışmaları bunları değiştirir."""

    max_turns: int = Field(default=12, ge=1)
    max_tool_calls_per_turn: int = Field(default=6, ge=1)
    enable_verifier: bool = Field(default=True, description="False = ablation koşusu")
    support_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Bu skorun altındaki olay belirsiz sayılır"
    )
    enable_zoom_loop: bool = Field(default=True, description="Kaba-ince temellendirme döngüsü")
    max_zoom_iterations: int = Field(default=2, ge=0)
    enable_clarifying_questions: bool = True
    enable_episodic_memory: bool = True
    enable_sop_rag: bool = True
    require_confirmation_for_irreversible: bool = True
    tool_retry_max: int = Field(default=2, ge=0)
    tool_backoff_base_ms: float = Field(default=200.0, gt=0)


class FaultInjectionConfig(GozcuModel):
    """Kaos testi ayarları — Faz 3 'hata kurtarma oranı' KPI'ının kaynağı.

    Üretimde/demoda kapalıdır; eval koşularında açılır.
    """

    enabled: bool = False
    failure_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    seed: int = 1337
    kinds: list[str] = Field(
        default_factory=lambda: ["timeout", "unavailable", "rate_limit", "invalid_response"]
    )


class Profile(GozcuModel):
    """Bir donanım/ortam profilinin tamamı."""

    name: str
    description: str = ""
    vlm: VLMConfig = Field(default_factory=VLMConfig)
    planner: PlannerConfig = Field(default_factory=PlannerConfig)
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)
    perception: PerceptionConfig = Field(default_factory=PerceptionConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    faults: FaultInjectionConfig = Field(default_factory=FaultInjectionConfig)

    cassette_dir: str = Field(default="data/cassettes")
    cassette_mode: str = Field(
        default="replay",
        description="replay (CPU) | record (GPU'da kaset üret) | passthrough (kaset yok)",
    )

    @property
    def cassette_path(self) -> Path:
        p = Path(self.cassette_dir)
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def is_gpu(self) -> bool:
        return self.perception.device.startswith("cuda")


def profile_path(name: str) -> Path:
    return PROFILE_DIR / f"{name}.yaml"


def available_profiles() -> list[str]:
    if not PROFILE_DIR.is_dir():
        return []
    return sorted(p.stem for p in PROFILE_DIR.glob("*.yaml"))


@lru_cache(maxsize=8)
def load_profile(name: str | None = None) -> Profile:
    """Profili yükle. Sıra: argüman > GOZCU_PROFILE ortam değişkeni > cpu-dev.

    Bilinmeyen bir alan varsa Pydantic hata verir (``extra="forbid"``) — profil
    dosyasındaki yazım hataları sessizce yutulmaz.
    """
    resolved = name or os.environ.get(ENV_VAR) or DEFAULT_PROFILE
    path = profile_path(resolved)
    if not path.is_file():
        raise FileNotFoundError(
            f"profil bulunamadı: {resolved} ({path}). Mevcut: {available_profiles()}"
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw.setdefault("name", resolved)
    return Profile.model_validate(raw)
