#!/usr/bin/env python3
"""Test the shared OpenAlex throttle client: global pacing + 429 backoff."""
import sys
from pathlib import Path
import threading
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import crawler.openalex_client as oc

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

# 2b) 日级熔断：Retry-After 85590s → 不睡 24h，立即放弃 + 全局暂停窗口
oc._quota_pause_until = 0.0
sleeps = []
def fake_get_daily(url, params=None, timeout=None):
    class R:
        status_code = 429
        headers = {"Retry-After": "85590"}
        def json(self): return {}
    return R()
with patch.object(oc.time, "sleep", side_effect=lambda s: sleeps.append(s)), \
     patch.object(oc.httpx, "get", fake_get_daily):
    r = oc.openalex_get("https://api.openalex.org/works")
    assert r is None, "日级熔断应立即放弃"
    assert not any(s > 600 for s in sleeps), f"不允许长睡眠: {sleeps}"
    assert oc._quota_pause_until > oc.time.monotonic(), "应设置全局熔断窗口"
    # 熔断窗口内的后续请求直接放弃，不再发 HTTP
    n_http = []
    def counting_get(url, params=None, timeout=None):
        n_http.append(1)
        class R2:
            status_code = 200
            headers = {}
            def json(self): return {}
        return R2()
    with patch.object(oc.httpx, "get", counting_get):
        assert oc.openalex_get("https://api.openalex.org/works") is None
    assert not n_http, "熔断窗口内不应发请求"
oc._quota_pause_until = 0.0
print("[2b] 日级熔断：立即放弃+全局暂停，绝不 sleep 24h ✓")

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
