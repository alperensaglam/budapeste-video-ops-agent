"""Nihai analiz raporu — sistemin dışa açılan TEK sözleşmesi.

Şartname, Bölüm 5, birebir istenen çıktı::

    {
      "summary": "...",
      "events":  [{"time": "00:15", "event": "Forklift devrildi"}],
      "risk":    "Yüksek",
      "actions": ["Sağlık ekibini çağır", "Alanı güvenlik altına al"]
    }

TASARIM KARARI — "şartname sözleşmesi, bizim şemamızın ALT KÜMESİDİR":
Üst seviyede şartnamenin dört anahtarı BİREBİR korunur (jüri gözünde net eşleşme,
geriye dönük uyum), üzerine ``*_detail`` zenginleştirmeleri eklenir. ``events`` ve
``actions`` TÜRETİLMİŞ alanlardır (``computed_field``) — tek doğruluk kaynağı
``events_detail`` / ``actions_detail``, böylece ikisi asla birbirinden ayrışamaz.

Sahibi: Alperen üretir (L4 report düğümü); İbrahim tüketir (L6 API/UI).
DONDURULMUŞ SINIR #4.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, computed_field

from gozcu.contracts.actions import RecommendedAction
from gozcu.contracts.common import AnalysisDepth, Confidence, GozcuModel, RiskLevel, Seconds
from gozcu.contracts.events import DetectedEvent
from gozcu.contracts.risk import RiskAssessment

#: Şartnamenin zorunlu kıldığı üst seviye anahtarlar. Sözleşme testi bunu kilitler.
SARTNAME_REQUIRED_KEYS: tuple[str, ...] = ("summary", "events", "risk", "actions")


class Abstention(GozcuModel):
    """Sistemin BİLEREK karar vermediği nokta.

    Çekimserlik bir özelliktir, eksiklik değil. Şartname "açıklanabilir çıktı" istiyor;
    neyi bilmediğini söyleyen bir sistem, her şeyi bilir gibi davranandan daha güvenilir.
    Demoda "olaysız video" senaryosunda bu alan yıldız oyuncudur.
    """

    topic: str = Field(description="Neyin belirlenemediği")
    reason: str = Field(description="Neden belirlenemedi — Türkçe")
    t_start: Seconds | None = None
    t_end: Seconds | None = None
    suggested_followup: str = Field(
        default="", description="Operatörün ne yapması önerilir (ör. 2 numaralı kamerayı iste)"
    )


class RunMetrics(GozcuModel):
    """Performans ve maliyet muhasebesi.

    Şartname, Bölüm 4: "Video işleme süresi, model inference süresi, bellek ve donanım
    kullanımı ... önemli değerlendirme kriterleri arasındadır."
    Bu alan HER raporda döner ve demoda ekranda canlı görünür.
    """

    video_duration_s: Seconds = 0.0
    e2e_latency_s: float = Field(default=0.0, ge=0.0)
    ingest_s: float = Field(default=0.0, ge=0.0)
    perception_s: float = Field(default=0.0, ge=0.0)
    vlm_s: float = Field(default=0.0, ge=0.0)
    agent_s: float = Field(default=0.0, ge=0.0)
    vlm_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    agent_turns: int = Field(default=0, ge=0)
    frames_sampled: int = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    peak_vram_gb: float | None = None
    cache_hit_rate: Confidence = 0.0
    profile: str = Field(default="cpu-dev", description="Hangi donanım profilinde koştu")
    model_name: str = ""

    @computed_field
    @property
    def rtf(self) -> float:
        """Real-Time Factor = işleme süresi / video süresi. Ana performans KPI.

        RTF < 1.0 gerçek zamandan hızlı demektir. Hedef: H200 profilinde 0.20 veya altı.
        """
        if self.video_duration_s <= 0:
            return 0.0
        return round(self.e2e_latency_s / self.video_duration_s, 4)


class AnalysisReport(GozcuModel):
    """Sistemin nihai çıktısı. Şartname sözleşmesi + GÖZCÜ zenginleştirmesi."""

    # ── Kimlik / bağlam ────────────────────────────────────────────────
    video_id: str
    schema_version: str = Field(
        default="1.0.0", description="Sözleşme sürümü — kırıcı değişimde artar"
    )
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDART

    # ── ŞARTNAME SÖZLEŞMESİ (doğrudan alanlar) ─────────────────────────
    summary: str = Field(
        min_length=1,
        description="Kısa, anlaşılır, gereksiz detaydan arındırılmış Türkçe özet. "
        "Operatörün hızlı karar almasını destekleyecek şekilde yapılandırılmış.",
    )
    risk: RiskLevel = Field(description="Şartnamedeki risk alanı: Yüksek / Orta / Düşük / ...")

    # ── ZENGİNLEŞTİRME (tek doğruluk kaynakları) ───────────────────────
    events_detail: list[DetectedEvent] = Field(default_factory=list)
    risk_assessment: RiskAssessment | None = None
    actions_detail: list[RecommendedAction] = Field(default_factory=list)
    abstentions: list[Abstention] = Field(default_factory=list)
    timeline_note: str = Field(
        default="", description="Olay akışının nedensel anlatımı (başlangıç-gelişim-sonuç)"
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Ajanın operatöre sormak istediği netleştirici sorular. "
        "Rubrikteki 'doğru soruları sorma' maddesinin somut çıktısı.",
    )
    metrics: RunMetrics = Field(default_factory=RunMetrics)

    # ── TÜRETİLMİŞ ŞARTNAME ALANLARI (asla elle set edilmez) ───────────

    @computed_field
    @property
    def events(self) -> list[dict[str, str]]:
        """Şartname biçimi. events_detail alanından türetilir, zamana göre sıralıdır."""
        ordered = sorted(self.events_detail, key=lambda x: x.t_start)
        return [e.to_sartname_event() for e in ordered]

    @computed_field
    @property
    def actions(self) -> list[str]:
        """Şartname biçimi. actions_detail alanından türetilir, önceliğe göre sıralıdır."""
        order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        ranked = sorted(self.actions_detail, key=lambda a: order.get(a.priority.value, 9))
        return [a.to_sartname_action() for a in ranked]

    # ── Serileştirme ───────────────────────────────────────────────────

    def to_sartname_json(self) -> dict[str, Any]:
        """SADECE şartnamenin dört anahtarı. Uyumluluk testi ve minimal tüketiciler için."""
        return {
            "summary": self.summary,
            "events": self.events,
            "risk": self.risk.value,
            "actions": self.actions,
        }

    def to_output(self) -> dict[str, Any]:
        """Tam çıktı — şartname anahtarları ÖNCE, zenginleştirme sonra.

        Anahtar sırası kasıtlıdır: jüri JSON dosyasını açtığında ilk gördüğü şey
        şartnamenin istediği dört alan olur.
        """
        out: dict[str, Any] = self.to_sartname_json()
        rest = self.model_dump(mode="json", exclude={"summary", "risk", "events", "actions"})
        out.update(rest)
        return out

    # ── Kendi kendini denetleme ────────────────────────────────────────

    def integrity_issues(self) -> list[str]:
        """Rapor yayınlanmadan önceki iç tutarlılık denetimi.

        Bu liste BOŞ değilse rapor operatöre gösterilmez; ajan reflect düğümüne döner.
        Halüsinasyon savunmasının son kapısıdır.
        """
        issues: list[str] = []
        event_ids = {e.id for e in self.events_detail}

        for ev in self.events_detail:
            if not ev.evidence:
                issues.append(f"{ev.id}: kanıtsız olay (evidence listesi boş)")
            elif not ev.has_deterministic_support and ev.support_score < 0.5:
                issues.append(
                    f"{ev.id}: yalnızca VLM kaynaklı ve destek skoru düşük "
                    f"({ev.support_score:.2f}) — belirsiz olarak işaretlenmeli"
                )

        for act in self.actions_detail:
            unknown = [eid for eid in act.triggering_event_ids if eid not in event_ids]
            if unknown:
                issues.append(f"{act.id}: bilinmeyen olaya atıf {unknown}")
            if not act.triggering_event_ids and self.events_detail:
                issues.append(f"{act.id}: hiçbir olaya bağlanmamış aksiyon")

        if self.risk_assessment and self.risk_assessment.level != self.risk:
            issues.append(
                f"risk uyuşmazlığı: üst seviye {self.risk.value} != "
                f"risk_assessment.level {self.risk_assessment.level.value}"
            )
        return issues
