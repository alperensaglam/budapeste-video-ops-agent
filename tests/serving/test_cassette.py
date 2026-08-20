"""Kaset altyapısı testleri.

Bu testler, ekibin GPU'suz çalışabilmesini sağlayan mekanizmayı korur.
Kırmızıysa üç kişi (Alperen, Hasan, İbrahim) çalışamaz hale gelir.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gozcu.contracts.vlm import (
    FrameRef,
    MessageRole,
    VLMMessage,
    VLMRequest,
    VLMResponse,
    VLMUsage,
)
from gozcu.serving.cassette import (
    Cassette,
    CassetteMissError,
    CassetteVLM,
    RecordingVLM,
    ScriptedVLM,
    merge_cassettes,
)

SHA = "a" * 64


def istek(text: str = "merhaba", prompt_id: str = "test@v1", t: float = 0.0) -> VLMRequest:
    return VLMRequest(
        messages=[
            VLMMessage(
                role=MessageRole.USER,
                text=text,
                frames=[FrameRef(t=t, sha256=SHA, width=640, height=480)],
            )
        ],
        model="test-model",
        prompt_id=prompt_id,
    )


def yanit(text: str = "cevap") -> VLMResponse:
    return VLMResponse(text=text, model="test-model", usage=VLMUsage(completion_tokens=2))


class TestCacheKey:
    """Kaset anahtarı isteğin İÇERİĞİNE bağlı olmalı, ortama değil."""

    def test_ayni_istek_ayni_anahtar(self) -> None:
        assert istek().cache_key() == istek().cache_key()

    def test_farkli_metin_farkli_anahtar(self) -> None:
        assert istek("a").cache_key() != istek("b").cache_key()

    def test_farkli_kare_zamani_farkli_anahtar(self) -> None:
        assert istek(t=0.0).cache_key() != istek(t=5.0).cache_key()

    def test_dosya_yolu_anahtari_etkilemez(self) -> None:
        """Kaset başka makinede de tutmalı — path ortama bağlıdır, hash'e girmez."""
        a = istek()
        b = istek()
        b.messages[0].frames[0].path = "/bambaska/bir/yol/kare.jpg"
        assert a.cache_key() == b.cache_key()

    def test_prompt_surumu_anahtari_degistirir(self) -> None:
        """Prompt v1 -> v2 değişince eski kaset kullanılmamalı."""
        assert istek(prompt_id="x@v1").cache_key() != istek(prompt_id="x@v2").cache_key()


class TestKayitVeOynatma:
    def test_kaydet_ve_geri_oku(self, tmp_path: Path) -> None:
        yol = tmp_path / "k.jsonl"
        kaset = Cassette(yol, mode="record")
        kaset.put(istek(), yanit("forklift devrildi"))

        tekrar = Cassette(yol, mode="replay")
        assert len(tekrar) == 1
        bulunan = tekrar.get(istek())
        assert bulunan is not None
        assert bulunan.text == "forklift devrildi"
        assert bulunan.from_cache is True

    def test_replay_modu_diske_yazmaz(self, tmp_path: Path) -> None:
        yol = tmp_path / "k.jsonl"
        Cassette(yol, mode="record").put(istek(), yanit())
        boyut = yol.stat().st_size

        kaset = Cassette(yol, mode="replay")
        kaset.put(istek("baska"), yanit())
        assert yol.stat().st_size == boyut, "replay modunda dosya değişmemeli"

    def test_bozuk_satir_atlanir(self, tmp_path: Path) -> None:
        yol = tmp_path / "k.jsonl"
        Cassette(yol, mode="record").put(istek(), yanit())
        with yol.open("a", encoding="utf-8") as fh:
            fh.write("bu gecerli json degil\n")
        assert len(Cassette(yol, mode="replay")) == 1

    def test_compact_yinelenenleri_temizler(self, tmp_path: Path) -> None:
        yol = tmp_path / "k.jsonl"
        kaset = Cassette(yol, mode="record")
        for _ in range(3):
            kaset.put(istek(), yanit())  # aynı anahtar, 3 kez append
        assert len(yol.read_text(encoding="utf-8").strip().splitlines()) == 3
        assert kaset.compact() == 1
        assert len(yol.read_text(encoding="utf-8").strip().splitlines()) == 1

    def test_turkce_karakterler_gidip_geliyor(self, tmp_path: Path) -> None:
        yol = tmp_path / "k.jsonl"
        metin = "Yerde hareketsiz kişi tespit edildi; sağlık ekibi çağrılmalı."
        Cassette(yol, mode="record").put(istek(), yanit(metin))
        okunan = Cassette(yol, mode="replay").get(istek())
        assert okunan is not None and okunan.text == metin


class TestCassetteVLM:
    @pytest.mark.asyncio
    async def test_isabet(self, tmp_path: Path) -> None:
        yol = tmp_path / "k.jsonl"
        Cassette(yol, mode="record").put(istek(), yanit("tamam"))
        vlm = CassetteVLM(Cassette(yol, mode="replay"))
        r = await vlm.generate(istek())
        assert r.text == "tamam"
        assert vlm.hits == 1 and vlm.hit_rate == 1.0

    @pytest.mark.asyncio
    async def test_iskalama_gurultulu_hata_verir(self, tmp_path: Path) -> None:
        """Sessiz boş yanıt = yalancı yeşil test. Bilerek patlıyoruz."""
        vlm = CassetteVLM(Cassette(tmp_path / "yok.jsonl", mode="replay"))
        with pytest.raises(CassetteMissError) as exc:
            await vlm.generate(istek())
        assert "record-cassettes" in str(exc.value), "hata mesajı çözümü söylemeli"


class TestRecordingVLM:
    @pytest.mark.asyncio
    async def test_mevcut_kayit_varsa_modeli_cagirmaz(self, tmp_path: Path) -> None:
        """Kaggle GPU kotası (haftada 30 saat) boşa gitmemeli."""
        yol = tmp_path / "k.jsonl"
        Cassette(yol, mode="record").put(istek(), yanit("eski"))

        ic = ScriptedVLM(["YENI CAGRI"])
        sarmal = RecordingVLM(ic, Cassette(yol, mode="record"))
        r = await sarmal.generate(istek())

        assert r.text == "eski"
        assert sarmal.reused == 1 and sarmal.recorded == 0
        assert ic.calls == [], "iç model hiç çağrılmamalıydı"

    @pytest.mark.asyncio
    async def test_yeni_istek_kaydedilir(self, tmp_path: Path) -> None:
        yol = tmp_path / "k.jsonl"
        sarmal = RecordingVLM(ScriptedVLM(["taze yanit"]), Cassette(yol, mode="record"))
        r = await sarmal.generate(istek())
        assert r.text == "taze yanit" and sarmal.recorded == 1
        assert len(Cassette(yol, mode="replay")) == 1


class TestBirlestirme:
    def test_farkli_kisilerin_kasetleri_birlesir(self, tmp_path: Path) -> None:
        a, b = tmp_path / "emre.jsonl", tmp_path / "alperen.jsonl"
        Cassette(a, mode="record").put(istek("soru-a"), yanit("cevap-a"))
        Cassette(b, mode="record").put(istek("soru-b"), yanit("cevap-b"))

        hedef = tmp_path / "birlesik.jsonl"
        assert merge_cassettes([a, b], hedef) == 2
        birlesik = Cassette(hedef, mode="replay")
        assert birlesik.get(istek("soru-a")).text == "cevap-a"  # type: ignore[union-attr]
        assert birlesik.get(istek("soru-b")).text == "cevap-b"  # type: ignore[union-attr]
