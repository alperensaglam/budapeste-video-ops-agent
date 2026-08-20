"""Tek video segmentini VLM ile yapılandırılmış biçimde analiz eder."""

from __future__ import annotations

import json
from collections.abc import Sequence

from pydantic import ValidationError

from gozcu.contracts.events import SegmentAnalysis
from gozcu.contracts.evidence import EvidenceItem
from gozcu.contracts.vlm import FrameRef, MessageRole, VLMClient, VLMMessage, VLMRequest
from gozcu.understanding.prompts import load_prompt

SEGMENT_PROMPT_ID = "segment_analysis@v1"


class InvalidSegmentAnalysisError(ValueError):
    """VLM yanıtı SegmentAnalysis sözleşmesine uymadığında."""


def _evidence_context(items: Sequence[EvidenceItem]) -> str:
    if not items:
        return "Kanıt Grafiği henüz gözlem sağlamadı. Yalnızca kareleri kullan."
    lines = []
    for item in items:
        subject = f" subject={item.subject}" if item.subject else ""
        lines.append(
            f"- {item.id} t={item.t:.3f}s source={item.source.value} "
            f"kind={item.kind} conf={item.confidence:.2f}{subject} detail={item.detail}"
        )
    return "\n".join(lines)


class SegmentAnalyzer:
    """L3 ince dikey dilim: kareler → guided JSON → ``SegmentAnalysis``."""

    def __init__(self, client: VLMClient, max_tokens: int = 1200) -> None:
        self._client = client
        self._max_tokens = max_tokens

    async def analyze(
        self,
        *,
        segment_id: str,
        t_start: float,
        t_end: float,
        frames: Sequence[FrameRef],
        evidence: Sequence[EvidenceItem] = (),
    ) -> SegmentAnalysis:
        if t_end < t_start:
            raise ValueError("t_end < t_start")
        if not frames:
            raise ValueError("segment analizi için en az bir kare gerekli")

        user_prompt = load_prompt(
            SEGMENT_PROMPT_ID,
            segment_id=segment_id,
            t_start=f"{t_start:.3f}",
            t_end=f"{t_end:.3f}",
            n_frames=len(frames),
            evidence_context=_evidence_context(evidence),
        )
        request = VLMRequest(
            messages=[
                VLMMessage(
                    role=MessageRole.SYSTEM,
                    text=(
                        "Kanıta bağlı, çekimser ve açıklanabilir video analizi yap. "
                        "Yanıt olarak yalnızca geçerli JSON üret."
                    ),
                ),
                VLMMessage(role=MessageRole.USER, text=user_prompt, frames=list(frames)),
            ],
            model=self._client.model_name,
            temperature=0.0,
            max_tokens=self._max_tokens,
            json_schema=SegmentAnalysis.model_json_schema(),
            seed=0,
            prompt_id=SEGMENT_PROMPT_ID,
        )
        response = await self._client.generate(request)
        if response.schema_valid is False:
            raise InvalidSegmentAnalysisError("VLM yanıtı JSON şemasına uymuyor")
        try:
            raw = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise InvalidSegmentAnalysisError("VLM geçerli JSON üretmedi") from exc
        if not isinstance(raw, dict):
            raise InvalidSegmentAnalysisError("VLM yanıtı JSON nesnesi değil")

        # Segment kimliği/zamanı çıkarım değil kontrol verisidir; modelin bunları
        # değiştirmesine izin vermeyiz.
        raw.update(
            {
                "segment_id": segment_id,
                "t_start": t_start,
                "t_end": t_end,
                "n_frames_used": len(frames),
            }
        )
        try:
            return SegmentAnalysis.model_validate(raw)
        except ValidationError as exc:
            raise InvalidSegmentAnalysisError(f"SegmentAnalysis doğrulanamadı: {exc}") from exc
