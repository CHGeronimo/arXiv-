from __future__ import annotations

import logging
import time
from typing import Generator, List, Set

import httpx

from crawler.models import Paper

logger = logging.getLogger(__name__)

S2_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,abstract,authors,year,venue,citationCount,externalIds,publicationDate"


class S2Crawler:
    def __init__(self, keywords: List[str], max_per_keyword: int = 20, year_from: int = 2024):
        self.keywords = keywords
        self.max_per_keyword = max_per_keyword
        self.year_from = year_from

    def _search(self, keyword: str) -> List[dict]:
        params = {
            "query": keyword,
            "limit": self.max_per_keyword,
            "fields": S2_FIELDS,
            "year": f"{self.year_from}-",
        }
        for attempt in range(3):
            try:
                resp = httpx.get(S2_BASE, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = 3 * (2 ** attempt)
                    logger.warning(
                        f"S2 rate limited on '{keyword}', backoff {wait}s"
                    )
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data.get("data") or []
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait = 3 * (2 ** attempt)
                    logger.warning(
                        f"S2 rate limited on '{keyword}', backoff {wait}s"
                    )
                    time.sleep(wait)
                    continue
                logger.warning(
                    f"S2 search attempt {attempt+1}/3 failed: {e}"
                )
            except Exception as e:
                logger.warning(
                    f"S2 search attempt {attempt+1}/3 failed: {e}"
                )
            if attempt < 2:
                time.sleep(1)
        logger.error(f"S2 search failed for keyword '{keyword}' after 3 retries")
        return []

    def _parse_paper(self, item: dict, keyword: str) -> Paper | None:
        paper_id = item.get("paperId") or ""
        title = item.get("title") or ""
        if not title:
            return None

        abstract = item.get("abstract") or ""

        authors: List[str] = []
        for author in item.get("authors") or []:
            name = author.get("name", "")
            if name:
                authors.append(name)

        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI") or ""
        arxiv_id = external_ids.get("ArXiv") or ""

        paper_id_final = doi or paper_id

        url = f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""

        pdf = ""
        if arxiv_id:
            pdf = f"https://arxiv.org/pdf/{arxiv_id}"

        venue = item.get("venue") or ""
        citation_count = item.get("citationCount") or 0
        pub_date = item.get("publicationDate") or ""
        year = item.get("year")

        if pub_date == "" and year is not None:
            pub_date = f"{year}-01-01"

        return Paper(
            id=paper_id_final,
            source="semantic_scholar",
            title=title,
            summary=abstract,
            authors=authors,
            categories=[keyword],
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
            logger.info(f"S2 searching: '{keyword}'")
            items = self._search(keyword)

            count = 0
            for item in items:
                paper = self._parse_paper(item, keyword)
                if paper and paper.id not in seen_ids:
                    seen_ids.add(paper.id)
                    yield paper
                    count += 1

            logger.info(f"S2 got {count} papers for '{keyword}'")
            time.sleep(3)

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
