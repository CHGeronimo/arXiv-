from __future__ import annotations

import logging
import time
from typing import Generator, List, Set

import httpx

from crawler.models import Paper

logger = logging.getLogger(__name__)

S2_AUTHOR_SEARCH = "https://api.semanticscholar.org/graph/v1/author/search"
S2_AUTHOR_PAPERS = "https://api.semanticscholar.org/graph/v1/author"
S2_PAPER_FIELDS = "title,abstract,authors,year,venue,citationCount,externalIds,publicationDate"


def search_authors(query: str, limit: int = 10) -> List[dict]:
    """Search S2 for authors matching query. Returns list of author dicts."""
    params = {"query": query, "limit": limit, "fields": "name,affiliations,paperCount"}
    for attempt in range(3):
        try:
            resp = httpx.get(S2_AUTHOR_SEARCH, params=params, timeout=15)
            if resp.status_code == 429:
                logger.warning("S2 author search rate limited")
                time.sleep(2)
                continue
            resp.raise_for_status()
            return resp.json().get("data") or []
        except Exception as e:
            logger.warning(f"S2 author search attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(1)
    return []


def get_author_papers(
    author_id: str,
    limit: int = 100,
    year_from: int = 2024,
) -> List[dict]:
    """Fetch papers by a specific S2 author."""
    url = f"{S2_AUTHOR_PAPERS}/{author_id}/papers"
    params = {
        "fields": S2_PAPER_FIELDS,
        "limit": min(limit, 100),
        "year": f"{year_from}-",
    }
    for attempt in range(3):
        try:
            resp = httpx.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                logger.warning(f"S2 author papers rate limited for {author_id}")
                time.sleep(2)
                continue
            resp.raise_for_status()
            return resp.json().get("data") or []
        except Exception as e:
            logger.warning(f"S2 author papers attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(1)
    return []


def _parse_paper(item: dict) -> Paper | None:
    paper_id = item.get("paperId") or ""
    title = item.get("title") or ""
    if not title:
        return None

    abstract = item.get("abstract") or ""
    authors: List[str] = [
        a["name"] for a in (item.get("authors") or []) if a.get("name")
    ]

    external_ids = item.get("externalIds") or {}
    doi = external_ids.get("DOI") or ""
    arxiv_id = external_ids.get("ArXiv") or ""
    paper_id_final = doi or paper_id

    url = f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""
    pdf = f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else ""

    venue = item.get("venue") or ""
    citation_count = item.get("citationCount") or 0
    pub_date = item.get("publicationDate") or ""
    year = item.get("year")
    if not pub_date and year is not None:
        pub_date = f"{year}-01-01"

    return Paper(
        id=paper_id_final,
        source="author_s2",
        title=title,
        summary=abstract,
        authors=authors,
        categories=[],
        doi=doi,
        published_date=pub_date,
        url=url,
        pdf=pdf,
        venue=venue,
        citation_count=citation_count if isinstance(citation_count, int) else 0,
    )


class AuthorCrawler:
    """Crawl papers from subscribed authors via S2 Author API."""

    def __init__(
        self,
        authors: List[dict],
        papers_per_author: int = 50,
        year_from: int = 2024,
    ):
        self.authors = authors
        self.papers_per_author = papers_per_author
        self.year_from = year_from

    def crawl_iter(self) -> Generator[Paper, None, None]:
        seen_ids: Set[str] = set()

        for author in self.authors:
            author_id = author.get("authorId", "")
            author_name = author.get("name", "")
            if not author_id:
                continue

            logger.info(f"Fetching papers for author: {author_name} ({author_id})")
            items = get_author_papers(
                author_id,
                limit=self.papers_per_author,
                year_from=self.year_from,
            )

            count = 0
            for item in items:
                paper = _parse_paper(item)
                if paper and paper.id not in seen_ids:
                    seen_ids.add(paper.id)
                    yield paper
                    count += 1

            logger.info(f"Author {author_name}: {count} papers")
            time.sleep(0.5)

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
