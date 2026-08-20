"""Olay sözleşmeleri — Kanıt Grafiği olgularından türetilen YÜKSEK SEVİYE yorumlar.

Bir :class:`DetectedEvent`, ham olguların (bbox, ses, poz) anlamlandırılmış halidir.
Kritik kural: **her olay evidence_ids taşır.** Kanıtsız olay rapora giremez
(bkz. :mod:`gozcu.contracts.report` ve verifier düğümü).

Sahibi: Alperen (L4) üretir; Emre (L3) SegmentAnalysis'i besler.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from gozcu.contracts.common import (
    Confidence,
    EventPhase,
    EvidenceSource,
    GozcuModel,
    Seconds,
    Severity,
    to_timecode,
)


class EvidenceRef(GozcuModel):
    """Rapora gömülen, insan tarafından okunabilir kanıt atıfı.

    Şartname: "Sistem çıktıları mümkün olduğunca açıklanabilir olmalıdır."
    Bu tip o açıklanabilirliğin somut taşıyıcısıdır: jüri bir iddiayı görüp
    "bunu nereden biliyorsun?" dediğinde cevap burada.
    """

    source: EvidenceSource
    t: Seconds
    detail: str
    conf: Confidence
    evidence_id: str | None = Field(default=None, description="Kanıt Grafiği'ndeki atom")


class DetectedEvent(GozcuModel):
    """Zaman damgalı, gerekçeli, kanıta bağlı olay."""

    id: str = Field(pattern=r"^evt_\d{3,}$")
    t_start: Seconds
    t_end: Seconds
    type: str = Field(
        min_length=1,
        description="snake_case olay tipi: arac_devrilmesi, dusme, hareketsiz_kisi, "
        "kkd_ihlali, yetkisiz_giris, kalabalik_toplanmasi, yangin_duman, kavga",
    )
    label: str = Field(min_length=1, description="Operatöre gösterilen kısa Türkçe metin")
    severity: Severity
    confidence: Confidence
    phase: EventPhase = EventPhase.GELISIM
    zone: str | None = None
    actors: list[dict[str, str | int]] = Field(
        default_factory=list, description="Örn. track_id + class çiftleri"
    )
    evidence: list[EvidenceRef] = Field(
        default_factory=list, description="Bu olayı destekleyen kanıtlar"
    )
    evidence_ids: list[str] = Field(
        default_factory=list, description="Kanıt Grafiği atom kimlikleri (verifier kullanır)"
    )
    support_score: Confidence = Field(
        default=0.0,
        description="Verifier'in hesapladığı kanıt-destek skoru. Eşiğin altındaysa olay "
        "belirsiz işaretlenir ve aksiyon üretilmez.",
    )
    verified: bool = Field(default=False, description="Verifier düğümünden geçti mi")
    caused_by: list[str] = Field(default_factory=list, description="Önceki olay id'leri")

    @model_validator(mode="after")
    def _check(self) -> DetectedEvent:
        if self.t_end < self.t_start:
            raise ValueError(f"t_end ({self.t_end}) < t_start ({self.t_start})")
        return self

    @property
    def time(self) -> str:
        """Şartname formatı, örn. 00:15."""
        return to_timecode(self.t_start)

    @property
    def duration(self) -> float:
        return self.t_end - self.t_start

    @property
    def has_deterministic_support(self) -> bool:
        """En az bir deterministik (VLM olmayan) kaynak bu olayı destekliyor mu?

        Halüsinasyon savunmasının birinci filtresi.
        """
        return any(ref.source.is_deterministic for ref in self.evidence)

    def to_sartname_event(self) -> dict[str, str]:
        """Şartnamedeki birebir biçim: time + event anahtarları."""
        return {"time": self.time, "event": self.label}


class SegmentAnalysis(GozcuModel):
    """VLM'in tek bir video segmenti için ürettiği yapılandırılmış çıktı (L3).

    Emre -> Alperen arasındaki DONDURULMUŞ SINIR #2'nin parçası.
    Hiyerarşik özetleme bunları toplayarak video geneline çıkar.
    """

    segment_id: str
    t_start: Seconds
    t_end: Seconds
    description: str = Field(description="Segmentin kısa Türkçe betimlemesi")
    observed_actions: list[str] = Field(default_factory=list)
    observed_objects: list[str] = Field(default_factory=list)
    anomaly: bool = Field(default=False, description="Olağandışı bir şey var mı")
    anomaly_reason: str = ""
    candidate_events: list[str] = Field(
        default_factory=list, description="Ham olay adayları — henüz doğrulanmamış"
    )
    needs_closer_look: bool = Field(
        default=False,
        description="True ise ajan bu aralığı yüksek fps ile YENİDEN sorgular "
        "(kaba-ince temellendirme döngüsü)",
    )
    confidence: Confidence = 0.5
    n_frames_used: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _check(self) -> SegmentAnalysis:
        if self.t_end < self.t_start:
            raise ValueError("t_end < t_start")
        return self
