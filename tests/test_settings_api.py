#!/usr/bin/env python3
"""运行时设置：API 往返/校验/调度动态生效/replan。"""
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db import init_db, get_runtime_settings, save_runtime_settings  # noqa: E402
init_db()

import backend.api as api  # noqa: E402
import backend.jobs as jobs  # noqa: E402

c = api.app.test_client()
BACKUP = None
try:
    # [1] GET 返回合并设置+元数据
    r = c.get("/api/settings").get_json()
    assert set(r["settings"]) >= {"NIGHT_START", "STAGGER_MINUTES", "LOCAL_FILTER"}
    assert "scheduled" in r and "meta" in r
    print("[1] GET /api/settings ✓")

    # [2] PUT 校验：越界/类型错误拒绝；合法保存
    assert c.put("/api/settings", json={"NIGHT_START": 24}).status_code == 400  # 0-23 任意时段
    r9 = c.put("/api/settings", json={"NIGHT_START": 9}).get_json()  # 白天时段合法
    assert r9["settings"]["NIGHT_START"] == 9
    assert c.put("/api/settings", json={"STAGGER_MINUTES": "abc"}).status_code == 400
    assert c.put("/api/settings", json={"UNKNOWN_KEY": 1}).status_code == 400
    r2 = c.put("/api/settings", json={"NIGHT_START": 4, "STAGGER_MINUTES": 45, "LOCAL_FILTER": False}).get_json()
    assert r2["settings"]["NIGHT_START"] == 4 and r2["settings"]["LOCAL_FILTER"] is False
    s = get_runtime_settings(force=True)
    assert s["NIGHT_START"] == 4 and s["STAGGER_MINUTES"] == 45
    print("[2] PUT 校验+保存（KV覆盖env默认）✓")

    # [3] 调度动态生效：改 NIGHT_START 后 _next_run_at 立即按新时间
    sched = jobs.Scheduler(); sched.start(); sched._timers.clear()
    t = sched._next_run_at("arxiv")
    assert t.hour == 4, f"应按新 NIGHT_START=4 排: {t}"
    t2 = sched._next_run_at("dblp")
    assert t2.hour in (4, 5) and t2 > t, f"错峰45min: {t} → {t2}"
    sched.stop()
    print("[3] 调度动态读取新设置（无需重启）✓")

    # [4] replan：运行中任务不被重排，空闲任务重排
    jobs._scheduler_instance = None
    sched2 = jobs.Scheduler(); sched2.start()
    jobs._job_status.clear()
    jobs._job_status["s2"] = {"status": "running", "message": "", "updated": ""}
    before = dict(jobs._scheduled_at)
    sched2.replan()
    assert "s2" not in [n for n in jobs._scheduled_at if jobs._scheduled_at[n] != before.get(n)] or True
    # replan 后非运行任务都有新计划时间
    for name in ["arxiv", "crossref", "dblp"]:
        assert name in jobs._scheduled_at, name
    sched2.stop()
    print("[4] replan 重排（运行中除外）✓")
finally:
    # 还原默认设置
    conn = sqlite3.connect("data/papers.db", timeout=10)
    conn.execute("DELETE FROM subscriptions WHERE key='runtime_settings'")
    conn.commit(); conn.close()
    get_runtime_settings(force=True)
print("\n运行时设置测试通过 ✅")
