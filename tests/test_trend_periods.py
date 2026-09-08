#!/usr/bin/env python3
"""周/月双周期趋势：窗口/键名/period_type、API scope、自动沉淀调度。"""
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api  # noqa: E402
from ai import trend_analyzer  # noqa: E402

# ── [1] 月度生成：本月入库论文入选、键为 YYYY-MM、period_type=monthly ──
mem = sqlite3.connect(":memory:")
mem.row_factory = sqlite3.Row
mem.execute("CREATE TABLE papers (id TEXT, title TEXT, published_date TEXT, created_at TEXT)")
mem.execute("CREATE TABLE ai_results (paper_id TEXT, tldr TEXT, method TEXT, result TEXT, recommendation TEXT, relevance_score INT)")
mem.execute("""CREATE TABLE trend_reports (week_start TEXT PRIMARY KEY, new_methods TEXT,
    solved_problems TEXT, controversies TEXT, opportunities TEXT, paper_count INT,
    period_type TEXT, generated_at TEXT)""")
this_month = datetime.now().strftime("%Y-%m")
mem.execute("INSERT INTO papers VALUES ('m1','月内新发现','2024-01-01',?)", (f"{this_month}-03 00:00:00",))
mem.execute("INSERT INTO ai_results VALUES ('m1','t','m','r','recommended',9)")
mem.execute("INSERT INTO papers VALUES ('m0','上月旧文','2024-01-01','2026-07-15 00:00:00')")
mem.execute("INSERT INTO ai_results VALUES ('m0','t','m','r','recommended',8)")

class _R:
    content = '{"new_methods": ["x"], "solved_problems": ["y"], "controversies": ["z"], "opportunities": ["w"]}'
class _Chain:
    def invoke(self, inputs):
        captured.update(inputs)
        return _R()
captured = {}
class _Prompt:
    def __or__(self, other): return _Chain()

with patch.object(trend_analyzer, "get_conn", return_value=mem), \
     patch("ai.llm.build_chat", return_value=object()), \
     patch.object(trend_analyzer.ChatPromptTemplate, "from_template", return_value=_Prompt()):
    r = trend_analyzer.generate_trend_report_period("monthly")
assert r["week_start"] == this_month and r["period_type"] == "monthly", r
assert r["paper_count"] == 1, "上月入库的论文不应入选"
assert "month-scale" in captured.get("scale_hint", ""), "月度 prompt 应带月尺度提示"
row = mem.execute("SELECT period_type FROM trend_reports WHERE week_start=?", (this_month,)).fetchone()
assert row["period_type"] == "monthly"
print("[1] 月度生成：本月窗口/YYYY-MM键/period_type ✓")

# ── [2] API scope：latest 按类型过滤，列表分 weeks/months ──
mem2 = sqlite3.connect(":memory:")
mem2.row_factory = sqlite3.Row
mem2.execute("""CREATE TABLE trend_reports (week_start TEXT PRIMARY KEY, new_methods TEXT,
    solved_problems TEXT, controversies TEXT, opportunities TEXT, paper_count INT,
    period_type TEXT, generated_at TEXT)""")
mem2.execute("INSERT INTO trend_reports VALUES ('2026-09', 'mo', '', '', '', 30, 'monthly', NULL)")
mem2.execute("INSERT INTO trend_reports VALUES ('2026-08-31', 'wk', '', '', '', 50, 'weekly', NULL)")
c = api.app.test_client()
with patch.object(api, "get_conn", lambda: mem2):
    assert c.get("/api/trend-radar?scope=monthly").get_json()["report"]["week_start"] == "2026-09"
    assert c.get("/api/trend-radar?scope=weekly").get_json()["report"]["week_start"] == "2026-08-31"
    listed = c.get("/api/trend-radars").get_json()
    assert listed["months"] == ["2026-09"] and listed["weeks"] == ["2026-08-31"], listed
print("[2] API scope 过滤 + 周月列表分离 ✓")

# ── [3] trigger 带 scope=monthly 调用月度生成 ──
import time  # noqa: E402
with patch("ai.trend_analyzer.generate_trend_report_period",
           return_value={"week_start": "2026-09", "paper_count": 9, "period_type": "monthly"}) as gen:
    r = c.post("/api/trigger/trend", json={"scope": "monthly"})
    assert r.status_code == 200 and r.get_json()["scope"] == "monthly"
    for _ in range(50):
        time.sleep(0.1)
        if gen.called:
            break
    assert gen.called and gen.call_args[0][0] == "monthly"
print("[3] trigger scope=monthly ✓")

# ── [4] 滚动刷新：每晚刷当期周/月报；1日额外归档上月（带上界防跨期污染）──
from jobs import run_trend_auto, get_job_status  # noqa: E402
calls = []
def _rec(pt, key=None, window_end=None):
    calls.append((pt, key, window_end))
    return {"week_start": key or "x", "paper_count": 1}
with patch("ai.trend_analyzer.generate_trend_report_period", side_effect=_rec):
    run_trend_auto(today=date(2026, 9, 5))    # 周六：滚动刷当期
    assert calls == [("weekly", None, None), ("monthly", None, None)], calls
    calls.clear()
    run_trend_auto(today=date(2026, 9, 1))    # 1日：滚动 + 归档上月带上界
    assert calls[:2] == [("weekly", None, None), ("monthly", None, None)]
    assert calls[2] == ("monthly", "2026-08", "2026-09-01"), calls[2]
print("[4] trend_auto 滚动刷新 + 月初归档窗口上界 ✓")

print("\n周月双周期趋势测试通过 ✅")
