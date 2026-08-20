"""OpenAI uyumlu vLLM hizmeti için gerçek çok-ortamlı istemci."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import mimetypes
import re
import time
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from gozcu.config import VLMConfig
from gozcu.contracts.vlm import FrameRef, MessageRole, VLMRequest, VLMResponse, VLMUsage


class VLLMClientError(RuntimeError):
    """vLLM isteği hazırlanamadığında veya hizmet geçersiz yanıt verdiğinde."""


def _schema_name(prompt_id: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", prompt_id).strip("-")
    return normalized or "gozcu-output"


def _detect_mime(data: bytes, path: str | None = None) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    guessed = mimetypes.guess_type(path or "")[0]
    return guessed if guessed and guessed.startswith("image/") else "image/jpeg"


def _frame_data_url(frame: FrameRef) -> str:
    """FrameRef'i OpenAI Vision biçiminde veri URL'sine çevir ve hash'i doğrula."""
    if frame.data_b64:
        encoded = frame.data_b64
        if encoded.startswith("data:"):
            try:
                header, encoded = encoded.split(",", 1)
            except ValueError as exc:
                raise VLLMClientError("geçersiz data URL") from exc
            mime = header.removeprefix("data:").split(";", 1)[0] or "image/jpeg"
        else:
            mime = "image/jpeg"
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise VLLMClientError("FrameRef.data_b64 geçerli base64 değil") from exc
        if not frame.data_b64.startswith("data:"):
            mime = _detect_mime(data)
    elif frame.path:
        path = Path(frame.path)
        if not path.is_file():
            raise VLLMClientError(f"kare dosyası bulunamadı: {path}")
        data = path.read_bytes()
        mime = _detect_mime(data, frame.path)
        encoded = base64.b64encode(data).decode("ascii")
    else:
        raise VLLMClientError("gerçek VLM çağrısı için karede path veya data_b64 gerekli")

    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_hash != frame.sha256:
        raise VLLMClientError(
            f"kare SHA-256 uyuşmuyor: beklenen={frame.sha256} gerçek={actual_hash}"
        )
    return f"data:{mime};base64,{encoded}"


def _message_payload(request: VLMRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for message in request.messages:
        role = message.role.value
        text = message.text
        if message.role is MessageRole.TOOL:
            # VLMMessage sözleşmesinde tool_call_id yok; OpenAI'nin tool rolünü taklit
            # etmek yerine kaynağı açıkça işaretlenmiş kullanıcı bağlamına dönüştürürüz.
            role = MessageRole.USER.value
            text = f"[Araç sonucu]\n{text}"
        if not message.frames:
            messages.append({"role": role, "content": text})
            continue

        content: list[dict[str, Any]] = []
        if text:
            content.append({"type": "text", "text": text})
        for frame in message.frames:
            content.append({"type": "text", "text": f"[video zamanı: {frame.t:.3f} s]"})
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": _frame_data_url(frame)},
                }
            )
        messages.append({"role": role, "content": content})
    return messages


def _schema_is_valid(text: str, schema: dict[str, Any] | None) -> bool | None:
    if schema is None:
        return None
    try:
        payload = json.loads(text)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(payload)
    except (json.JSONDecodeError, SchemaError, ValidationError):
        return False
    return True


class VLLMClient:
    """OpenAI uyumlu endpoint üzerinden gerçek ``VLMClient`` uygulaması.

    ``client`` parametresi yalnızca birim testlerinde sahte OpenAI istemcisi enjekte
    etmek içindir. Normal kullanımda ``openai.AsyncOpenAI`` tembel yüklenir.
    """

    def __init__(self, config: VLMConfig, client: Any | None = None) -> None:
        self._config = config
        self._model_name = config.model
        if client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:  # pragma: no cover - ortam bağımlılığı
                raise RuntimeError(
                    "gerçek vLLM istemcisi için `pip install -e .[understanding]` çalıştırın"
                ) from exc
            client = AsyncOpenAI(
                base_url=config.resolved_base_url(),
                api_key=config.resolved_api_key(),
                timeout=config.request_timeout_s,
                max_retries=0,
            )
        self._client = client

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, request: VLMRequest) -> VLMResponse:
        model = request.model or self._model_name
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": _message_payload(request),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.seed is not None:
            kwargs["seed"] = request.seed
        if request.json_schema is not None and self._config.guided_json:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": _schema_name(request.prompt_id),
                    "schema": request.json_schema,
                    "strict": True,
                },
            }

        started = time.perf_counter()
        try:
            completion = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise VLLMClientError(f"vLLM çağrısı başarısız: {type(exc).__name__}: {exc}") from exc
        latency_ms = (time.perf_counter() - started) * 1000.0

        if not completion.choices:
            raise VLLMClientError("vLLM boş choices listesi döndürdü")
        choice = completion.choices[0]
        text = choice.message.content
        if not isinstance(text, str) or not text.strip():
            raise VLLMClientError("vLLM boş metin döndürdü")

        usage = getattr(completion, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        finish_reason = getattr(choice, "finish_reason", "stop") or "stop"
        returned_model = getattr(completion, "model", None) or model
        return VLMResponse(
            text=text,
            model=str(returned_model),
            usage=VLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                ttft_ms=None,
            ),
            finish_reason=str(finish_reason),
            schema_valid=_schema_is_valid(text, request.json_schema),
        )
