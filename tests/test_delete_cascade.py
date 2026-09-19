#!/usr/bin/env python3
"""删除端点级联清理：论文删除必须连带 ai_results/feedback/cards/fulltext，不留孤儿。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from backend.db import init_db, get_conn  # noqa: E402
init_db()

import backend.api as api  # noqa: E402

PID = "del-cascade-test-2609"
c = api.app.test_client()
conn = get_conn()

# 造一篇带全类子行的论文
conn.execute("INSERT OR REPLACE INTO papers (id, source, title) VALUES (?,?,?)", (PID, "test", "删除级联测试"))
conn.execute("INSERT OR REPLACE INTO ai_results (paper_id, tldr) VALUES (?,?)", (PID, "t"))
conn.execute("INSERT OR REPLACE INTO feedback (paper_id, rating) VALUES (?,?)", (PID, "like"))
conn.execute("INSERT OR REPLACE INTO knowledge_cards (paper_id, keywords) VALUES (?,?)", (PID, "[]"))
conn.commit()

# [1] DELETE 后 papers 与全部子表干净，且记入 ignored
r = c.delete(f"/api/paper/{PID}")
assert r.status_code == 200, r.status_code
n = conn.execute("SELECT COUNT(*) FROM papers WHERE id=?", (PID,)).fetchone()[0]
assert n == 0, f"papers 残留 {n} 行"
for table in ("ai_results", "feedback", "knowledge_cards", "fulltext_analysis"):
    n = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE paper_id=?", (PID,)).fetchone()[0]
    assert n == 0, f"{table} 残留 {n} 行"
ig = conn.execute("SELECT reason FROM ignored_papers WHERE paper_id=?", (PID,)).fetchone()
assert ig and ig[0] == "user_deleted"
print("[1] 单篇删除级联 + ignored 记录 ✓")

# [2] 不存在的论文 → 404，且 ignored 不被污染
assert c.delete("/api/paper/ghost-id-xyz").status_code == 404
assert conn.execute("SELECT COUNT(*) FROM ignored_papers WHERE paper_id='ghost-id-xyz'").fetchone()[0] == 0
print("[2] 404 不污染 ignored ✓")

# 清理
conn.execute("DELETE FROM ignored_papers WHERE paper_id=?", (PID,))
conn.commit()
print("\n删除级联测试通过 ✅")
