"""OpenAI-uyumlu Slot B istemcisinin CPU'da çalışan sözleşme testleri."""

from __future__ import annotations

import base64
import hashlib
import json
from types import SimpleNamespace
from typing import Any

import pytest

from gozcu.config import VLMBackend, VLMConfig
from gozcu.contracts.events import SegmentAnalysis
from gozcu.contracts.vlm import FrameRef, MessageRole, VLMMessage, VLMRequest
from gozcu.serving import VLLMClient, VLLMClientError


def _analysis_json() -> str:
    return json.dumps(
        {
            "segment_id": "seg_001",
            "t_start": 0.0,
            "t_end": 10.0,
            "description": "Bir kişi depo koridorunda yürüyor.",
            "observed_actions": ["yürüme"],
            "observed_objects": ["kişi"],
            "anomaly": False,
            "anomaly_reason": "",
            "candidate_events": [],
            "needs_closer_look": False,
            "confidence": 0.91,
            "n_frames_used": 1,
        },
        ensure_ascii=False,
    )


def _frame() -> FrameRef:
    data = b"\x89PNG\r\n\x1a\nphase-1-l3"
    return FrameRef(
        t=2.5,
        sha256=hashlib.sha256(data).hexdigest(),
        width=320,
        height=180,
        data_b64=base64.b64encode(data).decode("ascii"),
    )


class _FakeCompletions:
    def __init__(self, text: str) -> None:
        self.text = text
        self.kwargs: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(
            model="vlm",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.text),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(prompt_tokens=40, completion_tokens=25),
        )


class _FakeOpenAI:
    def __init__(self, text: str) -> None:
        self.completions = _FakeCompletions(text)
        self.chat = SimpleNamespace(completions=self.completions)


def _config() -> VLMConfig:
    return VLMConfig(
        backend=VLMBackend.VLLM,
        model="vlm",
        base_url="http://127.0.0.1:8000/v1",
        guided_json=True,
    )


@pytest.mark.asyncio
async def test_slot_b_istegi_gorsel_ve_guided_json_ile_gider() -> None:
    fake = _FakeOpenAI(_analysis_json())
    client = VLLMClient(_config(), client=fake)
    request = VLMRequest(
        messages=[
            VLMMessage(role=MessageRole.USER, text="Bu segmenti analiz et", frames=[_frame()])
        ],
        model="vlm",
        json_schema=SegmentAnalysis.model_json_schema(),
        prompt_id="segment_analysis@v1",
    )

    response = await client.generate(request)

    assert response.model == "vlm"
    assert response.schema_valid is True
    assert response.usage.prompt_tokens == 40
    sent = fake.completions.kwargs
    assert sent is not None
    assert sent["model"] == "vlm"
    assert sent["response_format"]["type"] == "json_schema"
    assert sent["response_format"]["json_schema"]["strict"] is True
    content = sent["messages"][0]["content"]
    assert any(part["type"] == "image_url" for part in content)
    image = next(part for part in content if part["type"] == "image_url")
    assert image["image_url"]["url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_sema_disi_yanit_gecersiz_isaretlenir() -> None:
    fake = _FakeOpenAI('{"description":"eksik alanlar"}')
    client = VLLMClient(_config(), client=fake)
    request = VLMRequest(
        messages=[VLMMessage(role=MessageRole.USER, text="analiz")],
        model="vlm",
        json_schema=SegmentAnalysis.model_json_schema(),
        prompt_id="segment_analysis@v1",
    )

    response = await client.generate(request)

    assert response.schema_valid is False


@pytest.mark.asyncio
async def test_kare_hashi_eslesmezse_api_cagrilmaz() -> None:
    fake = _FakeOpenAI(_analysis_json())
    client = VLLMClient(_config(), client=fake)
    frame = _frame().model_copy(update={"sha256": "0" * 64})
    request = VLMRequest(
        messages=[VLMMessage(role=MessageRole.USER, frames=[frame])],
        model="vlm",
    )

    with pytest.raises(VLLMClientError, match="SHA-256 uyuşmuyor"):
        await client.generate(request)
    assert fake.completions.kwargs is None
