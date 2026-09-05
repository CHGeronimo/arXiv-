"""Shared throttled OpenAlex HTTP client.

Every OpenAlex call in the project (DBLP venue search, keyword search,
Crossref abstract backfill) funnels through one process-wide rate limiter:
a global lock enforcing a minimum interval between request starts, plus
429-aware exponential backoff honoring Retry-After. Concurrent crawlers
(e.g. manual "全部爬取" firing DBLP and S2 search together) therefore
cannot trip OpenAlex's rate limit against each other.

Set OPENALEX_EMAIL (ai/.env) to a real address to join OpenAlex's polite
pool, which gets noticeably higher limits than an anonymous client.
"""
from __future__ import annotations

import logging
import os
import threading
import time

import httpx

logger = logging.getLogger(__name__)

MIN_INTERVAL = float(os.environ.get("OPENALEX_MIN_INTERVAL", "1.2"))  # seconds between request starts
MAX_RETRIES = 4

_lock = threading.Lock()
_last_request = 0.0
# 日配额熔断窗口：Retry-After 超过阈值视为"今天别再打了"，
# 窗口内所有请求直接返回 None，让任务快速收尾而不是空转重试
_quota_pause_until = 0.0
_QUOTA_PAUSE_THRESHOLD = 600.0  # 秒；超过即视为日级熔断
_BACKOFF_CAP = 60.0


def _mailto() -> str:
    return os.environ.get("OPENALEX_EMAIL", "openalex@arxivsci-daily.local")


def _throttle() -> None:
    """Block until MIN_INTERVAL has passed since the previous request start."""
    global _last_request
    with _lock:
        wait = _last_request + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()


def openalex_get(url: str, params: dict | None = None, timeout: float = 30) -> dict | None:
    """Rate-limited GET returning parsed JSON, or None after exhausting retries.

    429 → Retry-After-aware backoff (capped) / 5xx → short retries / other 4xx →
    give up. Retry-After or backoff exceeding _QUOTA_PAUSE_THRESHOLD means the
    daily quota is burnt: pause ALL OpenAlex traffic for that window instead of
    sleeping inside one request, so crawl jobs finish immediately.
    """
    global _quota_pause_until
    if time.monotonic() < _quota_pause_until:
        return None  # 日配额熔断窗口内，快速放弃

    params = dict(params or {})
    params.setdefault("mailto", _mailto())

    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()
        try:
            resp = httpx.get(url, params=params, timeout=timeout)
        except Exception as e:
            logger.warning(f"OpenAlex 请求失败（第 {attempt}/{MAX_RETRIES} 次）: {e}")
            time.sleep(min(3 * attempt, _BACKOFF_CAP))
            continue

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "")
            backoff = int(retry_after) if retry_after.isdigit() else min(5 * 2 ** (attempt - 1), _BACKOFF_CAP)
            if backoff > _QUOTA_PAUSE_THRESHOLD:
                # 日级配额熔断（Retry-After 可能高达 86400s）：
                # 全局暂停并放弃本请求，绝不 sleep 一整天
                _quota_pause_until = time.monotonic() + min(backoff, 6 * 3600)
                logger.warning(
                    f"OpenAlex 日配额熔断（Retry-After={backoff}s），全局暂停 OpenAlex 请求 "
                    f"{min(backoff, 6*3600)//60} 分钟，本轮任务提前收尾"
                )
                return None
            backoff = min(backoff, _BACKOFF_CAP)
            logger.warning(f"OpenAlex 429 限流，{backoff}s 后重试（第 {attempt}/{MAX_RETRIES} 次）")
            time.sleep(backoff)
            continue
        if resp.status_code >= 500:
            logger.warning(f"OpenAlex {resp.status_code}（第 {attempt}/{MAX_RETRIES} 次），5s 后重试")
            time.sleep(5)
            continue
        if resp.status_code >= 400:
            logger.error(f"OpenAlex 请求错误 {resp.status_code}（不重试）: {url}")
            return None
        try:
            return resp.json()
        except Exception as e:
            logger.warning(f"OpenAlex 响应解析失败: {e}")
            return None

    logger.error(f"OpenAlex 请求在 {MAX_RETRIES} 次重试后仍失败: {url}")
    return None
