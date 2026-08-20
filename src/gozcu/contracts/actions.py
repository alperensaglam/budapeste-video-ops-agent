"""Aksiyon önerisi sözleşmeleri — karar destek katmanının çıktısı.

Şartname, Bölüm 4:
    "Geliştirilen çözüm yalnızca analiz yapan bir sistem değil, aynı zamanda bir
     karar destek sistemi olmalıdır."

Her aksiyon üç şeye bağlıdır:
  1. hangi OLAYDAN doğduğu (triggering_event_ids),
  2. hangi SOP maddesine dayandığı (sop_ref),
  3. hangi MOCK ARACIN onu yürüteceği (tool).
Bu üçlü, "uydurulmuş öneri"yi yapısal olarak imkânsız kılar.

Sahibi: İbrahim (L5).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from gozcu.contracts.common import ActionPriority, GozcuModel


class ActionStatus(StrEnum):
    ONERILDI = "önerildi"
    ONAY_BEKLIYOR = "operatör_onayı_bekliyor"
    ONAYLANDI = "onaylandı"
    REDDEDILDI = "reddedildi"
    YURUTULUYOR = "yürütülüyor"
    TAMAMLANDI = "tamamlandı"
    BASARISIZ = "başarısız"


class RecommendedAction(GozcuModel):
    """Operatöre sunulan, gerekçeli ve yürütülebilir aksiyon."""

    id: str = Field(pattern=r"^act_\d{3,}$")
    action: str = Field(min_length=1, description="Türkçe emir kipi, örn. Sağlık ekibini çağır")
    priority: ActionPriority
    owner: str = Field(description="saglik_birimi, guvenlik, vardiya_amiri, bakim, isg")
    deadline_sec: int | None = Field(default=None, ge=0, description="Hedef müdahale süresi")
    tool: str | None = Field(
        default=None, description="Bu aksiyonu yürütecek mock aracın adı (varsa)"
    )
    tool_args: dict[str, object] = Field(default_factory=dict)
    sop_ref: str | None = Field(
        default=None, description="Dayandığı prosedür maddesi, örn. ISG-PR-014 madde 4.2"
    )
    triggering_event_ids: list[str] = Field(
        default_factory=list, description="Bu aksiyonu doğuran olay(lar) — BOŞ OLAMAZ prod'da"
    )
    rationale: str = Field(default="", description="Neden bu aksiyon — Türkçe")
    status: ActionStatus = ActionStatus.ONERILDI
    requires_confirmation: bool = Field(
        default=False,
        description="Geri alınamaz aksiyonlar (112 arama, saha kapatma) True olmalı. "
        "LangGraph interrupt() ile operatör onayı beklenir.",
    )

    def to_sartname_action(self) -> str:
        """Şartnamedeki birebir biçim: düz metin dizisi elemanı."""
        return self.action


class ActionExecutionResult(GozcuModel):
    """Mock aracın yürütme sonucu. Hata enjeksiyon motoru da bu tipi üretir."""

    action_id: str
    tool: str
    ok: bool
    status: ActionStatus
    latency_ms: float = Field(ge=0.0)
    attempts: int = Field(default=1, ge=1, description="Yeniden denemeler dahil toplam")
    response: dict[str, object] = Field(default_factory=dict)
    error_kind: str | None = Field(
        default=None, description="timeout, unavailable, rate_limit, invalid_response, partial"
    )
    error_message: str = ""
    recovered_by: str | None = Field(
        default=None,
        description="Hata sonrası kurtarma yolu: retry, fallback_tool, degraded, ask_user. "
        "Hata Kurtarma Oranı KPI'ı bu alandan hesaplanır.",
    )
