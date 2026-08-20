"""GÖZCÜ veri sözleşmeleri — TEK GERÇEK KAYNAK.

Bu paket Faz 0'da DONDURULUR. Değişiklik yapmak için:
  1. docs/decisions/ altına ADR yaz,
  2. schema_version'ı artır,
  3. dört katman sahibinin de onayını al (PR review).

Şemalar dört kişinin birbirini beklemeden çalışmasını sağlayan asıl mekanizmadır.
"""

from gozcu.contracts.actions import (
    ActionExecutionResult,
    ActionStatus,
    RecommendedAction,
)
from gozcu.contracts.common import (
    ActionPriority,
    AnalysisDepth,
    BoundingBox,
    Confidence,
    EventPhase,
    EvidenceSource,
    GozcuModel,
    RiskLevel,
    Seconds,
    Severity,
    from_timecode,
    risk_rank,
    to_timecode,
)
from gozcu.contracts.events import DetectedEvent, EvidenceRef, SegmentAnalysis
from gozcu.contracts.evidence import (
    EvidenceGraphStats,
    EvidenceItem,
    EvidenceQuery,
    EvidenceQueryResult,
    EvidenceRelation,
    TrackSegment,
)
from gozcu.contracts.report import (
    SARTNAME_REQUIRED_KEYS,
    Abstention,
    AnalysisReport,
    RunMetrics,
)
from gozcu.contracts.risk import RiskAssessment, RiskFactor, SafetyGuardRule
from gozcu.contracts.tools import (
    Tool,
    ToolCall,
    ToolCategory,
    ToolErrorKind,
    ToolResult,
    ToolSpec,
)
from gozcu.contracts.vlm import (
    CassetteEntry,
    FrameRef,
    MessageRole,
    VLMClient,
    VLMMessage,
    VLMRequest,
    VLMResponse,
    VLMUsage,
)

__all__ = [
    "SARTNAME_REQUIRED_KEYS",
    "Abstention",
    "ActionExecutionResult",
    "ActionPriority",
    "ActionStatus",
    "AnalysisDepth",
    "AnalysisReport",
    "BoundingBox",
    "CassetteEntry",
    "Confidence",
    "DetectedEvent",
    "EventPhase",
    "EvidenceGraphStats",
    "EvidenceItem",
    "EvidenceQuery",
    "EvidenceQueryResult",
    "EvidenceRef",
    "EvidenceRelation",
    "EvidenceSource",
    "FrameRef",
    "GozcuModel",
    "MessageRole",
    "RecommendedAction",
    "RiskAssessment",
    "RiskFactor",
    "RiskLevel",
    "RunMetrics",
    "SafetyGuardRule",
    "Seconds",
    "SegmentAnalysis",
    "Severity",
    "Tool",
    "ToolCall",
    "ToolCategory",
    "ToolErrorKind",
    "ToolResult",
    "ToolSpec",
    "TrackSegment",
    "VLMClient",
    "VLMMessage",
    "VLMRequest",
    "VLMResponse",
    "VLMUsage",
    "from_timecode",
    "risk_rank",
    "to_timecode",
]
