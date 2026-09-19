#!/usr/bin/env python3
"""跨源去重：别名/DOI/标题+日期解析、ignored 别名、回填合并、存量合并脚本。"""
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from backend.crawler.models import Paper  # noqa: E402
import backend.paper_store as ps  # noqa: E402
import merge_duplicates as md  # noqa: E402


def _tmp_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE papers (id TEXT PRIMARY KEY, source TEXT, title TEXT, summary TEXT,
            doi TEXT, pdf TEXT, url TEXT, venue TEXT, citation_count INTEGER, published_date TEXT,
            extra TEXT);
        CREATE TABLE ignored_papers (paper_id TEXT PRIMARY KEY, reason TEXT);
        CREATE TABLE ai_results (paper_id TEXT PRIMARY KEY, tldr TEXT);
        CREATE TABLE feedback (paper_id TEXT PRIMARY KEY, rating TEXT);
        CREATE TABLE knowledge_cards (paper_id TEXT PRIMARY KEY, keywords TEXT);
        CREATE TABLE fulltext_analysis (paper_id TEXT PRIMARY KEY, content TEXT);
        CREATE TABLE knowledge_clusters (cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_name TEXT, method_keywords TEXT, paper_ids TEXT, problem_domains TEXT);
    """)
    return conn


def _p(**kw):
    base = dict(id="x", source="test", title="T", summary="s", authors=[], categories=[],
                doi="", published_date="2026-01-01", url="", pdf="", venue="",
                citation_count=0)
    base.update(kw)
    return Paper(**base)


conn = _tmp_db()

# [1] 别名解析：DOI / arXiv id（pdf url 提取）/ arXiv DOI 形式
a = ps._paper_aliases(_p(id="2601.12345", pdf="https://arxiv.org/pdf/2601.12345v2"))
assert "2601.12345" in a and "https" not in "".join(a), a
b = ps._paper_aliases(_p(id="W123", doi="10.48550/arxiv.2601.99999"))
assert "10.48550/arxiv.2601.99999" in b and "2601.99999" in b, b
c = ps._paper_aliases(_p(id="10.1109/X.1", url="https://arxiv.org/abs/2506.11111"))
assert "2506.11111" in c, c
print("[1] 别名解析（id/DOI/arXiv 提取）✓")

with patch.object(ps, "get_conn", lambda: conn):
    # [2] 三种命中方式：DOI 别名 / papers.doi 字段 / 标题+日期归一
    conn.execute("INSERT INTO papers (id,source,title,summary,doi,citation_count,published_date) VALUES ('10.1109/tpami.2026.01','crossref','Deep Coordination RL','s','10.1109/TPAMI.2026.01',0,'2026-03-01')")
    r = ps._find_duplicate(_p(id="W999", doi="10.1109/tpami.2026.01"))
    assert r and r[1] == "alias", r  # 别名（DOI 小写）直命中
    r = ps._find_duplicate(_p(id="W998", title="Deep Coordination RL!", published_date="2026-03-01"))
    assert r and r[1] == "title", r  # 标点差异归一命中
    r = ps._find_duplicate(_p(id="W997", title="Totally Different Paper", published_date="2026-03-01"))
    assert r is None
    print("[2] 别名/标题+日期命中 ✓")

    # [3] ignored 别名：曾以 arXiv id 拉黑，DOI 再来直接拒
    conn.execute("INSERT INTO ignored_papers VALUES ('2601.77777','quick_filter_reject')")
    r = ps._find_duplicate(_p(id="10.48550/arxiv.2601.77777", doi="10.48550/arxiv.2601.77777",
                              title="Another Paper"))
    assert r and r[1] == "ignored", r
    print("[3] ignored 别名拦截 ✓")

    # [4] 回填：空缺字段补齐、引用数取大、已有值不覆盖
    conn.execute("UPDATE papers SET pdf='', citation_count=5 WHERE id='10.1109/tpami.2026.01'")
    ps._backfill_existing("10.1109/tpami.2026.01",
                          _p(id="W996", pdf="https://arxiv.org/pdf/2601.5", venue="TPAMI",
                             citation_count=9, doi="10.1109/TPAMI.2026.01",
                             title="Deep Coordination RL", published_date="2026-03-01"))
    row = conn.execute("SELECT pdf, venue, citation_count, title FROM papers WHERE id='10.1109/tpami.2026.01'").fetchone()
    assert row["pdf"] == "https://arxiv.org/pdf/2601.5" and row["venue"] == "TPAMI"
    assert row["citation_count"] == 9 and row["title"] == "Deep Coordination RL"
    print("[4] 回填合并（补空缺/引用取大）✓")

# [5] 存量合并脚本：构造 2 组重复（DOI 大小写 / 标题+日期），子表随迁
conn2 = _tmp_db()
conn2.executemany("INSERT INTO papers (id,source,title,summary,doi,venue,citation_count,published_date) VALUES (?,?,?,?,?,?,?,?)", [
    ("10.1609/AAAI.X1", "crossref", "Reward Shaping Study", "s", "10.1609/AAAI.X1", "AAAI", 3, "2026-02-01"),
    ("10.1609/aaai.x1", "dblp", "Reward Shaping Study", "s2", "", "", 7, "2026-02-01"),
    ("dblp-W7", "dblp", "Opponent Modeling Renewed", "s", "", "", 0, "2026-04-01"),
    ("dblp-W8", "dblp", "Opponent Modeling: Renewed", "s", "", "", 0, "2026-04-01"),
])
conn2.execute("INSERT INTO ai_results VALUES ('dblp-W7','已分析的版本')")
conn2.execute("INSERT INTO feedback VALUES ('dblp-W8','useful')")

def _groups_on(c):
    return md.find_duplicate_groups(c)

with patch.object(md, "init_db", lambda: None), patch.object(md, "sync_write", lambda *a, **k: None):
    groups = _groups_on(conn2)
    sizes = sorted(len(g) for g in groups)
    assert sizes == [2, 2], sizes
    # dry-run 不写
    with patch.object(md, "get_conn", lambda: conn2):
        r = md.merge(dry_run=True)
        assert r["merged"] == 0 and conn2.execute("SELECT COUNT(*) FROM papers").fetchone()[0] == 4
        # 执行合并：dblp-W8 并入 dblp-W7（有 AI 的为 canonical），feedback 随迁
        r2 = md.merge(dry_run=False)
        assert r2["dups"] == 2, r2
        ids = {row[0] for row in conn2.execute("SELECT id FROM papers")}
        assert ids == {"10.1609/AAAI.X1", "dblp-W7"}, ids
        assert conn2.execute("SELECT COUNT(*) FROM ai_results WHERE paper_id='dblp-W7'").fetchone()[0] == 1
        assert conn2.execute("SELECT COUNT(*) FROM feedback WHERE paper_id='dblp-W7'").fetchone()[0] == 1
print("[5] 存量合并（canonical 保 AI、子表随迁、dry-run 不写）✓")

# [6] 聚类悬空清理：被合并方的 id 从 knowledge_clusters.paper_ids 剔除
conn3 = _tmp_db()
conn3.executemany("INSERT INTO papers (id,source,title,doi) VALUES (?,?,?,?)", [
    ("keep-1", "dblp", "Paper A", "10.1/x"), ("dup-1", "dblp", "Paper A", "10.1/X")])
conn3.execute("INSERT INTO knowledge_clusters (cluster_name, method_keywords, paper_ids) VALUES (?,?,?)",
              ("聚类X", "[]", '["keep-1","dup-1","keep-2"]'))
with patch.object(md, "init_db", lambda: None), patch.object(md, "sync_write", lambda *a, **k: None), \
     patch.object(md, "get_conn", lambda: conn3):
    md.merge(dry_run=False)
pids = json.loads(conn3.execute("SELECT paper_ids FROM knowledge_clusters").fetchone()[0])
assert "dup-1" not in pids and "keep-1" in pids and "keep-2" in pids, pids
print("[6] 合并同步剔除聚类悬空 id ✓")

print("\n跨源去重测试通过 ✅")
