"""Ortak tipler, sabitler ve zaman yardımcıları.

TÜM katmanlar bu modüldeki tipleri kullanır. Türkçe enum DEĞERLERİ jüriye/operatöre
görünen metinlerdir; alan adları koda uygun İngilizce kalır.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# ─────────────────────────── Zaman ───────────────────────────

_TIMECODE_RE = re.compile(r"^(?:(\d+):)?([0-5]?\d):([0-5]\d)$")

Seconds = Annotated[float, Field(ge=0.0, description="Video başından itibaren saniye")]
Confidence = Annotated[float, Field(ge=0.0, le=1.0, description="Güven skoru [0,1]")]


def to_timecode(seconds: float) -> str:
    """3.7 -> '00:03' · 75.2 -> '01:15' · 3675.0 -> '1:01:15'.

    Şartnamedeki ``"time": "00:15"`` formatını üretir. Bir saatten uzun videolarda
    ``H:MM:SS`` biçimine genişler.
    """
    if seconds < 0:
        raise ValueError(f"negatif zaman: {seconds}")
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def from_timecode(tc: str) -> float:
    """'00:15' -> 15.0 · '1:01:15' -> 3675.0. Ters dönüşüm (eval/anotasyon için)."""
    m = _TIMECODE_RE.match(tc.strip())
    if not m:
        raise ValueError(f"geçersiz zaman kodu: {tc!r} (beklenen 'MM:SS' veya 'H:MM:SS')")
    hours = int(m.group(1) or 0)
    return hours * 3600 + int(m.group(2)) * 60 + int(m.group(3))


# ─────────────────────────── Enum'lar ───────────────────────────


class RiskLevel(StrEnum):
    """Şartnamedeki ``"risk": "Yüksek"`` alanının izinli değerleri.

    Sıralıdır; karşılaştırma için :func:`risk_rank` kullanın.
    """

    YOK = "Yok"
    DUSUK = "Düşük"
    ORTA = "Orta"
    YUKSEK = "Yüksek"
    KRITIK = "Kritik"


_RISK_ORDER: dict[str, int] = {
    RiskLevel.YOK: 0,
    RiskLevel.DUSUK: 1,
    RiskLevel.ORTA: 2,
    RiskLevel.YUKSEK: 3,
    RiskLevel.KRITIK: 4,
}


def risk_rank(level: RiskLevel) -> int:
    """Sıralı karşılaştırma için sayısal derece (emniyet bariyeri bunu kullanır)."""
    return _RISK_ORDER[level]


class Severity(StrEnum):
    """Tekil olayın ciddiyeti (video geneli riskten AYRI)."""

    BILGI = "bilgi"
    DUSUK = "düşük"
    ORTA = "orta"
    YUKSEK = "yüksek"
    KRITIK = "kritik"


class EventPhase(StrEnum):
    """Şartname: 'olayların başlangıç, gelişim ve sonuç süreçlerini ayırt edebilmelidir'."""

    BASLANGIC = "başlangıç"
    GELISIM = "gelişim"
    SONUC = "sonuç"


class EvidenceSource(StrEnum):
    """Bir olgunun nereden geldiği. Açıklanabilirliğin temel taşı.

    ``VLM`` dışındakiler DETERMİNİSTİK kaynaklardır; verifier düğümü VLM iddialarını
    yalnızca deterministik kaynaklara karşı doğrular.
    """

    DETECTOR = "detector"  # nesne/kişi tespiti
    TRACKER = "tracker"  # takip (kimlik sürekliliği, hız)
    POSE = "pose"  # poz kestirimi (düşme, hareketsizlik)
    ZONE = "zone"  # bölge/ROI mantığı
    AUDIO = "audio"  # ses olayı etiketleme
    ASR = "asr"  # konuşma tanıma
    MOTION = "motion"  # hareket enerjisi / optik akış
    VLM = "vlm"  # görsel-dil modeli çıkarımı (DOĞRULANMASI GEREKİR)
    OPERATOR = "operator"  # operatörün diyalogda verdiği bilgi
    MEMORY = "memory"  # epizodik bellekten gelen geçmiş olay

    @property
    def is_deterministic(self) -> bool:
        return self not in (EvidenceSource.VLM, EvidenceSource.MEMORY)


class ActionPriority(StrEnum):
    P0 = "P0"  # derhal (< 1 dk)
    P1 = "P1"  # acil (< 15 dk)
    P2 = "P2"  # planlı (< 24 sa)
    P3 = "P3"  # bilgilendirme / takip


class AnalysisDepth(StrEnum):
    """`triage` düğümünün LLM ile seçtiği strateji — 'statik olmayan pipeline' kanıtı."""

    HIZLI_TARAMA = "hizli_tarama"  # düşük fps, sadece deterministik algı
    STANDART = "standart"  # normal segment analizi
    DERIN = "derin"  # yüksek fps + kaba→ince temellendirme
    HEDEFLI = "hedefli"  # operatörün sorduğu belirli aralık


# ─────────────────────────── Temel model ───────────────────────────


class GozcuModel(BaseModel):
    """Projedeki tüm şemaların tabanı.

    ``extra="forbid"``: şema dışı alan sessizce geçmez — sözleşme ihlali erken patlar.
    Bu, 4 kişinin paralel çalışmasını güvenli kılan asıl mekanizmadır.
    """

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class BoundingBox(GozcuModel):
    """Normalize edilmiş kutu [0,1] — çözünürlükten bağımsız."""

    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)
    x2: float = Field(ge=0.0, le=1.0)
    y2: float = Field(ge=0.0, le=1.0)

    def model_post_init(self, _ctx: object) -> None:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError(f"geçersiz kutu: ({self.x1},{self.y1})-({self.x2},{self.y2})")

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    @property
    def aspect_ratio(self) -> float:
        """Genişlik/yükseklik. Düşme sezgisi: ayakta ~0.4, yerde >1.2."""
        return (self.x2 - self.x1) / (self.y2 - self.y1)
