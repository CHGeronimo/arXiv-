#!/usr/bin/env python3
"""LLM 动态双闸：bulk 占满时 priority 不排队；限值随时段/设置动态变化。"""
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import backend.ai.llm as llm  # noqa: E402

llm._LIMITS_OVERRIDE = (6, 0.0)  # 固定限值：总 6 / bulk 5

# [1] 夜窗判定（含跨午夜与不启用）
f = llm._is_night_hour
assert f(2, 0, 8) and f(7, 0, 8) and not f(8, 0, 8) and not f(12, 0, 8)
assert f(23, 22, 6) and f(3, 22, 6) and not f(8, 22, 6)   # 跨午夜
assert not f(5, 5, 5)                                       # start==end 不启用
print("[1] 夜窗窗口判定（含跨午夜）✓")

# [2] bulk 闸 = 总闸-1；bulk 占满时 priority 立刻获槽；bulk 超限阻塞
held_bulk = []
try:
    for _ in range(5):
        held_bulk.append(llm._acquire_llm_slot(priority=False))
    assert llm._BULK_GATE._active == 5 and llm._TOTAL_GATE._active == 5
    t0 = time.monotonic()
    held_pri = llm._acquire_llm_slot(priority=True)
    dt = time.monotonic() - t0
    assert dt < 1.5, f"priority 应立即获槽，等了 {dt:.2f}s"
    assert llm._TOTAL_GATE._active == 6
    print(f"[2] bulk 占满时 priority {dt*1000:.0f}ms 获槽（保留槽生效）✓")
    got = []
    def _try_bulk():
        llm._BULK_GATE.acquire()
        got.append(True)
    th = threading.Thread(target=_try_bulk, daemon=True)
    th.start(); th.join(0.5)
    assert not got, "bulk 超限不应立刻获槽"
    print("[3] bulk 超出容量正确阻塞 ✓")
finally:
    for held in held_bulk:
        for g in reversed(held):
            g.release()
    try:
        for g in reversed(held_pri):
            g.release()
    except NameError:
        pass

# [4] 限值动态上调：bulk 5 满载时把限值提到 9，第 6/7/8 个 bulk 应被放行
llm._LIMITS_OVERRIDE = (9, 0.0)
extra = []
try:
    for _ in range(5):
        extra.append(llm._acquire_llm_slot(priority=False))
    # 此时 bulk active=5 限制=8 → 还能拿 3 个
    more = []
    for _ in range(3):
        more.append(llm._acquire_llm_slot(priority=False))
    assert llm._BULK_GATE._active == 8
    print("[4] 限值动态上调后放行（凌晨放宽即此机制）✓")
finally:
    for held in extra + more:
        for g in reversed(held):
            g.release()

# [5] 释放无泄漏：全部归还后 active=0
assert llm._TOTAL_GATE._active == 0 and llm._BULK_GATE._active == 0
llm._LIMITS_OVERRIDE = None
print("[5] 闸归零无泄漏 ✓")

print("\nLLM 动态限流测试通过 ✅")
