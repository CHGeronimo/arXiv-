"""crawler/citation_crawler.py — Citation-following discovery via OpenAlex.

Anchors are papers the screening funnel rated must-read or the user liked.
For each anchor we pull its references and recent citers from OpenAlex
(free, globally throttled by openalex_client — no LLM involved in fetching),
keep recent high-signal candidates, and yield Paper objects that flow through
the standard screening funnel. LLM cost is therefore bounded by the local
pre-filter + quick_filter, same as every other source.
"""
from __future__ import annotations

import logging
import time
from typing import Generator, List, Set

from crawler.models import Paper
from crawler.openalex_client import openalex_get

logger = logging.getLogger(__name__)

WORKS = "https://api.openalex.org/works"

_SELECT = ("id,doi,title,abstract_inverted_index,authorships,"
           "primary_location,publication_year,cited_by_count")


def _decode_abstract(inv_index: dict | None) -> str:
    if not inv_index:
        return ""
    length = max(max(pos) for pos in inv_index.values()) + 1
    words = [""] * length
    for word, positions in inv_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words)


class CitationCrawler:
    """Expand anchor papers through their citation neighborhood.

    anchors: [{id, doi, title}] — papers worth following citations from.
    max_per_anchor caps references/citers separately; year_from drops old
    classics (they're either already known or out of discovery scope).
    """

    def __init__(self, anchors: List[dict], max_per_anchor: int = 15, year_from: int = 2024):
        self.anchors = anchors
        self.max_per_anchor = max_per_anchor
        self.year_from = year_from

    def _work_by_doi(self, doi: str) -> dict | None:
        return openalex_get(f"{WORKS}/doi:{doi}")

    def _batch_works(self, referenced: List[str]) -> List[dict]:
        """Batch-fetch works by OpenAlex ID. referenced_works returns full
        URLs (https://openalex.org/W123) but the filter wants bare W-ids."""
        ids = [r.rsplit("/", 1)[-1] for r in referenced if r]
        out: List[dict] = []
        for i in range(0, len(ids), 50):
            chunk = ids[i:i + 50]
            data = openalex_get(WORKS, {
                "filter": "ids.openalex:" + "|".join(chunk),
                "per_page": 50,
                "select": _SELECT,
            }) or {}
            out.extend(data.get("results") or [])
        return out

    def _citing_works(self, openalex_id: str) -> List[dict]:
        data = openalex_get(WORKS, {
            "filter": f"cites:{openalex_id}",
            "per_page": 25,
            "sort": "publication_date:desc",
            "select": _SELECT,
        }) or {}
        return data.get("results") or []

    def _to_paper(self, item: dict, relation: str) -> Paper | None:
        title = item.get("title") or ""
        if not title:
            return None
        doi = (item.get("doi") or "").replace("https://doi.org/", "")
        oa_id = (item.get("id") or "").split("/")[-1]
        year = item.get("publication_year") or 0
        loc = item.get("primary_location") or {}
        return Paper(
            id=doi or oa_id,
            source="citation",
            title=title,
            summary=_decode_abstract(item.get("abstract_inverted_index")),
            authors=[a.get("author", {}).get("display_name", "")
                     for a in (item.get("authorships") or []) if a.get("author", {}).get("display_name")],
            categories=[f"citation:{relation}"],
            doi=doi,
            published_date=f"{year}-01-01" if year else "",
            url=f"https://doi.org/{doi}" if doi else (item.get("id") or ""),
            pdf=loc.get("pdf_url") or "",
            venue=(loc.get("source") or {}).get("display_name", ""),
            citation_count=item.get("cited_by_count") or 0,
        )

    def crawl_iter(self) -> Generator[Paper, None, None]:
        seen: Set[str] = set()
        for anchor in self.anchors:
            doi = anchor.get("doi") or ""
            if not doi:
                continue
            work = self._work_by_doi(doi)
            if not work or not work.get("id"):
                logger.warning(f"引文锚点未找到: {anchor.get('title', '')[:50]} ({doi})")
                continue
            oa_id = work["id"].split("/")[-1]

            refs = [
                w for w in self._batch_works(work.get("referenced_works") or [])
                if (w.get("publication_year") or 0) >= self.year_from
            ]
            # 上限内优先高被引（高信号）
            refs.sort(key=lambda w: -(w.get("cited_by_count") or 0))
            citers = [
                w for w in self._citing_works(oa_id)
                if (w.get("publication_year") or 0) >= self.year_from
            ]

            candidates = (
                [("reference", w) for w in refs[:self.max_per_anchor]]
                + [("cited_by", w) for w in citers[:self.max_per_anchor]]
            )
            count = 0
            for relation, item in candidates:
                p = self._to_paper(item, relation)
                if p and p.id and p.id not in seen:
                    seen.add(p.id)
                    yield p
                    count += 1
            logger.info(
                f"引文扩展 [{anchor.get('title', '')[:40]}]: "
                f"{len(refs)} 近引文 / {len(citers)} 近被引 → {count} 候选"
            )
            time.sleep(0.2)

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
