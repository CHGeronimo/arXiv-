#!/usr/bin/env python3
"""设计vs实现差距修复回归（A/B 类）。"""
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import init_db, stop_writer  # noqa: E402
init_db()

import api  # noqa: E402
import paper_store  # noqa: E402
from crawler.models import Paper  # noqa: E402

# ── B④ quick_filter 元组 + relevance_reason 入 ignored_papers ──
ignored_calls = []
p = Paper(id="ab-qf-1", source="arxiv", title="Wireless protocol optimization", summary="network protocols")
with patch.object(paper_store, "_paper_exists", return_value=False), \
     patch.object(paper_store, "is_ignored", return_value=False), \
     patch.object(paper_store, "_ai_exists", return_value=False), \
     patch.object(paper_store, "ignore_paper",
                  side_effect=lambda pid, reason="", detail="": ignored_calls.append((pid, reason, detail))), \
     patch.object(paper_store, "_local_filter_enabled", return_value=False), \
     patch.object(paper_store, "get_quick_chain", return_value=None), \
     patch.object(paper_store, "get_ai_chain", return_value=(None, {})), \
     patch.object(paper_store, "quick_filter_paper",
                  return_value=(False, "Paper is about wireless protocols, outside the MARL research direction")):
    r = paper_store.append_paper(p, enhance=True)
assert r == "filter_reject"
assert ignored_calls == [("ab-qf-1", "quick_filter_reject", "Paper is about wireless protocols, outside the MARL research direction")], ignored_calls
print("[1] quick_filter 拒绝理由入库 ignored_papers.reason_detail ✓")

# ── B④ /api/ignored 返回 reason_detail ──
conn = sqlite3.connect("data/papers.db", timeout=10)
try:
    conn.execute("INSERT OR REPLACE INTO ignored_papers (paper_id, reason, reason_detail, ignored_at) VALUES (?,?,?,datetime('now'))",
                 ("ab-test-ignored", "quick_filter_reject", "test reason detail"))
    conn.commit()
    c = api.app.test_client()
    data = c.get("/api/ignored?reason=quick_filter_reject&per_page=1").get_json()
    entry = next(i for i in data["ignored"] if i["paper_id"] == "ab-test-ignored")
    assert entry["reason_detail"] == "test reason detail", entry
finally:
    conn.execute("DELETE FROM ignored_papers WHERE paper_id='ab-test-ignored'")
    conn.commit()
    conn.close()
print("[2] /api/ignored 透传 reason_detail ✓")

# ── B⑥ digest 文件缺失时从表回退 + 日期列表合并 ──
mem = sqlite3.connect(":memory:")
mem.execute("CREATE TABLE digests (date TEXT PRIMARY KEY, content TEXT, created_at TEXT)")
mem.execute("INSERT INTO digests VALUES ('2000-01-01', '# Rescue Digest', 'x')")
c = api.app.test_client()
with patch.object(api, "get_conn", lambda: mem):
    r = c.get("/api/digest/2000-01-01")  # 无此文件 → 表回退
    assert r.status_code == 200 and "Rescue Digest" in r.get_data(as_text=True)
    listed = c.get("/api/digests").get_json()["digests"]
    assert "2000-01-01" in listed and "2026-08-22" in listed, listed  # 表+文件合并
assert c.get("/api/digest/1999-01-01").status_code == 404
print("[3] digest 表回退 + 日期列表合并 ✓")

# ── B⑧ 趋势周列表端点 ──
weeks = c.get("/api/trend-radars").get_json()["weeks"]
assert isinstance(weeks, list) and weeks, weeks
print(f"[4] /api/trend-radars 历史{len(weeks)}周 ✓")

# ── B⑦ 问题域标注器（LLM 挂掉时返回空，不炸聚类）──
from ai.knowledge_clustering import _label_problem_domains  # noqa: E402

class _Resp:
    content = '{"多智能体强化学习": "序贯决策与控制", "机制设计": "机制设计与激励"}'
class _FakeLLM:
    def invoke(self, prompt):
        assert "多智能体强化学习" in prompt
        return _Resp()
with patch("ai.llm.build_chat", return_value=_FakeLLM()):
    domains = _label_problem_domains(["多智能体强化学习", "机制设计"])
assert domains["机制设计"] == "机制设计与激励", domains
with patch("ai.llm.build_chat", side_effect=RuntimeError("LLM down")):
    assert _label_problem_domains(["x"]) == {}
print("[5] 聚类问题域标注（LLM失败降级空）✓")

stop_writer()
print("\nA/B 修复回归通过 ✅")
