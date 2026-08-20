"""Sürümlenmiş Türkçe VLM prompt kütüphanesi."""

from __future__ import annotations

from pathlib import Path
from string import Template

PROMPT_ROOT = Path(__file__).with_name("prompts")


def load_prompt(prompt_id: str, **values: object) -> str:
    """``segment_analysis@v1`` biçimindeki kimlikle prompt'u yükleyip doldur."""
    try:
        name, version = prompt_id.split("@", 1)
    except ValueError as exc:
        raise ValueError(f"geçersiz prompt kimliği: {prompt_id!r}") from exc
    path = PROMPT_ROOT / version / f"{name}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"prompt bulunamadı: {prompt_id} ({path})")
    return Template(path.read_text(encoding="utf-8")).substitute(
        {key: str(value) for key, value in values.items()}
    )
