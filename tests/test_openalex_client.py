#!/usr/bin/env python3
"""Test the shared OpenAlex throttle client: global pacing + 429 backoff."""
import sys
from pathlib import Path
import threading
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backend.crawler.openalex_client as oc

oc.MIN_INTERVAL = 0.15  # 测试用短间隔

# 1) 多线程并发调用 → 请求间隔仍 >= MIN_INTERVAL（全局节流）
stamps = []
def fake_get(url, params=None, timeout=None):
    stamps.append(time.monotonic())
    class R:
        status_code = 200
        headers = {}
        def json(self): return {"results": ["x"]}
    return R()

with patch.object(oc.httpx, "get", fake_get):
    threads = [threading.Thread(target=lambda: oc.openalex_get("https://api.openalex.org/works")) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

gaps = [b - a for a, b in zip(sorted(stamps), sorted(stamps)[1:])]
assert len(stamps) == 5
assert min(gaps) >= oc.MIN_INTERVAL * 0.9, f"并发请求违反全局节流: gaps={gaps}"
print(f"[1] 5 线程并发全部节流 ✓（最小间隔 {min(gaps):.3f}s >= {oc.MIN_INTERVAL}s）")

# 2) 429 → 按 Retry-After 退避后重试成功
attempts = []
def fake_get_429(url, params=None, timeout=None):
    attempts.append(1)
    class R:
        def __init__(self, code, ra=None):
            self.status_code = code
            self.headers = {"Retry-After": ra} if ra else {}
        def json(self): return {"ok": True}
    if len(attempts) < 3:
        return R(429, "1")
    return R(200)

with patch.object(oc.httpx, "get", fake_get_429):
    result = oc.openalex_get("https://api.openalex.org/works")
assert result == {"ok": True} and len(attempts) == 3, (result, len(attempts))
print("[2] 429 尊重 Retry-After、退避后重试成功 ✓")

# 2b) 超大 Retry-After 是脏信号：封顶 60s 退避继续重试，绝不长睡眠/长熔断
oc._quota_pause_until = 0.0
oc._daily_429_streak = 0
sleeps = []
seq = []
def fake_get_dirty(url, params=None, timeout=None):
    seq.append(1)
    class R:
        def __init__(self, code, ra=None):
            self.status_code = code
            self.headers = {"Retry-After": ra} if ra else {}
        def json(self): return {"ok": True}
    if len(seq) == 1:
        return R(429, "85590")   # 脏的日级 Retry-After
    return R(200)
with patch.object(oc.time, "sleep", side_effect=lambda s: sleeps.append(s)), \
     patch.object(oc.httpx, "get", fake_get_dirty):
    r = oc.openalex_get("https://api.openalex.org/works")
assert r == {"ok": True}, "脏 Retry-After 后应重试成功"
assert all(s <= 60 for s in sleeps), f"退避必须封顶60s: {sleeps}"
assert oc._daily_429_streak == 0, "成功后 streak 应清零"
print("[2b] 脏 Retry-After(85590s)：封顶60s退避后重试成功，绝不长熔断 ✓")

# 2c) 真日配额耗尽：响应体带 budget 结构 → 立即全局暂停至重置（有判据，非盲信header）
oc._quota_pause_until = 0.0
oc._daily_429_streak = 0
sleeps2 = []
http_calls = []
def fake_get_budget(url, params=None, timeout=None):
    http_calls.append(1)
    class R:
        status_code = 429
        headers = {"Retry-After": "81733"}
        text = '{"error":"Rate limit exceeded","message":"Insufficient budget. This request costs $0.001 but you only have $0.0001 remaining. Resets at midnight UTC.","dailyRemainingUsd":0.0001}'
        def json(self): return {}
    return R()
with patch.object(oc.time, "sleep", side_effect=lambda s: sleeps2.append(s)), \
     patch.object(oc.httpx, "get", fake_get_budget):
    r = oc.openalex_get("https://api.openalex.org/works")
    assert r is None, "真配额耗尽应立即放弃"
    assert len(http_calls) == 1, f"应只发一次请求即停: {len(http_calls)}"
    assert all(s <= oc.MIN_INTERVAL + 0.01 for s in sleeps2), f"只允许节流sleep，不应退避: {sleeps2}"
    pause_left = oc._quota_pause_until - oc.time.monotonic()
    assert 0 < pause_left <= 24 * 3600 + 5, f"暂停应至UTC重置: {pause_left}"
oc._quota_pause_until = 0.0
print("[2c] 真配额耗尽（body判据）：一次请求即停，暂停至重置 ✓")

# 3) 确定性 4xx 不重试
n = []
def fake_get_404(url, params=None, timeout=None):
    n.append(1)
    class R:
        status_code = 404
        headers = {}
        def json(self): return {}
    return R()
with patch.object(oc.httpx, "get", fake_get_404):
    assert oc.openalex_get("https://api.openalex.org/works") is None
assert len(n) == 1, "404 不应重试"
print("[3] 404 立即放弃不重试 ✓")

# 4) mailto 注入 polite pool 邮箱
captured = {}
def fake_get_mailto(url, params=None, timeout=None):
    captured.update(params or {})
    class R:
        status_code = 200
        headers = {}
        def json(self): return {}
    return R()
with patch.dict("os.environ", {"OPENALEX_EMAIL": "real@example.com"}):
    with patch.object(oc.httpx, "get", fake_get_mailto):
        oc.openalex_get("https://api.openalex.org/works", {"search": "x"})
assert captured.get("mailto") == "real@example.com"
print("[4] OPENALEX_EMAIL 注入请求参数（polite pool）✓")

print("\n节流客户端测试全部通过 ✅")
