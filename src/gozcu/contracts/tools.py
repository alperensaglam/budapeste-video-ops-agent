"""Araç (tool) protokolü — DONDURULMUŞ SINIR #3.

Şartname değerlendirme kriteri (Bölüm 7, Teknik İmplementasyon %35):
    "Mock fonksiyonların ajanın araçları olarak başarıyla kullanılması"
    "dinamik araç seçimi ... hata işleme"

Alperen bu protokolü TANIMLAR (ajan bunu tüketir); İbrahim mock araçları,
Hasan algı araçlarını, Emre VLM araçlarını bu protokole göre IMPLEMENTE eder.
Böylece dördü birbirini beklemeden çalışır.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from gozcu.contracts.common import GozcuModel


class ToolCategory(StrEnum):
    """Ajanın araç seçim uzayı. Router önce kategori, sonra araç seçer."""

    PERCEPTION = "perception"  # Kanıt Grafiği'ni sorgula / yeni algı çalıştır  [Hasan]
    UNDERSTANDING = "understanding"  # VLM'e sor, segment analiz et, yakınlaş     [Emre]
    KNOWLEDGE = "knowledge"  # SOP RAG, bölge bilgisi, vardiya listesi         [İbrahim]
    MEMORY = "memory"  # epizodik bellek: geçmiş benzer olaylar          [Alperen]
    ACTION = "action"  # mock kurumsal sistemler (dispatch, notify, ...) [İbrahim]


class ToolErrorKind(StrEnum):
    """Hata enjeksiyon motorunun üretebildiği arıza modları.

    Ajanın her biri için farklı kurtarma stratejisi olmalı — Faz 3 kaos testi bunu ölçer.
    """

    TIMEOUT = "timeout"  # -> yeniden dene (üstel geri çekilme)
    UNAVAILABLE = "unavailable"  # -> alternatif araca geç (fallback)
    RATE_LIMIT = "rate_limit"  # -> bekle + yeniden dene
    INVALID_RESPONSE = "invalid_response"  # -> onarım turu veya alternatif
    PARTIAL = "partial"  # -> kısmi sonuçla devam, eksiği bildir
    NOT_FOUND = "not_found"  # -> operatöre sor (ask_user)
    PERMISSION_DENIED = "permission_denied"  # -> yetki yükselt / operatöre bildir


class ToolSpec(GozcuModel):
    """Aracın ajana tanıtımı. LLM'e verilen JSON şeması buradan üretilir."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    category: ToolCategory
    description: str = Field(
        min_length=10,
        description="LLM'in NE ZAMAN kullanacağını anlaması için Türkçe açıklama. "
        "Bu metin araç seçim doğruluğunu doğrudan etkiler — özenle yazın.",
    )
    parameters_schema: dict[str, Any] = Field(
        description="JSON Schema (Pydantic model_json_schema çıktısı)"
    )
    returns_schema: dict[str, Any] = Field(default_factory=dict)
    is_irreversible: bool = Field(
        default=False,
        description="True ise ajan yürütmeden ÖNCE operatör onayı ister (HITL). "
        "112 arama, saha kapatma, alarm çalma gibi.",
    )
    fallback_tools: list[str] = Field(
        default_factory=list,
        description="Bu araç UNAVAILABLE dönerse sırayla denenecek alternatifler",
    )
    typical_latency_ms: float = Field(default=100.0, ge=0.0)
    max_retries: int = Field(default=2, ge=0, le=5)


class ToolCall(GozcuModel):
    """Ajanın yaptığı tek araç çağrısı — trace ve KPI'ın birimi."""

    call_id: str
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="", description="Ajan bunu NEDEN seçti (Türkçe, trace'te görünür)")
    attempt: int = Field(default=1, ge=1)


class ToolResult(GozcuModel):
    """Araç çağrısının sonucu. Hata da başarı da bu tiple döner — istisna fırlatılmaz."""

    call_id: str
    tool: str
    ok: bool
    data: Any = None
    error_kind: ToolErrorKind | None = None
    error_message: str = ""
    latency_ms: float = Field(default=0.0, ge=0.0)
    attempts: int = Field(default=1, ge=1)
    recovered_by: str | None = None

    @property
    def should_retry(self) -> bool:
        """Bu hata tipi yeniden denemeye değer mi?"""
        return self.error_kind in (
            ToolErrorKind.TIMEOUT,
            ToolErrorKind.RATE_LIMIT,
            ToolErrorKind.INVALID_RESPONSE,
        )

    @property
    def should_fallback(self) -> bool:
        """Alternatif araca geçilmeli mi?"""
        return self.error_kind in (ToolErrorKind.UNAVAILABLE, ToolErrorKind.PERMISSION_DENIED)


@runtime_checkable
class Tool(Protocol):
    """Her aracın uyması gereken arayüz. Dört kişi de buna göre implemente eder."""

    spec: ToolSpec

    async def __call__(self, **kwargs: Any) -> ToolResult:  # pragma: no cover - protokol
        ...
