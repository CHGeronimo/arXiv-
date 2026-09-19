#!/usr/bin/env python3
"""引文顺藤摸瓜爬虫：锚点扩展、年份过滤、上限、去重。"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.crawler.citation_crawler import CitationCrawler  # noqa: E402

ANCHOR_WORK = {
    "id": "https://openalex.org/W111",
    "referenced_works": ["https://openalex.org/W1", "https://openalex.org/W2", "https://openalex.org/W3"],
    "cited_by_count": 10,
}

def _work(wid, title, year, cites=0, abstract="multi-agent coordination method"):
    return {"id": f"https://openalex.org/{wid}", "doi": f"https://doi.org/10.x/{wid}",
            "title": title, "publication_year": year, "cited_by_count": cites,
            "abstract_inverted_index": {w: [i] for i, w in enumerate(abstract.split())},
            "authorships": [{"author": {"display_name": "A. Researcher"}}],
            "primary_location": {"source": {"display_name": "NeurIPS"}, "pdf_url": ""}}

REFS = [_work("W1", "New MARL method", 2026, cites=5),
        _work("W2", "Old classic ignored by year filter", 2019),   # 年份过滤掉
        _work("W3", "Another recent cite", 2025)]
CITERS = [_work("W9", "Cites the anchor", 2026),
          _work("W8", "Old citer filtered", 2020)]                 # 年份过滤掉

calls = []
def fake_openalex_get(url, params=None, timeout=30):
    calls.append(url.split("?")[0].rsplit("/", 1)[-1] if "/doi:" in url else "works")
    if "/doi:" in url:
        return ANCHOR_WORK
    filt = (params or {}).get("filter", "")
    if filt.startswith("ids.openalex:"):
        by_id = {w["id"].rsplit("/", 1)[-1]: w for w in REFS}
        return {"results": [by_id[i] for i in filt.split("ids.openalex:")[1].split("|") if i in by_id]}
    if filt.startswith("cites:"):
        return {"results": CITERS}
    return {"results": []}

crawler = CitationCrawler(anchors=[{"id": "x", "doi": "10.x/anchor", "title": "Anchor"}], max_per_anchor=15)
with patch("backend.crawler.citation_crawler.openalex_get", side_effect=fake_openalex_get):
    papers = crawler.crawl()

titles = [p.title for p in papers]
assert "New MARL method" in titles and "Cites the anchor" in titles
assert not any("Old classic" in t or "Old citer" in t for t in titles), "2024 前的论文应被过滤"
assert len(papers) == 3, f"应得 3 候选, got {len(papers)}"
assert papers[0].source == "citation" and papers[0].doi
assert "citation:reference" in papers[0].categories and "citation:cited_by" in papers[-1].categories
assert papers[0].summary.startswith("multi-agent")
print(f"[1] 锚点扩展正确：{len(papers)} 候选，年份过滤/来源标记/摘要解码 ✓")

# 上限控制（max_per_anchor=1）
crawler2 = CitationCrawler(anchors=[{"id": "x", "doi": "10.x/anchor", "title": "Anchor"}], max_per_anchor=1)
with patch("backend.crawler.citation_crawler.openalex_get", side_effect=fake_openalex_get):
    papers2 = crawler2.crawl()
assert len(papers2) == 2, f"refs+citers 各取1应得 2, got {len(papers2)}"
print("[2] max_per_anchor 上限生效（引用/被引各 1）✓")

# 无 DOI 锚点跳过，不炸
crawler3 = CitationCrawler(anchors=[{"id": "x", "doi": "", "title": "No DOI"}])
assert list(crawler3.crawl_iter()) == []
print("[3] 无 DOI 锚点安全跳过 ✓")

print("\n引文爬虫测试通过 ✅")
