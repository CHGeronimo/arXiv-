#!/usr/bin/env python3
"""恶魔审查修复回归：feedback UPSERT / AI链缓存刷新 / 本地预筛豁免。"""
import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db import init_db, stop_writer  # noqa: E402
init_db()

import backend.api as api  # noqa: E402
import backend.paper_store as paper_store  # noqa: E402
from backend.crawler.models import Paper  # noqa: E402

c = api.app.test_client()
DB = "data/papers.db"
TESTPID = "devil-test-paper"

conn = sqlite3.connect(DB, timeout=10)
conn.execute("INSERT OR REPLACE INTO papers (id, source, title) VALUES (?,?,?)", (TESTPID, "arxiv", "Devil Test"))
conn.execute("INSERT OR REPLACE INTO ai_results (paper_id, method, motivation, recommendation) VALUES (?,?,?,?)",
             (TESTPID, "multi-agent credit assignment method", "coordination motivation", "recommended"))
conn.commit()

try:
    # [1] 收藏/已读在多次 feedback POST 后存活（INSERT OR REPLACE 曾抹掉它们）
    #     patch 掉画像后台线程保持封闭；rating:'' 在字段级语义下=不修改（设计变更）
    with patch.object(api, "_update_profile_from_feedback", lambda *a: None), \
         patch.object(api, "_remove_paper_note", lambda *a: None):
        c.post("/api/bookmark", json={"paper_id": TESTPID, "on": True})
        c.post("/api/read", json={"paper_id": TESTPID})
        c.post("/api/feedback", json={"paper_id": TESTPID, "rating": "like"})
        c.post("/api/feedback", json={"paper_id": TESTPID, "rating": "", "relevance": 4})
        row = conn.execute("SELECT bookmarked, is_read, rating, relevance FROM feedback WHERE paper_id=?", (TESTPID,)).fetchone()
        assert row == (1, 1, "like", 4), f"收藏/已读被抹 或 rating 被误清: {row}"
    print("[1] feedback UPSERT 不抹收藏/已读；rating:'' 不误清投票 ✓")

    # [2] feedback 更新 profile 后必须刷新 AI 链缓存（闭环曾需重启才生效）
    class FakeResp:
        content = '["devil topic A", "devil topic B"]'
    class FakeLLM:
        def __init__(self, *a, **k): pass
        def invoke(self, prompt): return FakeResp()

    resets = []
    with patch("backend.ai.llm.build_chat", return_value=FakeLLM()), \
         patch.object(api, "reset_ai_chain", side_effect=lambda: resets.append(1)):
        api._update_profile_from_feedback(TESTPID, "like")
    assert resets, "必须调用 reset_ai_chain"
    print("[2] feedback 更新 profile 后触发 AI 链缓存刷新 ✓")

    # [3] 本地预筛豁免：作者订阅、无摘要论文放行；有摘要零命中仍拒
    def run_append(source, title, summary):
        p = Paper(id=f"lf-{source}-{abs(hash(title)) % 99999}", source=source, title=title, summary=summary)
        calls = []
        with patch.object(paper_store, "_paper_exists", return_value=False), \
             patch.object(paper_store, "is_ignored", return_value=False), \
             patch.object(paper_store, "_ai_exists", return_value=False), \
             patch.object(paper_store, "ignore_paper", side_effect=lambda pid, r="": calls.append(r)), \
             patch.object(paper_store, "get_local_terms",
                          return_value={"reinforcement", "multi", "agent", "mechanism"}), \
             patch.object(paper_store, "quick_filter_paper", return_value=(True, "")), \
             patch.object(paper_store, "get_quick_chain", return_value=None), \
             patch.object(paper_store, "get_ai_chain", return_value=(None, {})), \
             patch.object(paper_store, "enhance_single",
                          return_value={"AI": {"recommendation": "ignore", "skip_reason": "low_relevance"}}), \
             patch.object(paper_store, "_insert_paper_row"):
            r = paper_store.append_paper(p, enhance=True)
        return r, calls

    r, _ = run_append("author_s2", "Pure decision theory proof", "no overlap words at all")
    assert r == "ai_reject", f"作者订阅不应被本地预筛拦截, got {r}"
    r, _ = run_append("arxiv", "Pure decision theory proof", "")  # 无摘要
    assert r == "ai_reject", f"无摘要论文应放行给 LLM, got {r}"
    r, calls = run_append("arxiv", "Pure decision theory proof", "no overlap words at all")
    assert r == "filter_reject" and calls == ["local_filter_reject"], (r, calls)
    print("[3] 本地预筛豁免（作者订阅/无摘要）+ 零命中拦截 ✓")
finally:
    # 还原 profile（去掉测试注入主题）与临时论文（CASCADE 清理 feedback/ai_results）
    prof_path = Path("research_profile.json")
    prof = json.loads(prof_path.read_text(encoding="utf-8"))
    prof["liked_topics"] = [t for t in prof.get("liked_topics", []) if not t.startswith("devil topic")]
    prof_path.write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
    conn.execute("DELETE FROM papers WHERE id = ?", (TESTPID,))
    conn.commit()
    conn.close()
    stop_writer()

print("\n恶魔修复回归全部通过 ✅")
