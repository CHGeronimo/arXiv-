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
# 防真熔断的短暂全局暂停（实测 OpenAlex/Cloudflare 的超大 Retry-After
# 是脏信号——同一秒内下一请求即成功，绝不能据此长熔断）
_quota_pause_until = 0.0
_daily_429_streak = 0
_DAILY_STREAK_LIMIT = 3     # 连续 N 次日级429才短暂暂停
_PAUSE_ON_STREAK = 600.0    # 暂停10分钟，不是6小时
_BACKOFF_CAP = 60.0         # 一切退避封顶60s


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


def quota_paused() -> bool:
    """True while the defensive short pause is active."""
    return time.monotonic() < _quota_pause_until


def openalex_get(url: str, params: dict | None = None, timeout: float = 30) -> dict | None:
    """Rate-limited GET returning parsed JSON, or None after exhausting retries.

    实测教训（2026-09-05）：OpenAlex 的 429 由 Cloudflare 边缘间歇性发出，
    Retry-After 可能给出 80000+ 秒的脏值而同一秒内下一请求即成功——
    因此一律 cap 到 60s 退避；只有连续 _DAILY_STREAK_LIMIT 次日级 429
    才暂停 _PAUSE_ON_STREAK（10分钟）作为真熔断的防御。
    """
    global _quota_pause_until, _daily_429_streak
    if time.monotonic() < _quota_pause_until:
        return None

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
            # 真熔断判据：OpenAlex 日配额耗尽时响应体带 budget 结构
            # （"Insufficient budget...dailyRemainingUsd"，额度1000credits/天，
            #  每请求$0.001，UTC午夜重置）；Cloudflare 抖动性 429 无此结构
            body = ""
            try:
                body = resp.text[:300]
            except Exception:
                pass
            retry_after = resp.headers.get("Retry-After", "")
            raw = int(retry_after) if retry_after.isdigit() else 5 * 2 ** (attempt - 1)
            if "Insufficient budget" in body or "dailyRemainingUsd" in body:
                _quota_pause_until = time.monotonic() + min(raw, 24 * 3600)
                logger.warning(
                    f"OpenAlex 日配额真耗尽（{body[:100]}），暂停至 UTC 午夜重置，任务收尾"
                )
                return None
            # 抖动：退避封顶 60s 继续重试（同秒内下一请求常即成功）
            backoff = min(raw, _BACKOFF_CAP)
            logger.warning(f"OpenAlex 429 限流（Retry-After={raw}s 视为抖动），退避 {backoff}s（第 {attempt}/{MAX_RETRIES} 次）")
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
            _daily_429_streak = 0  # 成功即清零
            return resp.json()
        except Exception as e:
            logger.warning(f"OpenAlex 响应解析失败: {e}")
            return None

    logger.error(f"OpenAlex 请求在 {MAX_RETRIES} 次重试后仍失败: {url}")
    return None
