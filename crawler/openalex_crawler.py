"""crawler/openalex_crawler.py — OpenAlex keyword search (replaces S2)."""
from __future__ import annotations

import logging
import time
from typing import Generator, List, Set

from crawler.models import Paper
from crawler.openalex_client import openalex_get

logger = logging.getLogger(__name__)

OPENALEX_BASE = "https://api.openalex.org/works"


class OpenAlexCrawler:
    """Search OpenAlex API for papers by keyword.

    Replaces S2Crawler for broader coverage. OpenAlex has no rate limit
    for small requests, making it more reliable for daily crawls.
    """
    def __init__(self, keywords: List[str], max_per_keyword: int = 10, year_from: int = 2024):
        self.keywords = keywords
        self.max_per_keyword = max_per_keyword
        self.year_from = year_from

    def _search(self, keyword: str) -> List[dict]:
        params = {
            "search": keyword,
            "per_page": self.max_per_keyword,
            "filter": f"from_publication_date:{self.year_from}-01-01,type:article",
            # 日期降序：relevance 排序下老经典长期霸榜，新论文进不了 top-N
            # 就永远发现不了；精度交给下游漏斗
            "sort": "publication_date:desc",
            "select": "id,doi,title,abstract_inverted_index,authorships,primary_location,publication_year,cited_by_count,concepts",
        }
        data = openalex_get(OPENALEX_BASE, params) or {}
        return data.get("results") or []

    def _decode_abstract(self, inv_index: dict | None) -> str:
        """Decode OpenAlex inverted index abstract to plain text."""
        if not inv_index:
            return ""
        length = max(max(pos) for pos in inv_index.values()) + 1
        words = [""] * length
        for word, positions in inv_index.items():
            for pos in positions:
                words[pos] = word
        return " ".join(words)

    def _parse_paper(self, item: dict, keyword: str) -> Paper | None:
        title = item.get("title") or ""
        if not title:
            return None

        abstract = self._decode_abstract(item.get("abstract_inverted_index"))

        authors: List[str] = []
        for a in item.get("authorships") or []:
            name = a.get("author", {}).get("display_name", "")
            if name:
                authors.append(name)

        doi = (item.get("doi") or "").replace("https://doi.org/", "")

        openalex_id = item.get("id", "")
        paper_id = doi or openalex_id.split("/")[-1] if openalex_id else ""

        loc = item.get("primary_location") or {}
        source = loc.get("source") or {}
        venue = source.get("display_name", "")

        url = f"https://openalex.org{openalex_id.split('.org')[-1]}" if openalex_id else ""
        if doi:
            url = f"https://doi.org/{doi}"

        pdf = ""
        pdf_url = loc.get("pdf_url") or ""
        if pdf_url:
            pdf = pdf_url

        citation_count = item.get("cited_by_count") or 0
        pub_year = item.get("publication_year")
        pub_date = f"{pub_year}-01-01" if pub_year else ""

        categories = [keyword]
        for concept in (item.get("concepts") or [])[:3]:
            cname = concept.get("display_name", "")
            if cname:
                categories.append(cname)

        return Paper(
            id=paper_id,
            source="openalex",
            title=title,
            summary=abstract,
            authors=authors,
            categories=categories,
            doi=doi,
            published_date=pub_date,
            url=url,
            pdf=pdf,
            venue=venue,
            citation_count=citation_count if isinstance(citation_count, int) else 0,
        )

    def crawl_iter(self) -> Generator[Paper, None, None]:
        seen_ids: Set[str] = set()

        for keyword in self.keywords:
            logger.info(f"OpenAlex 搜索: '{keyword}'")
            items = self._search(keyword)

            count = 0
            for item in items:
                paper = self._parse_paper(item, keyword)
                if paper and paper.id and paper.id not in seen_ids:
                    seen_ids.add(paper.id)
                    yield paper
                    count += 1

            logger.info(f"OpenAlex '{keyword}' 获取到 {count} 篇论文")
            time.sleep(0.2)

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
