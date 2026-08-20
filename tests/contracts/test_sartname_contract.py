"""ŞARTNAME UYUM TESTİ — projedeki en kritik test.

Bu test, sistemin çıktısının TEKNOFEST 2026 şartnamesi Bölüm 5'teki örnek JSON ile
birebir uyumlu kalmasını kilitler. Bu dosya kırmızıysa hiçbir şey teslim edilmez.

Şartname Bölüm 5, birebir örnek::

    {
      "summary": "Videoda forklift kazası ve yaralanma riski gözlenmiştir.",
      "events": [
        {"time": "00:15", "event": "Forklift devrildi"},
        {"time": "00:20", "event": "Yerde hareketsiz kişi"}
      ],
      "risk": "Yüksek",
      "actions": ["Sağlık ekibini çağır", "Alanı güvenlik altına al"]
    }
"""

from __future__ import annotations

import json

import pytest

from gozcu.contracts import (
    SARTNAME_REQUIRED_KEYS,
    ActionPriority,
    AnalysisReport,
    DetectedEvent,
    EvidenceRef,
    EvidenceSource,
    RecommendedAction,
    RiskAssessment,
    RiskLevel,
    Severity,
)

# Şartname Bölüm 3'teki senaryonun birebir yeniden inşası.
SARTNAME_ORNEK = {
    "summary": "Videoda forklift kazası ve yaralanma riski gözlenmiştir.",
    "events": [
        {"time": "00:15", "event": "Forklift devrildi"},
        {"time": "00:20", "event": "Yerde hareketsiz kişi"},
    ],
    "risk": "Yüksek",
    "actions": ["Sağlık ekibini çağır", "Alanı güvenlik altına al"],
}


@pytest.fixture
def forklift_raporu() -> AnalysisReport:
    """Şartnamedeki forklift senaryosunun GÖZCÜ raporu olarak inşası."""
    olaylar = [
        DetectedEvent(
            id="evt_001",
            t_start=15.0,
            t_end=18.9,
            type="arac_devrilmesi",
            label="Forklift devrildi",
            severity=Severity.KRITIK,
            confidence=0.88,
            support_score=0.87,
            verified=True,
            evidence=[
                EvidenceRef(
                    source=EvidenceSource.DETECTOR,
                    t=15.0,
                    detail="forklift kutusunun en/boy oranı 0.5 → 1.4",
                    conf=0.91,
                ),
                EvidenceRef(source=EvidenceSource.AUDIO, t=15.4, detail="çarpma sesi", conf=0.76),
            ],
        ),
        DetectedEvent(
            id="evt_002",
            t_start=20.0,
            t_end=35.0,
            type="hareketsiz_kisi",
            label="Yerde hareketsiz kişi",
            severity=Severity.KRITIK,
            confidence=0.82,
            support_score=0.90,
            verified=True,
            caused_by=["evt_001"],
            evidence=[
                EvidenceRef(
                    source=EvidenceSource.POSE,
                    t=20.0,
                    detail="yatay poz, 15 sn boyunca hız ~0",
                    conf=0.85,
                ),
            ],
        ),
    ]
    aksiyonlar = [
        RecommendedAction(
            id="act_001",
            action="Sağlık ekibini çağır",
            priority=ActionPriority.P0,
            owner="saglik_birimi",
            deadline_sec=60,
            tool="dispatch_medical_team",
            sop_ref="ISG-PR-014 madde 4.2",
            triggering_event_ids=["evt_002"],
            rationale="Hareketsiz kişi + yüksek enerjili çarpışma",
        ),
        RecommendedAction(
            id="act_002",
            action="Alanı güvenlik altına al",
            priority=ActionPriority.P1,
            owner="guvenlik",
            tool="lock_down_area",
            sop_ref="ISG-PR-014 madde 5.1",
            triggering_event_ids=["evt_001"],
            requires_confirmation=True,
        ),
    ]
    return AnalysisReport(
        video_id="ornek_forklift",
        summary="Videoda forklift kazası ve yaralanma riski gözlenmiştir.",
        risk=RiskLevel.YUKSEK,
        events_detail=olaylar,
        actions_detail=aksiyonlar,
        risk_assessment=RiskAssessment(
            level=RiskLevel.YUKSEK,
            score=0.86,
            rationale="Devrilme sonrası 20. saniyede hareketsiz kişi tespit edildi.",
        ),
    )


class TestSartnameUyumu:
    """Şartname Bölüm 5 sözleşmesinin birebir korunduğunu doğrular."""

    def test_cikti_sartname_ornegiyle_birebir_esit(self, forklift_raporu: AnalysisReport) -> None:
        assert forklift_raporu.to_sartname_json() == SARTNAME_ORNEK

    def test_zorunlu_anahtarlar_tam_cikti_icinde_de_var(
        self, forklift_raporu: AnalysisReport
    ) -> None:
        cikti = forklift_raporu.to_output()
        for anahtar in SARTNAME_REQUIRED_KEYS:
            assert anahtar in cikti, f"şartname anahtarı kayıp: {anahtar}"

    def test_sartname_anahtarlari_en_basta_gelir(self, forklift_raporu: AnalysisReport) -> None:
        """Jüri JSON dosyasını açtığında ilk gördüğü şey şartnamenin dört alanı olmalı."""
        ilk_dort = list(forklift_raporu.to_output().keys())[:4]
        assert tuple(ilk_dort) == SARTNAME_REQUIRED_KEYS

    def test_cikti_json_serilesebilir(self, forklift_raporu: AnalysisReport) -> None:
        """Geçerli JSON Oranı = 1.00 KPI'ının en temel garantisi."""
        metin = json.dumps(forklift_raporu.to_output(), ensure_ascii=False)
        geri = json.loads(metin)
        assert geri["risk"] == "Yüksek"
        assert geri["events"][0]["time"] == "00:15"

    def test_turkce_karakterler_bozulmuyor(self, forklift_raporu: AnalysisReport) -> None:
        metin = json.dumps(forklift_raporu.to_output(), ensure_ascii=False)
        assert "Sağlık ekibini çağır" in metin
        assert "Yüksek" in metin


