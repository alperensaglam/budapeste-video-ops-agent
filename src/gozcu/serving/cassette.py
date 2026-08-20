"""Kaset (cassette) altyapısı — kayıt / oynatma.

PROBLEM: Ekibin GPU'su yok, ama dört kişi de paralel çalışmak zorunda.

ÇÖZÜM: Emre Kaggle'ın ücretsiz T4'ünde gerçek VLM çıktılarını KASETE kaydeder
(``cassette_mode: record``); Alperen, Hasan ve İbrahim CPU'da aynı kasetten
oynatarak (``replay``) çalışır. Sonuç:

* testler deterministik ve milisaniyeler içinde koşar,
* ajan/UI/eval geliştirmesi GPU beklemez,
* gerçek koşularda da cache görevi görür (``rtf`` düşer, demo hızlanır).

Kaset formatı: JSONL — satır başına bir :class:`CassetteEntry`. Git dostu
(satır bazlı diff), insan okunabilir, birleştirmesi kolay.

Eşleştirme anahtarı :meth:`VLMRequest.cache_key` — isteğin içerik hash'idir.
Aynı prompt + aynı kareler + aynı şema = aynı anahtar = aynı yanıt.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from gozcu.contracts.vlm import (
    CassetteEntry,
    VLMRequest,
    VLMResponse,
    VLMUsage,
)


class CassetteMissError(KeyError):
    """Replay modunda kasette bulunamayan istek.

    Bu hata BİLEREK gürültülüdür: sessizce boş yanıt dönmek, testlerin yalancı
    yeşil vermesine yol açar. Mesaj, kaseti nasıl üreteceğini söyler.
    """

    def __init__(self, key: str, prompt_id: str, cassette: Path) -> None:
        self.key = key
        super().__init__(
            f"Kaset kaydı yok: key={key} prompt_id={prompt_id!r} dosya={cassette}\n"
            f"Çözüm: colab-t4 profilinde (Kaggle) şu komutu koşup kaseti repo'ya ekleyin:\n"
            f"  GOZCU_PROFILE=colab-t4 python tasks.py record-cassettes"
        )


class Cassette:
    """Tek bir JSONL kaset dosyasının okuma/yazma sarmalayıcısı.

    Bellek içi bir sözlük tutar; ``record`` modunda ek olarak diske append eder.
    """

    def __init__(self, path: Path, mode: str = "replay") -> None:
        if mode not in {"replay", "record", "passthrough"}:
            raise ValueError(f"geçersiz kaset modu: {mode}")
        self.path = path
        self.mode = mode
        self._entries: dict[str, CassetteEntry] = {}
        if mode in {"replay", "record"} and path.is_file():
            self.load()

    # ── Okuma ────────────────────────────────────────────────────────

    def load(self) -> int:
        """Kaseti diskten yükle. Bozuk satırları atlar ama sayar."""
        self._entries.clear()
        bad = 0
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    entry = CassetteEntry.model_validate_json(line)
                except Exception:
                    bad += 1
                    continue
                self._entries[entry.key] = entry
        if bad:
            print(f"[kaset] uyarı: {self.path.name} içinde {bad} bozuk satır atlandı")
        return len(self._entries)

    def get(self, request: VLMRequest) -> VLMResponse | None:
        entry = self._entries.get(request.cache_key())
        if entry is None:
            return None
        resp = entry.response.model_copy(deep=True)
        resp.from_cache = True
        return resp

    def __contains__(self, request: VLMRequest) -> bool:
        return request.cache_key() in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[CassetteEntry]:
        return iter(self._entries.values())

    # ── Yazma ────────────────────────────────────────────────────────

    def put(self, request: VLMRequest, response: VLMResponse) -> CassetteEntry:
        """Yeni kayıt ekle ve diske append et (record modu)."""
        first_text = next((m.text for m in request.messages if m.text), "")
        entry = CassetteEntry(
            key=request.cache_key(),
            prompt_id=request.prompt_id,
            model=response.model or request.model,
            request_preview=first_text[:400],
            n_frames=sum(len(m.frames) for m in request.messages),
            response=response,
            recorded_at=datetime.now(UTC).isoformat(timespec="seconds"),
            recorded_by=os.environ.get("GOZCU_RECORDER", os.environ.get("USER", "unknown")),
        )
        self._entries[entry.key] = entry
        if self.mode == "record":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(entry.model_dump_json() + "\n")
        return entry

    def compact(self) -> int:
        """Yinelenen anahtarları temizleyip dosyayı yeniden yaz.

        Kaset zamanla şişer (aynı prompt tekrar kaydedilir). Bunu haftalık
        çalıştırın; git diff'i temiz kalır.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(self._entries.values(), key=lambda e: (e.prompt_id, e.key))
        with self.path.open("w", encoding="utf-8") as fh:
            for entry in ordered:
                fh.write(entry.model_dump_json() + "\n")
        return len(ordered)

    def stats(self) -> dict[str, int]:
        """Kasetin içeriği — hangi prompt'tan kaç kayıt var."""
        by_prompt: dict[str, int] = {}
        for e in self._entries.values():
            by_prompt[e.prompt_id or "(isimsiz)"] = by_prompt.get(e.prompt_id or "(isimsiz)", 0) + 1
        return dict(sorted(by_prompt.items()))


