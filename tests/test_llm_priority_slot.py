#!/usr/bin/env python3
"""LLM 双闸优先槽：bulk 占满时交互式单发（简报/趋势/想法）不被排队。"""
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import backend.ai.llm as llm  # noqa: E402

# [1] bulk 闸容量 = 总闸 - 1（留 1 个优先槽）
assert llm._BULK_SEM._value == llm.LLM_MAX_CONCURRENT - 1
print(f"[1] 双闸容量: 总 {llm.LLM_MAX_CONCURRENT} / bulk {llm.LLM_MAX_CONCURRENT - 1} ✓")

# [2] bulk 全占时，priority 仍能立刻拿槽；bulk 再来则阻塞
held_bulk = []
try:
    for _ in range(llm.LLM_MAX_CONCURRENT - 1):
        held_bulk.append(llm._acquire_llm_slot(priority=False))
    t0 = time.monotonic()
    held_pri = llm._acquire_llm_slot(priority=True)
    dt = time.monotonic() - t0
    # 优先槽只等最小间隔（≤1.5s 宽容），不排队
    assert dt < 1.5, f"priority 应立即获槽，实际等了 {dt:.2f}s"
    print(f"[2] bulk 占满时 priority {dt*1000:.0f}ms 获槽 ✓")

    # bulk 第 6 个应阻塞（无槽可拿）——起线程验证
    got = []
    def _try_bulk():
        try:
            llm._acquire_llm_slot(priority=False)
            got.append(True)
        except Exception:
            got.append(False)
    th = threading.Thread(target=_try_bulk, daemon=True)
    th.start()
    th.join(0.6)
    assert not got, "bulk 超限不应立刻获槽"
    print("[3] bulk 超出容量正确阻塞 ✓")
finally:
    for held in held_bulk:
        for sem in reversed(held):
            sem.release()
    try:
        for sem in reversed(held_pri):
            sem.release()
    except NameError:
        pass

# [4] build_chat(priority=True) 注入：不透传给 ChatOpenAI（pydantic 不炸）
chat = llm.build_chat("glm-5.3-flash", thinking=False, priority=True)
assert chat._priority is True and not getattr(chat, "priority", None)
chat2 = llm.build_chat("glm-5.3-flash", thinking=False)
assert chat2._priority is False
print("[4] priority 参数注入/隔离 ✓")

print("\nLLM 优先槽测试通过 ✅")
