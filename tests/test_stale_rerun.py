#!/usr/bin/env python3
"""旧流程重跑：版本戳识别/重跑打新戳/幂等跳过——全程临时库，绝不触碰生产数据。"""
import os
import sqlite3
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from backend.db import init_db  # noqa: E402
init_db()

import backend.jobs as jobs  # noqa: E402
import backend.api as api  # noqa: E402
from backend.ai.enhance import PIPELINE_VERSION  # noqa: E402

# 临时库（jobs.get_conn 被替换 → 选择查询与 ignored 写入都隔离）
tmp = sqlite3.connect(":memory:", check_same_thread=False)
tmp.row_factory = sqlite3.Row
tmp.executescript("""
    CREATE TABLE papers (id TEXT PRIMARY KEY, source TEXT, title TEXT, summary TEXT,
        authors TEXT, categories TEXT, doi TEXT, published_date TEXT, url TEXT, pdf TEXT,
        venue TEXT, citation_count INTEGER, created_at TEXT);
    CREATE TABLE ai_results (paper_id TEXT PRIMARY KEY, tldr TEXT, pipeline_version TEXT,
        recommendation TEXT, relevance_score INTEGER);
    CREATE TABLE ignored_papers (paper_id TEXT PRIMARY KEY, reason TEXT);
""")
for i in range(3):
    tmp.execute("INSERT INTO papers (id, source, title, summary) VALUES (?,?,?,?)",
                (f"rerun-test-{i}", "test", f"Rerun {i}", f"abstract {i}"))
    tmp.execute("INSERT INTO ai_results VALUES (?,?,?,NULL,NULL)",
                (f"rerun-test-{i}", f"old {i}", "2026-08-01"))
tmp.execute("INSERT INTO papers (id, source, title, summary) VALUES ('rerun-fresh','test','F','s')")
tmp.execute("INSERT INTO ai_results VALUES ('rerun-fresh','new',?,'recommended',9)", (PIPELINE_VERSION,))
tmp.commit()

written = {}      # paper_id → ai dict（假写入器记录）
cards = []


def _fake_insert_ai(paper_id, ai):
    written[paper_id] = dict(ai)


c = api.app.test_client()
with patch.object(jobs, "get_conn", lambda: tmp), \
     patch.object(jobs, "get_ai_chain", return_value=(None, {"direction": "MARL"})), \
     patch.object(jobs, "enhance_single",
                  lambda p, ch, pr, lang: {"id": p["id"], "AI": {"tldr": f"重跑后 {p['id']}",
                                                                 "recommendation": "recommended",
                                                                 "relevance_score": 9}}), \
     patch.object(jobs, "_insert_ai_row", _fake_insert_ai), \
     patch.object(jobs, "_insert_knowledge_card", lambda pid, p: cards.append(pid)), \
     patch.object(jobs, "sync_write", lambda *a, **k: None), \
     patch.object(jobs, "_ai_max_workers", 3):
    # [1] 只重跑旧版本 3 篇；新版本与假写入均正确
    r = c.post("/api/trigger/enhance-rerun")
    assert r.status_code == 200
    deadline = time.time() + 20
    st = None
    while time.time() < deadline:
        st = c.get("/api/jobs").get_json().get("enhance_rerun")
        if st and st["status"] in ("done", "error"):
            break
        time.sleep(0.3)
    assert st and st["status"] == "done", st
    assert "3/3" in st["message"], st
    assert set(written) == {f"rerun-test-{i}" for i in range(3)}, written
    assert set(cards) == set(written), "知识卡片应随增强重提取"
    assert "rerun-fresh" not in written
    print("[1] 旧版本重跑+卡片随跑 / 新版本不动 ✓")

    # [2] 全部最新（把 written 结果模拟入库）→ 幂等跳过
    for pid, ai in written.items():
        tmp.execute("UPDATE ai_results SET tldr=?, pipeline_version=? WHERE paper_id=?",
                    (ai["tldr"], PIPELINE_VERSION, pid))
    tmp.commit()
    written.clear()
    c.post("/api/trigger/enhance-rerun")
    deadline = time.time() + 10
    while time.time() < deadline:
        st = c.get("/api/jobs").get_json().get("enhance_rerun")
        if st and st["status"] in ("done", "error"):
            break
        time.sleep(0.2)
    assert st["status"] == "done" and "无旧流程" in st["message"], st
    assert not written
    print("[2] 全最新时幂等跳过 ✓")

print("\n旧流程重跑测试通过（全程临时库隔离）✅")
