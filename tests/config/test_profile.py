"""Donanım profili testleri.

Üç profil (cpu-dev / colab-t4 / h200-prod) tek kod tabanının üç ortamda çalışmasını
sağlar. Bu testler, profillerin yazım hatası taşımadığını ve her ortam için doğru
kısıtlara sahip olduğunu garanti eder.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gozcu.config import (
    DEFAULT_PROFILE,
    Profile,
    VLMBackend,
    available_profiles,
    load_profile,
)
from gozcu.config.profile import PROFILE_DIR

BEKLENEN_PROFILLER = {"cpu-dev", "colab-t4", "h200-prod"}


class TestProfilYukleme:
    def test_uc_profil_de_mevcut(self) -> None:
        assert set(available_profiles()) == BEKLENEN_PROFILLER

    @pytest.mark.parametrize("ad", sorted(BEKLENEN_PROFILLER))
    def test_her_profil_hatasiz_yukleniyor(self, ad: str) -> None:
        """extra=forbid sayesinde YAML'daki yazım hatası burada patlar."""
        p = load_profile(ad)
        assert isinstance(p, Profile)
        assert p.name == ad
        assert p.description, f"{ad}: açıklama boş olmamalı"

    def test_varsayilan_profil_cpu_dev(self) -> None:
        assert DEFAULT_PROFILE == "cpu-dev"
        assert load_profile().name == "cpu-dev"

    def test_ortam_degiskeni_okunuyor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        load_profile.cache_clear()
        monkeypatch.setenv("GOZCU_PROFILE", "h200-prod")
        assert load_profile().name == "h200-prod"
        load_profile.cache_clear()

    def test_bilinmeyen_profil_yardimci_hata_verir(self) -> None:
        with pytest.raises(FileNotFoundError) as exc:
            load_profile("olmayan-profil")
        assert "cpu-dev" in str(exc.value), "hata mesajı mevcut profilleri listelemeli"

    def test_yaml_dosyalari_diskte_var(self) -> None:
        for ad in BEKLENEN_PROFILLER:
            assert (PROFILE_DIR / f"{ad}.yaml").is_file()


class TestCpuDevKisitlari:
    """cpu-dev, dört kişinin GPU'suz çalışmasını sağlayan profildir."""

    def test_gpu_gerektirmez(self) -> None:
        p = load_profile("cpu-dev")
        assert p.is_gpu is False
        assert p.perception.device == "cpu"

    def test_vlm_kasetten_oynatir(self) -> None:
        p = load_profile("cpu-dev")
        assert p.vlm.backend is VLMBackend.CASSETTE
        assert p.planner.backend is VLMBackend.CASSETTE
        assert p.cassette_mode == "replay"

    def test_kare_butcesi_dusuk_tutulmus(self) -> None:
        """CPU'da yüksek kare sayısı geliştirmeyi durdurur."""
        p = load_profile("cpu-dev")
        assert p.sampling.max_frames_total <= 32
        assert p.perception.max_video_seconds <= 120

    def test_asr_cpu_icin_int8(self) -> None:
        assert load_profile("cpu-dev").perception.asr_compute_type == "int8"


class TestGpuProfilleri:
    def test_colab_t4_bfloat16_kullanmaz(self) -> None:
        """T4 = Turing (sm75): bfloat16 desteklenmez, half zorunlu."""
        p = load_profile("colab-t4")
        assert p.vlm.dtype == "half"
        assert p.is_gpu is True

    def test_colab_t4_kaset_kaydeder(self) -> None:
        """Emre'nin profili ekibin geri kalanı için kaset üretir."""
        assert load_profile("colab-t4").cassette_mode == "record"

    def test_h200_fp8_kullanir(self) -> None:
        """H200 = Hopper (sm90): FP8 native desteklenir."""
        p = load_profile("h200-prod")
        assert p.vlm.dtype == "fp8"
        assert p.vlm.enable_prefix_caching is True

    def test_h200_uzun_video_destekler(self) -> None:
        """Vardiya raporu senaryosu için en az 1 saat."""
        assert load_profile("h200-prod").perception.max_video_seconds >= 3600

    def test_gpu_profilleri_yerel_endpoint_kullanir(self) -> None:
        """Şartname: dış API / kapalı servis / bulut bağımlılığı YASAK."""
        for ad in ("colab-t4", "h200-prod"):
            p = load_profile(ad)
            for url in (p.vlm.base_url, p.planner.base_url):
                assert "localhost" in url or "127.0.0.1" in url, (
                    f"{ad}: {url} yerel değil — şartname dış servis bağımlılığını yasaklıyor"
                )


class TestOrtakDavranis:
    @pytest.mark.parametrize("ad", sorted(BEKLENEN_PROFILLER))
    def test_verifier_varsayilan_acik(self, ad: str) -> None:
        """Verifier halüsinasyon savunmasıdır; ablation dışında kapatılamaz."""
        assert load_profile(ad).agent.enable_verifier is True

    @pytest.mark.parametrize("ad", sorted(BEKLENEN_PROFILLER))
    def test_geri_alinamaz_aksiyon_onay_ister(self, ad: str) -> None:
        """112 arama / saha kapatma her profilde operatör onayı gerektirir."""
        assert load_profile(ad).agent.require_confirmation_for_irreversible is True

    @pytest.mark.parametrize("ad", sorted(BEKLENEN_PROFILLER))
    def test_hata_enjeksiyonu_varsayilan_kapali(self, ad: str) -> None:
        """Kaos testi yalnızca eval koşularında açılır; demoda asla."""
        assert load_profile(ad).faults.enabled is False

    @pytest.mark.parametrize("ad", sorted(BEKLENEN_PROFILLER))
    def test_uyarlanabilir_ornekleme_acik(self, ad: str) -> None:
        """Şartname: statik, yalnızca kural tabanlı çözümler düşük puanlanır."""
        assert load_profile(ad).sampling.adaptive is True

    def test_kaset_yolu_mutlak_cozuluyor(self) -> None:
        yol = load_profile("cpu-dev").cassette_path
        assert isinstance(yol, Path)
        assert yol.is_absolute()
        assert yol.name == "cassettes"
