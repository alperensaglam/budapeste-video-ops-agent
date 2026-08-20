"""VLM/LLM istemci sözleşmesi ve kaset (cassette) formatı — DONDURULMUŞ SINIR #2.

NEDEN VAR: Ekibin şu an GPU'su yok. Emre Kaggle'da gerçek model çıktılarını KASET
olarak kaydeder; Alperen, Hasan ve İbrahim bu kasetlerle CPU'da, deterministik ve
saniyeler içinde çalışır. GPU darboğazı 4 kişiyi değil 1 kişiyi bağlar.

Aynı arayüz üç profilde de geçerlidir:
    cpu-dev    -> CassetteVLM (kayıttan oynatma) veya küçük GGUF model
    colab-t4   -> vLLM @ localhost, Qwen3-VL-4B/8B AWQ
    h200-prod  -> vLLM @ localhost, Qwen3-VL-32B FP8

Kaset anahtarı, isteğin İÇERİK HASH'idir; böylece aynı istek her zaman aynı yanıtı
alır (testler deterministik) ve gerçek çalıştırmalarda cache görevi görür.
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from gozcu.contracts.common import GozcuModel, Seconds


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FrameRef(GozcuModel):
    """VLM'e gönderilen tek kare.

    ``data_b64`` kasete YAZILMAZ (dosya şişer); yerine ``sha256`` tutulur. Kaset
    eşleştirmesi hash üzerinden yapılır, görüntünün kendisi diskte ayrı durur.
    """

    t: Seconds = Field(description="Karenin video içindeki zamanı — prompt'a da yazılır")
    sha256: str = Field(min_length=64, max_length=64)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    path: str | None = Field(default=None, description="Diskteki yol (varsa)")
    data_b64: str | None = Field(default=None, exclude=True, repr=False)


class VLMMessage(GozcuModel):
    """Çok-ortamlı mesaj: metin + kareler."""

    role: MessageRole
    text: str = ""
    frames: list[FrameRef] = Field(default_factory=list)


class VLMRequest(GozcuModel):
    """VLM'e giden istek. Hash'i kaset anahtarıdır."""

    messages: list[VLMMessage]
    model: str = Field(default="", description="Boşsa profil varsayılanı kullanılır")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)
    #: Pydantic model_json_schema çıktısı. vLLM guided_json (xgrammar) ile
    #: geçerli JSON GARANTİ edilir — "Geçerli JSON Oranı = 1.00" KPI'ının dayanağı.
    json_schema: dict[str, Any] | None = None
    seed: int | None = Field(default=0, description="Tekrar üretilebilirlik için")
    prompt_id: str = Field(
        default="", description="Prompt kütüphanesindeki sürüm, ör. segment_analysis@v2"
    )

    def cache_key(self) -> str:
        """İçerik hash'i. Kaset anahtarı ve prefix-cache dostu cache anahtarı.

        Yalnızca yanıtı ETKİLEYEN alanlar hash'e girer; ``path`` gibi ortam-bağımlı
        alanlar girmez, aksi halde kaset başka makinede tutmaz.
        """
        h = hashlib.sha256()
        h.update(f"{self.model}|{self.temperature}|{self.max_tokens}|{self.seed}".encode())
        h.update(f"|{self.prompt_id}".encode())
        if self.json_schema is not None:
            h.update(repr(sorted(self.json_schema.items())).encode())
        for m in self.messages:
            h.update(f"|{m.role.value}|{m.text}".encode())
            for fr in m.frames:
                h.update(f"|{fr.sha256}|{fr.t}".encode())
        return h.hexdigest()[:32]


class VLMUsage(GozcuModel):
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    ttft_ms: float | None = Field(default=None, description="Time to first token")

    @property
    def tokens_per_second(self) -> float:
        if self.latency_ms <= 0:
            return 0.0
        return round(self.completion_tokens / (self.latency_ms / 1000.0), 2)


class VLMResponse(GozcuModel):
    text: str
    model: str = ""
    usage: VLMUsage = Field(default_factory=VLMUsage)
    finish_reason: str = "stop"
    from_cache: bool = Field(default=False, description="Kasetten mi geldi")
    schema_valid: bool | None = Field(
        default=None, description="json_schema istendiyse doğrulama sonucu"
    )
    repair_attempts: int = Field(
        default=0, ge=0, description="JSON onarım turu sayısı — 0 olması hedeftir"
    )


class CassetteEntry(GozcuModel):
    """Diske yazılan tek kayıt. ``data/cassettes/<name>.jsonl`` içinde satır başına bir tane."""

    key: str = Field(description="VLMRequest.cache_key()")
    prompt_id: str = ""
    model: str = ""
    request_preview: str = Field(
        default="", max_length=400, description="İnsan gözüyle bakmak için ilk mesajın başı"
    )
    n_frames: int = Field(default=0, ge=0)
    response: VLMResponse
    recorded_at: str = Field(default="", description="ISO-8601 zaman damgası")
    recorded_by: str = Field(default="", description="Kaseti üreten kişi/ortam (izlenebilirlik)")


@runtime_checkable
class VLMClient(Protocol):
    """Tüm VLM istemcilerinin uyduğu arayüz.

    Uygulamalar: ``CassetteVLM`` (CPU), ``VLLMClient`` (Colab/H200), ``ScriptedVLM`` (test).
    Ajan ve algı katmanları BU TİPE bağımlıdır, somut sınıfa değil.
    """

    async def generate(self, request: VLMRequest) -> VLMResponse:  # pragma: no cover
        ...

    @property
    def model_name(self) -> str:  # pragma: no cover
        ...
