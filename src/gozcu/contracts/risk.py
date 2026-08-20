"""Risk değerlendirme sözleşmeleri.

Şartname, Bölüm 4: "Statik, yalnızca kural tabanlı çözümler düşük puanlanacaktır."

Bu yüzden risk seviyesini MODEL belirler (:class:`RiskAssessment` bir LLM çıktısıdır).
:class:`SafetyGuardRule` yalnızca ince bir EMNİYET BARİYERİ'dir: modelin kararını
yükseltebilir, asla düşüremez. Bu ayrım dokümantasyonda ve sunumda açıkça belirtilir —
"kural motoru değil, güvenlik bariyeri".
"""

from __future__ import annotations

from pydantic import Field

from gozcu.contracts.common import Confidence, GozcuModel, RiskLevel, Severity, risk_rank


class RiskFactor(GozcuModel):
    """Risk skorunu oluşturan tekil etken — açıklanabilirlik için ayrıştırılmıştır."""

    name: str = Field(description="yaralanma_olasiligi, maruziyet, siddet, mudahale_gecikmesi")
    weight: float = Field(ge=0.0, le=1.0)
    value: float = Field(ge=0.0, le=1.0)
    rationale: str = ""

    @property
    def contribution(self) -> float:
        return self.weight * self.value


class RiskAssessment(GozcuModel):
    """Video geneli risk değerlendirmesi. LLM üretir, emniyet bariyeri denetler."""

    level: RiskLevel
    score: Confidence = Field(description="Sürekli risk skoru [0,1]")
    factors: list[RiskFactor] = Field(default_factory=list)
    rationale: str = Field(description="Türkçe gerekçe — operatörün okuyacağı metin")
    uncertainty: str = Field(
        default="", description="Neyin doğrulanamadığı. Boş bırakmak yerine dürüst olun."
    )
    driving_event_ids: list[str] = Field(
        default_factory=list, description="Bu seviyeyi belirleyen olaylar"
    )
    model_level: RiskLevel | None = Field(
        default=None, description="Bariyer ÖNCESİ modelin verdiği seviye (şeffaflık izi)"
    )
    guard_applied: str | None = Field(default=None, description="Uygulanan bariyer kuralının adı")

    @property
    def was_escalated(self) -> bool:
        """Emniyet bariyeri modelin kararını yükseltti mi? UI'da rozet olarak gösterilir."""
        return self.model_level is not None and risk_rank(self.level) > risk_rank(self.model_level)


class SafetyGuardRule(GozcuModel):
    """Emniyet bariyeri kuralı: yalnızca ALT SINIR koyar, asla üst sınır koymaz.

    Örnek: hareketsiz_kisi olayı doğrulandıysa risk asla Düşük'ün altında olamaz.

    Bunlar risk MOTORU değildir — model kararının güvenlik tarafında kalmasını sağlayan
    az sayıda (hedef: 6'dan az) sınır koşuludur ve her biri gerekçesiyle dokümante edilir.
    Sayı arttıkça "kural tabanlı sistem" eleştirisine açık hale geliriz; sınırı koruyun.
    """

    name: str
    when_event_type: str = Field(description="Bu olay tipi DOĞRULANMIŞ olarak varsa")
    min_severity_required: Severity = Severity.ORTA
    floor_level: RiskLevel = Field(description="Riskin inebileceği en düşük seviye")
    justification: str = Field(description="Neden bu bariyer var — sunumda savunulacak metin")
