"""Shared ChatOpenAI factory with per-task GLM thinking-intensity control.

GLM-5.x thinking models burn most of their latency on reasoning. Volume and
interactive tasks don't need it, so each call site picks a default:

  thinking=False → {"type": "disabled"}  ~3x faster; fine for classification,
                   keyword expansion, extraction, short JSON output
  thinking=True  → {"type": "enabled"}   deep reasoning for quality-critical,
                   low-frequency analysis (scoring, fulltext, trend, digest)

The THINKING env var overrides globally: auto (default, per-task defaults)
| on | off.
"""
from __future__ import annotations

import os

from langchain_openai import ChatOpenAI


def build_chat(
    model: str,
    *,
    thinking: bool = False,
    temperature: float | None = None,
    timeout: float = 120,
    **kwargs,
) -> ChatOpenAI:
    mode = os.environ.get("THINKING", "auto").strip().lower()
    if mode in ("on", "1", "true", "enabled"):
        thinking = True
    elif mode in ("off", "0", "false", "disabled"):
        thinking = False

    params: dict = {
        "timeout": timeout,
        "extra_body": {"thinking": {"type": "enabled" if thinking else "disabled"}},
    }
    if temperature is not None:
        params["temperature"] = temperature
    params.update(kwargs)
    return ChatOpenAI(model=model, **params)
