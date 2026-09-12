#!/usr/bin/env python3
"""全局 LLM 频率控制：并发槽/最小间隔/1302退避重试。"""
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ai.llm as L  # noqa: E402

# 测试环境无真实 key：构造前注入假凭据（invoke 全程被 mock，不会真请求）
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.test.local/v1")

# 测试用小参数
L.LLM_MIN_INTERVAL = 0.15
L._LLM_SEM = threading.Semaphore(2)

class _Msg:
    def __init__(self, content): self.content = content

# [1] 请求起点全局最小间隔（串行 4 次调用，间隔 >= 0.15s）
stamps = []
def fake_invoke(self, inp, *a, **k):
    stamps.append(time.monotonic())
    return _Msg("ok")
with patch.object(L.ChatOpenAI, "invoke", fake_invoke):
    chat = L.build_chat("glm-5.3-flash")
    for _ in range(4):
        chat.invoke("hi")
gaps = [b - a for a, b in zip(stamps, stamps[1:])]
assert min(gaps) >= 0.14, f"违反最小间隔: {gaps}"
print(f"[1] 全局最小间隔节流 ✓（最小 {min(gaps):.3f}s >= {L.LLM_MIN_INTERVAL}s）")

# [2] 并发槽上限：4 线程并发，峰值 ≤ 2
L._llm_last = 0.0
cur = [0]; peak = [0]; lock = threading.Lock()
def slow_invoke(self, inp, *a, **k):
    with lock:
        cur[0] += 1; peak[0] = max(peak[0], cur[0])
    time.sleep(0.3)
    with lock:
        cur[0] -= 1
    return _Msg("ok")
with patch.object(L.ChatOpenAI, "invoke", slow_invoke):
    chat2 = L.build_chat("glm-5.3-flash")
    ts = [threading.Thread(target=lambda: chat2.invoke("x")) for _ in range(4)]
    for t in ts: t.start()
    for t in ts: t.join()
assert peak[0] <= 2, f"并发超限: peak={peak[0]}"
print(f"[2] 并发槽上限 ✓（4线程峰值 {peak[0]} <= 2）")

# [3] 1302 限流 → 指数退避重试成功（3/6/9s 被 mock 掉不真睡）
L._llm_last = 0.0
attempts = []
def flaky_invoke(self, inp, *a, **k):
    attempts.append(1)
    if len(attempts) <= 2:
        raise RuntimeError("Error code: 429 - {'error': {'code': '1302', 'message': '您的账户已达到速率限制'}}")
    return _Msg("recovered")
sleeps = []
with patch.object(L.ChatOpenAI, "invoke", flaky_invoke), \
     patch.object(L.time, "sleep", side_effect=lambda s: sleeps.append(s)):
    chat3 = L.build_chat("glm-5.3-flash")
    out = chat3.invoke("hi")
assert out.content == "recovered" and len(attempts) == 3
backoffs = [s for s in sleeps if s >= 3]  # 过滤掉节流的小间隔 sleep
assert backoffs == [3, 6], f"退避应为3/6s: {sleeps}"
# 非限流错误不重试
calls = []
def hard_error(self, inp, *a, **k):
    calls.append(1)
    raise RuntimeError("balance insufficient 1113")
with patch.object(L.ChatOpenAI, "invoke", hard_error):
    try:
        chat3.invoke("hi")
        raise AssertionError("应抛出")
    except RuntimeError as e:
        assert "1113" in str(e)
assert len(calls) == 1, "非限流错误不应重试"
print("[3] 1302/429 指数退避(3/6/9s)重试；非限流错误立即抛出 ✓")

print("\nLLM 频率控制测试通过 ✅")
