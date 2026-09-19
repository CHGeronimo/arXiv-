"""Shared ChatOpenAI factory with per-task GLM thinking-intensity control.

GLM-5.x thinking models burn most of their latency on reasoning. Volume and
interactive tasks don't need it, so each call site picks a default:

  thinking=False → {"type": "disabled"}  ~3x faster; fine for classification,
                   keyword expansion, extraction, short JSON output
  thinking=True  → {"type": "enabled"}   deep reasoning for quality-critical,
                   low-frequency analysis (scoring, fulltext, trend, digest)

The THINKING env var overrides globally: auto (default, per-task defaults)
| on | off.

全局 LLM 频率控制（2026-09-12 实锤 Error 1302 速率限制）：
所有 LLM 请求经此处的信号量+最小间隔节流，并对 429/1302 做指数退避重试。
LLM_MAX_CONCURRENT（默认2）与 LLM_MIN_INTERVAL（默认1.0s，≈60次/分）可调。
"""
from __future__ import annotations

import logging
import os
import threading
import time

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# ── 全局频率控制 ─────────────────────────────────────────────
LLM_MAX_CONCURRENT = int(os.environ.get("LLM_MAX_CONCURRENT", "2"))
LLM_MIN_INTERVAL = float(os.environ.get("LLM_MIN_INTERVAL", "1.0"))
_LLM_SEM = threading.Semaphore(LLM_MAX_CONCURRENT)
_llm_lock = threading.Lock()
_llm_last = 0.0

_RATE_LIMIT_MARKERS = ("1302", "429", "速率限制", "rate limit", "Rate limit")


def _acquire_llm_slot() -> None:
    """占一个并发槽并对请求起点做全局最小间隔（所有 LLM 调用共享）。"""
    global _llm_last
    _LLM_SEM.acquire()
    try:
        with _llm_lock:
            wait = _llm_last + LLM_MIN_INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            _llm_last = time.monotonic()
    except Exception:
        _LLM_SEM.release()
        raise


def _is_rate_limit_error(e: Exception) -> bool:
    msg = str(e)
    return any(m in msg for m in _RATE_LIMIT_MARKERS)


class _RateLimitedChat(ChatOpenAI):
    """invoke 级节流 + 429/1302 指数退避重试（3/6/9s，共3次）。"""

    def invoke(self, input, *args, **kwargs):  # noqa: A002
        last_err: Exception | None = None
        for attempt in range(4):
            _acquire_llm_slot()
            try:
                return super().invoke(input, *args, **kwargs)
            except Exception as e:
                if _is_rate_limit_error(e) and attempt < 3:
                    wait = 3 * (attempt + 1)
                    logger.warning(f"GLM 限流（{str(e)[:80]}...），退避 {wait}s 后重试（第 {attempt + 1}/3 次）")
                    time.sleep(wait)
                    last_err = e
                    continue
                raise
            finally:
                _LLM_SEM.release()
        raise last_err  # pragma: no cover — 4次全限流


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

    params: dict = {"timeout": timeout}
    # thinking 开关是 GLM 专属参数：DeepSeek 等其他 OpenAI 兼容端点不认识，
    # 可能直接 400——只在 bigmodel 端点上附带
    effective_base = kwargs.get("base_url") or os.environ.get("OPENAI_BASE_URL", "") or ""
    if "bigmodel" in effective_base:
        params["extra_body"] = {"thinking": {"type": "enabled" if thinking else "disabled"}}
    if temperature is not None:
        params["temperature"] = temperature
    params.update(kwargs)
    return _RateLimitedChat(model=model, **params)
