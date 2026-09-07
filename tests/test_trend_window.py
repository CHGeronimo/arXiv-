#!/usr/bin/env python3
"""趋势雷达：入库时间窗口 + 任务状态跟踪 + 入口/结果日志。"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api  # noqa: E402
from ai import trend_analyzer  # noqa: E402

# [1] 窗口按 created_at：本周入库但 published_date 是老日期的论文必须入选
mem = sqlite3.connect(":memory:")
mem.row_factory = sqlite3.Row
mem.execute("CREATE TABLE papers (id TEXT, title TEXT, published_date TEXT, created_at TEXT)")
mem.execute("CREATE TABLE ai_results (paper_id TEXT, tldr TEXT, method TEXT, result TEXT, recommendation TEXT, relevance_score INT)")
mem.execute("""CREATE TABLE trend_reports (week_start TEXT PRIMARY KEY, new_methods TEXT,
    solved_problems TEXT, controversies TEXT, opportunities TEXT, paper_count INT,
    period_type TEXT, generated_at TEXT)""")
this_week = datetime.now().strftime("%Y-%m-%d")
mem.execute("INSERT INTO papers VALUES ('new-cite','Citation Paper','2024-01-01',?)", (f"{this_week} 03:00:00",))  # 引文/会议论文典型：老投稿日+本周入库
mem.execute("INSERT INTO ai_results VALUES ('new-cite','t','m','r','recommended',9)")
mem.execute("INSERT INTO papers VALUES ('old-intake','Old Intake','2026-09-01','2026-06-01 00:00:00')")  # published 本周但上月入库
mem.execute("INSERT INTO ai_results VALUES ('old-intake','t','m','r','recommended',8)")

class _R:
    content = '{"new_methods": "m", "solved_problems": "p", "controversies": "c", "opportunities": "o"}'
class _Chain:
    def invoke(self, inputs):
        captured.append(inputs)
        return _R()

captured = []
class _Prompt:
    def __or__(self, other): return _Chain()

with patch.object(trend_analyzer, "get_conn", return_value=mem), \
     patch("ai.llm.build_chat", return_value=object()), \
     patch.object(trend_analyzer.ChatPromptTemplate, "from_template", return_value=_Prompt()):
    result = trend_analyzer.generate_trend_report()

assert result is not None, "本周入库论文必须生成报告"
assert result["paper_count"] == 1
assert any("Citation Paper" in str(v) for v in captured[0].values()), "入库论文必须进入分析 prompt"
print("[1] 窗口按 created_at（老投稿日的本周新论文入选）✓")

# [2] 无论文时返回 None（状态由 api 层记录为"本周无论文入库"）
mem2 = sqlite3.connect(":memory:")
mem2.row_factory = sqlite3.Row
mem2.execute("CREATE TABLE papers (id TEXT, title TEXT, published_date TEXT, created_at TEXT)")
mem2.execute("CREATE TABLE ai_results (paper_id TEXT, tldr TEXT, method TEXT, result TEXT, recommendation TEXT, relevance_score INT)")
with patch.object(trend_analyzer, "get_conn", return_value=mem2):
    assert trend_analyzer.generate_trend_report() is None
print("[2] 无论文入库时返回 None ✓")

# [3] trigger 端点写入 job 状态（前端轮询 /api/jobs 判断完成）
from jobs import get_job_status  # noqa: E402
with patch("ai.trend_analyzer.generate_trend_report_period",
           return_value={"paper_count": 5, "week_start": "x", "period_type": "weekly"}) as gen:
    import threading, time
    c = api.app.test_client()
    r = c.post("/api/trigger/trend")
    assert r.status_code == 200
    for _ in range(50):
        time.sleep(0.1)
        st = get_job_status().get("trend", {})
        if st.get("status") == "done":
            break
    assert get_job_status()["trend"]["status"] == "done"
    assert "5 篇" in get_job_status()["trend"]["message"]
    assert gen.called
print("[3] trigger → job 状态 done + 消息（前端可轮询）✓")

print("\n趋势雷达修复测试通过 ✅")
