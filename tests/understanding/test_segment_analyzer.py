"""Faz 1 / L3 tek-segment analiz akışının sözleşme testleri."""

from __future__ import annotations

import base64
import hashlib
import json

import pytest

from gozcu.contracts.events import SegmentAnalysis
from gozcu.contracts.vlm import FrameRef, MessageRole
from gozcu.serving import ScriptedVLM
from gozcu.understanding import (
    SEGMENT_PROMPT_ID,
    AnalyzeSegmentTool,
    InvalidSegmentAnalysisError,
    SegmentAnalyzer,
)


def _frame() -> FrameRef:
    data = b"phase-1-frame"
    return FrameRef(
        t=4.0,
        sha256=hashlib.sha256(data).hexdigest(),
        width=640,
        height=360,
        data_b64=base64.b64encode(data).decode("ascii"),
    )


def _model_output() -> str:
    return json.dumps(
        {
            "segment_id": "modelin_degistirmeye_calistigi_id",
            "t_start": 90.0,
            "t_end": 99.0,
            "description": "Bir kişi koridorda yürüyor.",
            "observed_actions": ["yürüme"],
            "observed_objects": ["kişi"],
            "anomaly": False,
            "anomaly_reason": "",
            "candidate_events": [],
            "needs_closer_look": False,
            "confidence": 0.86,
            "n_frames_used": 99,
        },
        ensure_ascii=False,
    )


@pytest.mark.asyncio
async def test_tek_segment_segment_analysis_uretir() -> None:
    client = ScriptedVLM(_model_output(), model_name="vlm")
    analyzer = SegmentAnalyzer(client)

    result = await analyzer.analyze(
        segment_id="seg_001",
        t_start=0.0,
        t_end=10.0,
        frames=[_frame()],
    )

    assert isinstance(result, SegmentAnalysis)
    assert result.segment_id == "seg_001"
    assert result.t_start == 0.0
    assert result.t_end == 10.0
    assert result.n_frames_used == 1
    assert result.description == "Bir kişi koridorda yürüyor."

    request = client.calls[0]
    assert request.prompt_id == SEGMENT_PROMPT_ID
    assert request.model == "vlm"
    assert request.temperature == 0.0
    assert request.json_schema == SegmentAnalysis.model_json_schema()
    assert request.messages[0].role is MessageRole.SYSTEM
    assert request.messages[1].frames[0].t == 4.0


@pytest.mark.asyncio
async def test_gecersiz_json_acik_hata_verir() -> None:
    analyzer = SegmentAnalyzer(ScriptedVLM("JSON değil"))

    with pytest.raises(InvalidSegmentAnalysisError, match="geçerli JSON"):
        await analyzer.analyze(
            segment_id="seg_001",
            t_start=0.0,
            t_end=10.0,
            frames=[_frame()],
        )


@pytest.mark.asyncio
async def test_l3_araci_tool_sozlesmesine_uygun_sonuc_dondurur() -> None:
    tool = AnalyzeSegmentTool(SegmentAnalyzer(ScriptedVLM(_model_output(), model_name="vlm")))

    result = await tool(
        call_id="call_001",
        segment_id="seg_001",
        t_start=0.0,
        t_end=10.0,
        frames=[_frame().model_dump(mode="json")],
    )

    assert result.ok is True
    assert result.call_id == "call_001"
    assert result.tool == "analyze_video_segment"
    assert result.data["segment_id"] == "seg_001"
    assert tool.spec.returns_schema == SegmentAnalysis.model_json_schema()
