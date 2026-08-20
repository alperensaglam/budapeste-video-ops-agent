"""Kanıt Grafiği (Evidence Graph) sözleşmeleri — 'algı ↔ anlam köprüsü'.

Şartname, Bölüm 4:
    "Sistem, düşük seviyeli algı (object detection vb.) ile yüksek seviyeli çıkarım
     (olay yorumlama) arasında bir köprü kurabilmelidir."

Bu modül o köprünün veri sözleşmesidir. İki temel kural:

1. **Her olgu zaman damgalı ve kaynaklıdır.** Kaynağı olmayan olgu grafiğe giremez.
2. **Grafik LLM bağlamına dökülmez.** Ajan onu ARAÇLARLA sorgular
   (:class:`EvidenceQuery`). Bu, hem bağlam verimliliği hem doğrulanabilirlik sağlar.

Sahibi: Hasan (L0-L2). Tüketicisi: Alperen (L4 ajan), Emre (L3 VLM bağlamı).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from gozcu.contracts.common import (
    BoundingBox,
    Confidence,
    EvidenceSource,
    GozcuModel,
    Seconds,
)

# ─────────────────────────── Olgu (Fact) ───────────────────────────


class EvidenceItem(GozcuModel):
    """Kanıt Grafiği'nin atomu: tek bir zaman damgalı, kaynaklı gözlem.

    Örnek::

        EvidenceItem(
            id="ev_0042", t=15.2, source=EvidenceSource.DETECTOR,
            kind="object_detected", confidence=0.91,
            subject="forklift", track_id=7,
            bbox=BoundingBox(x1=.3, y1=.4, x2=.7, y2=.9),
            detail="forklift bbox en/boy oranı 0.5 → 1.4 (devrilme sezgisi)",
        )
    """

    id: str = Field(pattern=r"^ev_\d{4,}$", description="Kararlı kimlik: ev_0001")
    t: Seconds
    t_end: Seconds | None = Field(default=None, description="Aralıklı olgular için bitiş")
    source: EvidenceSource
    kind: str = Field(
        min_length=1,
        description="Olgu tipi, snake_case (ör. object_detected, fall_detected, "
        "zone_violation, speech_segment, audio_event, no_motion)",
    )
    confidence: Confidence
    subject: str | None = Field(default=None, description="Özne sınıfı: person, forklift, ...")
    track_id: int | None = Field(default=None, ge=0, description="Takip kimliği (varsa)")
    bbox: BoundingBox | None = None
    zone: str | None = Field(default=None, description="Bölge kimliği (ör. depo_A_kavsak)")
    detail: str = Field(default="", description="Türkçe, insan-okur açıklama")
    attrs: dict[str, Any] = Field(
        default_factory=dict, description="Kaynağa özgü ek alanlar (şemasız kaçış kapısı)"
    )

    @model_validator(mode="after")
    def _check_interval(self) -> EvidenceItem:
        if self.t_end is not None and self.t_end < self.t:
            raise ValueError(f"t_end ({self.t_end}) < t ({self.t})")
        return self

    @property
    def duration(self) -> float:
        return (self.t_end - self.t) if self.t_end is not None else 0.0

    @property
    def is_deterministic(self) -> bool:
        """Verifier yalnızca deterministik olguları 'kanıt' sayar."""
        return self.source.is_deterministic


class TrackSegment(GozcuModel):
    """Bir varlığın zaman içindeki sürekli izi. Nedenselliğin taşıyıcısı."""

    track_id: int = Field(ge=0)
    cls: str = Field(description="person, forklift, vehicle, ...")
    t_start: Seconds
    t_end: Seconds
    confidence: Confidence
    zones: list[str] = Field(default_factory=list, description="Uğradığı bölgeler, sırayla")
    mean_speed: float | None = Field(
        default=None, ge=0.0, description="Normalize kare/sn hız — hareketsizlik tespiti için"
    )
    n_observations: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _check_span(self) -> TrackSegment:
        if self.t_end < self.t_start:
            raise ValueError(f"t_end ({self.t_end}) < t_start ({self.t_start})")
        return self


class EvidenceRelation(GozcuModel):
    """İki olgu/iz arasındaki uzamsal-zamansal ilişki. 'Grafik'i grafik yapan kenar."""

    src_id: str
    dst_id: str
    kind: Literal[
        "precedes",  # zamansal öncelik
        "co_occurs",  # eşzamanlılık
        "same_entity",  # aynı varlık (takip birleştirme / çoklu kamera)
        "spatial_near",  # uzamsal yakınlık
        "causes",  # nedensellik HİPOTEZİ (VLM üretir, kesin değildir)
        "corroborates",  # bağımsız kaynaktan doğrulama (verifier için altın kenar)
    ]
    confidence: Confidence = 1.0
    detail: str = ""


# ─────────────────────────── Sorgu arayüzü ───────────────────────────


class EvidenceQuery(GozcuModel):
    """Ajanın Kanıt Grafiği'ni sorgulama sözleşmesi.

    Bu, Hasan → Alperen arasındaki DONDURULMUŞ SINIR #1'dir. Ajan grafiğe doğrudan
    erişmez; yalnızca bu sorguyu üreten bir araç çağırır.
    """

    t_start: Seconds | None = None
    t_end: Seconds | None = None
    sources: list[EvidenceSource] | None = None
    kinds: list[str] | None = None
    subjects: list[str] | None = None
    track_ids: list[int] | None = None
    zones: list[str] | None = None
    min_confidence: Confidence = 0.0
    deterministic_only: bool = Field(default=False, description="Verifier bunu True ile çağırır")
    limit: int = Field(default=200, ge=1, le=5000)

    @model_validator(mode="after")
    def _check_window(self) -> EvidenceQuery:
        if self.t_start is not None and self.t_end is not None and self.t_end < self.t_start:
            raise ValueError("t_end < t_start")
        return self


class EvidenceQueryResult(GozcuModel):
    """Sorgu sonucu + ajanın bağlam bütçesini yönetmesi için sayaçlar."""

    items: list[EvidenceItem]
    total_matched: int = Field(ge=0, description="limit uygulanmadan önceki eşleşme sayısı")
    truncated: bool = False
    query_ms: float = Field(default=0.0, ge=0.0)


class EvidenceGraphStats(GozcuModel):
    """`triage` düğümünün analiz derinliğini seçmek için baktığı özet.

    Bu istatistikler LLM'e verilir; LLM 'bu videoda ne kadar iş var?' kararını buna
    bakarak verir → statik olmayan pipeline.
    """

    video_id: str
    duration_s: Seconds
    n_items: int = Field(ge=0)
    n_tracks: int = Field(ge=0)
    n_relations: int = Field(default=0, ge=0)
    by_source: dict[str, int] = Field(default_factory=dict)
    by_kind: dict[str, int] = Field(default_factory=dict)
    #: Saniyelik hareket+ses yoğunluğu profili (uyarlanabilir örnekleme buna bakar)
    activity_profile: list[float] = Field(default_factory=list)
    has_audio: bool = True
    peak_activity_windows: list[tuple[float, float]] = Field(
        default_factory=list, description="En yoğun (t_start, t_end) aralıkları, azalan sırada"
    )
