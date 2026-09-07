#!/usr/bin/env python3
"""Test nightly scheduler: no immediate runs, 30-min stagger, chain intact."""
import sys
from pathlib import Path
import time
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import jobs

ran = []
chain = []

jobs.JOB_FUNCS = {name: (lambda n=name: ran.append(n)) for name in
                  ["arxiv", "crossref", "dblp", "s2", "author", "citations", "trend_auto"]}
jobs.run_retro_enhance = lambda: chain.append("enhance")
jobs.run_digest_job = lambda: chain.append("digest")

import api
api._retro_knowledge_extract = lambda: chain.append("knowledge")
api._retro_fulltext_analyze = lambda: chain.append("fulltext")

ORDER = ["arxiv", "crossref", "dblp", "s2", "author", "citations", "trend_auto"]
EXPECTED_MINUTES = [0, 30, 60, 90, 120, 150, 180]  # index × 30min

# 1) 默认模式：start() 不执行任何任务，定时器排在凌晨、间隔 30 分钟
import os
os.environ.pop("RUN_ON_START", None)
os.environ.pop("STAGGER_MINUTES", None)
os.environ.pop("NIGHT_START", None)
s = jobs.Scheduler()
s.start()
time.sleep(0.2)
assert ran == [], f"start() 不应立即执行任务, got {ran}"
assert len(s._timers) == 7
now = datetime.now()
for name, exp_min in zip(ORDER, EXPECTED_MINUTES):
    t = s._next_run_at(name)
    assert t > now and (t - now) < timedelta(days=1.1)
    base = now.replace(hour=2, minute=0, second=0, microsecond=0)
    expected = base + timedelta(minutes=exp_min)
    if expected <= now:
        expected += timedelta(days=1)
    assert (t.year, t.month, t.day, t.hour, t.minute) == (expected.year, expected.month, expected.day, expected.hour, expected.minute), (name, t, expected)
s.stop()
print("[1] 默认启动不跑任务；02:00-05:00 七任务错峰 ✓")

# 2) STAGGER_MINUTES 可调
with patch.dict("os.environ", {"STAGGER_MINUTES": "60"}):
    s4 = jobs.Scheduler()
    t = s4._next_run_at("author")
    assert t.minute == 0 and t.hour == 6, f"02:00 + 4×60min 应为 06:00, got {t}"
    t5 = s4._next_run_at("citations")
    assert t5.hour == 7 and t5.minute == 0, f"02:00 + 5×60min 应为 07:00, got {t5}"
    s4.stop()
print("[2] STAGGER_MINUTES 可配置 ✓")

# 3) 任务执行 + arxiv 链 + 重排
s2 = jobs.Scheduler()
s2.start()
s2._timers.clear()
s2._run_and_schedule_next("arxiv")
assert "arxiv" in ran
assert chain == ["enhance", "knowledge", "fulltext", "digest"], f"arxiv 链条必须完整, got {chain}"
assert len(s2._timers) == 1
s2._timers.clear()
s2._run_and_schedule_next("crossref")
assert chain == ["enhance", "knowledge", "fulltext", "digest"], "非 arxiv 不触发链"
s2.stop()
print("[3] 任务执行 + arxiv 串联分析链 + 自动重排 ✓")

# 4) RUN_ON_START=1 立即执行
with patch.dict("os.environ", {"RUN_ON_START": "1"}):
    s3 = jobs.Scheduler()
    n_before = len(ran)
    s3.start()
    time.sleep(0.2)
    assert sorted(ran[n_before:]) == ["arxiv", "author", "citations", "crossref", "dblp", "s2", "trend_auto"]
    s3.stop()
print("[4] RUN_ON_START=1 启动即全量执行 ✓")

# 5) 手动触发路径独立于调度器
import inspect
src = inspect.getsource(api.trigger_job)
assert "threading.Thread" in src and "Scheduler" not in src
print("[5] /api/trigger/* 手动触发随时可用 ✓")

# 6) 夜间互斥：上一任务 running 时，本任务推迟而不执行
s5 = jobs.Scheduler()
s5.start()
s5._timers.clear()
jobs._job_status.clear()
jobs._job_status["dblp"] = {"status": "running", "message": "", "updated": ""}
n_before6 = len(ran)
s5._run_and_schedule_next("s2")
time.sleep(0.3)
assert "s2" not in ran[n_before6:], "dblp 运行中时 s2 不应执行"
assert len(s5._timers) == 1, "应安排推迟重试定时器"
s5.stop()
# running 清除后可正常执行
jobs._job_status.clear()
s6 = jobs.Scheduler(); s6.start(); s6._timers.clear()
n6 = len(ran)
s6._run_and_schedule_next("s2")
assert "s2" in ran[n6:]
s6.stop()
print("[6] 夜间互斥：任务运行中推迟 15 分钟，完成后正常执行 ✓")

print("\n调度器测试全部通过 ✅")
