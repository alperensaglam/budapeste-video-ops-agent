"""Ajanın çağıracağı L3 segment analiz aracı."""

from __future__ import annotations

import time
from typing import Any

from pydantic import Field, ValidationError

from gozcu.contracts.common import GozcuModel
from gozcu.contracts.events import SegmentAnalysis
from gozcu.contracts.evidence import EvidenceItem
from gozcu.contracts.tools import ToolCategory, ToolErrorKind, ToolResult, ToolSpec
from gozcu.contracts.vlm import FrameRef
from gozcu.understanding.segment_analyzer import (
    InvalidSegmentAnalysisError,
    SegmentAnalyzer,
)


class AnalyzeSegmentArgs(GozcuModel):
    segment_id: str
    t_start: float = Field(ge=0.0)
    t_end: float = Field(ge=0.0)
    frames: list[FrameRef] = Field(min_length=1)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class AnalyzeSegmentTool:
    """``Tool`` protokolüne uyan VLM segment analiz aracı."""

    spec = ToolSpec(
        name="analyze_video_segment",
        category=ToolCategory.UNDERSTANDING,
        description=(
            "Bir video zaman aralığındaki kareleri ve deterministik kanıtları VLM ile "
            "yorumlayıp yapılandırılmış Türkçe segment analizi üretir."
        ),
        parameters_schema=AnalyzeSegmentArgs.model_json_schema(),
        returns_schema=SegmentAnalysis.model_json_schema(),
        typical_latency_ms=5000.0,
        max_retries=1,
    )

    def __init__(self, analyzer: SegmentAnalyzer) -> None:
        self._analyzer = analyzer

    async def __call__(self, **kwargs: Any) -> ToolResult:
        call_id = str(kwargs.pop("call_id", "vlm_segment"))
        started = time.perf_counter()
        try:
            args = AnalyzeSegmentArgs.model_validate(kwargs)
            analysis = await self._analyzer.analyze(
                segment_id=args.segment_id,
                t_start=args.t_start,
                t_end=args.t_end,
                frames=args.frames,
                evidence=args.evidence,
            )
        except ValidationError as exc:
            return self._error(call_id, started, ToolErrorKind.INVALID_RESPONSE, str(exc))
        except InvalidSegmentAnalysisError as exc:
            return self._error(call_id, started, ToolErrorKind.INVALID_RESPONSE, str(exc))
        except TimeoutError as exc:
            return self._error(call_id, started, ToolErrorKind.TIMEOUT, str(exc))
        except Exception as exc:
            return self._error(call_id, started, ToolErrorKind.UNAVAILABLE, str(exc))
        return ToolResult(
            call_id=call_id,
            tool=self.spec.name,
            ok=True,
            data=analysis.model_dump(mode="json"),
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )

    def _error(
        self,
        call_id: str,
        started: float,
        kind: ToolErrorKind,
        message: str,
    ) -> ToolResult:
        return ToolResult(
            call_id=call_id,
            tool=self.spec.name,
            ok=False,
            error_kind=kind,
            error_message=message,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
