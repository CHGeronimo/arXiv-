#!/usr/bin/env python3
"""运行时改进回归：crossref known_ids 去重 / stats 版本字段。"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backend.api as api  # noqa: E402

# ── [1] Crossref 爬取层跳过已知论文（不为它下载后处理/回填摘要）──
from backend.crawler.crossref_crawler import CrossrefCrawler  # noqa: E402
from backend.crawler.subs_store import Journal  # noqa: E402

items = [{"DOI": "10.1/known", "title": ["已知论文"], "type": "journal-article", "abstract": "<p>abs</p>"},
         {"DOI": "10.1/new", "title": ["新论文"], "type": "journal-article", "abstract": "<p>abs</p>"}]
c = CrossrefCrawler(journals=[Journal(issn="0001", name="J")], known_ids={"10.1/known"})
with patch.object(c, "_fetch_recent", return_value=items), \
     patch.object(c, "_needs_update", return_value=True), \
     patch.object(c, "_fill_abstracts_openalex") as bf:
    papers = list(c.crawl_iter())
assert [p.id for p in papers] == ["10.1/new"], [p.id for p in papers]
batch_arg = bf.call_args[0][0]
assert [p.id for p in batch_arg] == ["10.1/new"], "回填只应处理新论文"
print("[1] crossref known_ids：已知论文跳过（含摘要回填）✓")

# ── [2] /api/stats 携带版本与 stale 标记 ──
c2 = api.app.test_client()
data = c2.get("/api/stats").get_json()
assert "daemon_version" in data and "disk_version" in data and "code_stale" in data
assert isinstance(data["must_read"], int)
with patch.object(api, "_git_hash", return_value="bbb222"):
    api._disk_version_cache["checked"] = 0.0  # 强制刷新磁盘缓存
    api._DAEMON_VERSION = "aaa111"
    d2 = c2.get("/api/stats").get_json()
    assert d2["code_stale"] is True and d2["disk_version"] == "bbb222"
with patch.object(api, "_git_hash", return_value="same9"):
    api._disk_version_cache["checked"] = 0.0
    api._DAEMON_VERSION = "same9"
    d3 = c2.get("/api/stats").get_json()
    assert d3["code_stale"] is False
print("[2] /api/stats 版本字段 + stale 判定 ✓")

print("\n运行时改进测试通过 ✅")
