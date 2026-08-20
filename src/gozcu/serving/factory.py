"""Donanım profiline göre VLM istemcisi kurma fabrikası."""

from __future__ import annotations

from gozcu.config import Profile, VLMBackend
from gozcu.contracts.vlm import VLMClient
from gozcu.serving.cassette import CassetteVLM, RecordingVLM, cassette_for
from gozcu.serving.vllm_client import VLLMClient


def create_vlm_client(profile: Profile, cassette_name: str = "default") -> VLMClient:
    """Profilin backend ve kaset moduna uygun istemciyi oluştur."""
    if profile.vlm.backend is VLMBackend.CASSETTE:
        return CassetteVLM(cassette_for(profile, cassette_name), profile.vlm.model)
    if profile.vlm.backend is not VLMBackend.VLLM:
        raise ValueError(f"desteklenmeyen gerçek VLM backend'i: {profile.vlm.backend.value}")

    live = VLLMClient(profile.vlm)
    if profile.cassette_mode == "record":
        return RecordingVLM(live, cassette_for(profile, cassette_name))
    return live