class CassetteVLM:
    """Kasetten oynatan :class:`~gozcu.contracts.vlm.VLMClient` uygulaması.

    ``cpu-dev`` profilinin varsayılan VLM'i. Gerçek modelin yerine geçer ve
    :class:`~gozcu.contracts.vlm.VLMClient` protokolünü birebir karşılar; ajan
    kodu hangi arkada çalıştığını bilmez.
    """

    def __init__(self, cassette: Cassette, model_name: str = "cassette") -> None:
        self._cassette = cassette
        self._model_name = model_name
        self.hits = 0
        self.misses = 0

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total, 4) if total else 0.0

    async def generate(self, request: VLMRequest) -> VLMResponse:
        cached = self._cassette.get(request)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        raise CassetteMissError(request.cache_key(), request.prompt_id, self._cassette.path)


class RecordingVLM:
    """Gerçek bir VLM istemcisini sarmalayıp her yanıtı kasete yazar.

    Emre bunu ``colab-t4`` profilinde kullanır::

        inner = VLLMClient(profile.vlm)
        client = RecordingVLM(inner, Cassette(path, mode="record"))

    Kaset zaten doluysa modeli hiç çağırmaz → tekrar koşular ücretsiz, GPU kotası
    boşa gitmez (Kaggle'da haftalık 30 saat sınırlı).
    """

    def __init__(self, inner: object, cassette: Cassette, reuse_existing: bool = True) -> None:
        self._inner = inner
        self._cassette = cassette
        self._reuse = reuse_existing
        self.recorded = 0
        self.reused = 0

    @property
    def model_name(self) -> str:
        return getattr(self._inner, "model_name", "unknown")

    async def generate(self, request: VLMRequest) -> VLMResponse:
        if self._reuse:
            cached = self._cassette.get(request)
            if cached is not None:
                self.reused += 1
                return cached
        response: VLMResponse = await self._inner.generate(request)  # type: ignore[attr-defined]
        self._cassette.put(request, response)
        self.recorded += 1
        return response


class ScriptedVLM:
    """Birim testler için sabit yanıt üreten istemci.

    Kaset gerektirmez; ajan mantığının belirli bir VLM çıktısına nasıl tepki
    verdiğini test etmek için kullanılır (ör. "VLM kanıtsız olay uydurursa
    verifier onu eler mi?").
    """

    def __init__(self, responses: list[str] | str, model_name: str = "scripted") -> None:
        self._queue = [responses] if isinstance(responses, str) else list(responses)
        self._i = 0
        self._model_name = model_name
        self.calls: list[VLMRequest] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, request: VLMRequest) -> VLMResponse:
        self.calls.append(request)
        if not self._queue:
            raise AssertionError("ScriptedVLM: yanıt kuyruğu boş")
        text = self._queue[min(self._i, len(self._queue) - 1)]
        self._i += 1
        return VLMResponse(
            text=text,
            model=self._model_name,
            usage=VLMUsage(prompt_tokens=0, completion_tokens=len(text) // 4, latency_ms=0.0),
        )


# ── Yardımcılar ──────────────────────────────────────────────────────


def cassette_for(profile: object, name: str = "default") -> Cassette:
    """Profile göre kaset dosyasını çöz ve doğru modda aç."""
    directory: Path = profile.cassette_path  # type: ignore[attr-defined]
    mode: str = profile.cassette_mode  # type: ignore[attr-defined]
    return Cassette(directory / f"{name}.jsonl", mode=mode)


def merge_cassettes(sources: list[Path], target: Path) -> int:
    """Birden fazla kaseti tek dosyada birleştir (çakışmada son kayıt kazanır).

    Ekipteki farklı kişiler farklı kasetler üretirse bunu kullanın.
    """
    merged: dict[str, CassetteEntry] = {}
    for src in sources:
        if not src.is_file():
            continue
        for line in src.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                entry = CassetteEntry.model_validate_json(line)
            except Exception:
                continue
            merged[entry.key] = entry
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        for entry in sorted(merged.values(), key=lambda e: (e.prompt_id, e.key)):
            fh.write(entry.model_dump_json() + "\n")
    return len(merged)


def load_jsonl(path: Path) -> list[dict]:
    """Genel amaçlı JSONL okuyucu (eval anotasyonları da bu formatta)."""
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(json.loads(line))
    return out