class TestTuretilmisAlanlar:
    """events ve actions türetilmiş alanlardır — kaynakla asla ayrışamaz."""

    def test_olaylar_zamana_gore_siralanir(self) -> None:
        rapor = AnalysisReport(
            video_id="v",
            summary="x",
            risk=RiskLevel.DUSUK,
            events_detail=[
                DetectedEvent(
                    id="evt_002",
                    t_start=30.0,
                    t_end=31.0,
                    type="b",
                    label="Sonra",
                    severity=Severity.DUSUK,
                    confidence=0.5,
                ),
                DetectedEvent(
                    id="evt_001",
                    t_start=10.0,
                    t_end=11.0,
                    type="a",
                    label="Önce",
                    severity=Severity.DUSUK,
                    confidence=0.5,
                ),
            ],
        )
        assert [e["event"] for e in rapor.events] == ["Önce", "Sonra"]
        assert [e["time"] for e in rapor.events] == ["00:10", "00:30"]

    def test_aksiyonlar_oncelige_gore_siralanir(self) -> None:
        rapor = AnalysisReport(
            video_id="v",
            summary="x",
            risk=RiskLevel.ORTA,
            actions_detail=[
                RecommendedAction(
                    id="act_002",
                    action="Sonra yapılacak",
                    priority=ActionPriority.P2,
                    owner="bakim",
                ),
                RecommendedAction(
                    id="act_001",
                    action="Derhal yapılacak",
                    priority=ActionPriority.P0,
                    owner="saglik_birimi",
                ),
            ],
        )
        assert rapor.actions == ["Derhal yapılacak", "Sonra yapılacak"]

    def test_bos_rapor_da_gecerli_sartname_json_uretir(self) -> None:
        """Olaysız video senaryosu: sistem uydurmamalı ama geçerli JSON vermeli."""
        rapor = AnalysisReport(
            video_id="sakin_vardiya",
            summary="Kayıt boyunca kritik bir olay tespit edilmedi.",
            risk=RiskLevel.YOK,
        )
        cikti = rapor.to_sartname_json()
        assert cikti["events"] == []
        assert cikti["actions"] == []
        assert cikti["risk"] == "Yok"
        json.dumps(cikti, ensure_ascii=False)  # patlamamalı


class TestButunlukDenetimi:
    """integrity_issues() halüsinasyon savunmasının son kapısıdır."""

    def test_saglikli_rapor_sorunsuz(self, forklift_raporu: AnalysisReport) -> None:
        assert forklift_raporu.integrity_issues() == []

    def test_kanitsiz_olay_yakalanir(self) -> None:
        rapor = AnalysisReport(
            video_id="v",
            summary="x",
            risk=RiskLevel.ORTA,
            events_detail=[
                DetectedEvent(
                    id="evt_001",
                    t_start=1.0,
                    t_end=2.0,
                    type="a",
                    label="Kanıtsız iddia",
                    severity=Severity.ORTA,
                    confidence=0.9,
                )
            ],
        )
        sorunlar = rapor.integrity_issues()
        assert any("kanıtsız" in s for s in sorunlar)

    def test_sadece_vlm_kaynakli_zayif_olay_yakalanir(self) -> None:
        """VLM tek başına konuşamaz — deterministik destek veya yüksek skor şart."""
        rapor = AnalysisReport(
            video_id="v",
            summary="x",
            risk=RiskLevel.ORTA,
            events_detail=[
                DetectedEvent(
                    id="evt_001",
                    t_start=1.0,
                    t_end=2.0,
                    type="a",
                    label="Sadece VLM gördü",
                    severity=Severity.ORTA,
                    confidence=0.9,
                    support_score=0.3,
                    evidence=[
                        EvidenceRef(
                            source=EvidenceSource.VLM, t=1.0, detail="bana öyle geldi", conf=0.9
                        )
                    ],
                )
            ],
        )
        sorunlar = rapor.integrity_issues()
        assert any("belirsiz" in s for s in sorunlar)

    def test_bilinmeyen_olaya_atif_yapan_aksiyon_yakalanir(self) -> None:
        rapor = AnalysisReport(
            video_id="v",
            summary="x",
            risk=RiskLevel.ORTA,
            events_detail=[
                DetectedEvent(
                    id="evt_001",
                    t_start=1.0,
                    t_end=2.0,
                    type="a",
                    label="Gerçek olay",
                    severity=Severity.ORTA,
                    confidence=0.9,
                    support_score=0.8,
                    evidence=[
                        EvidenceRef(
                            source=EvidenceSource.DETECTOR, t=1.0, detail="tespit", conf=0.9
                        )
                    ],
                )
            ],
            actions_detail=[
                RecommendedAction(
                    id="act_001",
                    action="Hayali aksiyon",
                    priority=ActionPriority.P1,
                    owner="guvenlik",
                    triggering_event_ids=["evt_999"],
                )
            ],
        )
        assert any("bilinmeyen olaya atıf" in s for s in rapor.integrity_issues())

    def test_risk_uyusmazligi_yakalanir(self) -> None:
        rapor = AnalysisReport(
            video_id="v",
            summary="x",
            risk=RiskLevel.DUSUK,
            risk_assessment=RiskAssessment(
                level=RiskLevel.KRITIK, score=0.95, rationale="tutarsız"
            ),
        )
        assert any("risk uyuşmazlığı" in s for s in rapor.integrity_issues())
