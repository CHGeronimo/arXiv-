from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Generator, List, Set

import httpx

from crawler.models import Paper
from crawler.subs_store import Conference

logger = logging.getLogger(__name__)

DBLP_BASE = "https://dblp.uni-trier.de/search/publ/api"
OPENALEX_BASE = "https://api.openalex.org/works"

VENUE_MAP = {
    "CVPR": "CVPR",
    "ICCV": "ICCV",
    "ECCV": "ECCV",
    "NeurIPS": "NeurIPS",
    "ICML": "ICML",
    "ICLR": "ICLR",
    "ACL": "ACL",
    "EMNLP": "EMNLP",
    "NAACL": "NAACL",
}


class DblpCrawler:
    def __init__(self, conferences: List[Conference], fetch_interval_hours: int = 24):
        self.conferences = conferences
        self.fetch_interval_hours = fetch_interval_hours

    def _needs_update(self, conf: Conference) -> bool:
        if conf.last_updated is None:
            return True
        try:
            last = datetime.fromisoformat(conf.last_updated.replace("Z", "+00:00"))
            diff = datetime.now(timezone.utc) - last
            return diff.total_seconds() >= self.fetch_interval_hours * 3600
        except Exception:
            return True

    def _fetch_recent(self, venue: str, year: int) -> List[dict]:
        dblp_venue = VENUE_MAP.get(venue, venue)
        query = f"venue:{dblp_venue} year:{year}"
        url = f"{DBLP_BASE}?q={query}&format=json&h=100"
        for attempt in range(3):
            try:
                resp = httpx.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                hits = data.get("result", {}).get("hits", {}).get("hit", [])
                return hits if isinstance(hits, list) else [hits]
            except Exception as e:
                logger.warning(f"DBLP fetch attempt {attempt+1}/3 failed: {e}")
                if attempt == 2:
                    logger.error(f"DBLP fetch failed for {venue} {year} after 3 retries")
        return []

    def _parse_hit(self, hit: dict, venue: str) -> Paper | None:
        info = hit.get("info", {})
        title = info.get("title", "")
        if not title:
            return None

        # Authors: single dict for 1 author, list of dicts for multiple
        raw_authors = info.get("authors", {}).get("author", [])
        if isinstance(raw_authors, dict):
            raw_authors = [raw_authors]
        authors = [a.get("text", "") for a in raw_authors if a.get("text")]

        doi = info.get("doi", "")
        year = info.get("year", "")
        url = info.get("url", "")
        ee = info.get("ee", "")
        key = info.get("key", "")

        return Paper(
            id=doi or f"dblp-{abs(hash(title))}",
            source="dblp",
            title=title,
            summary="",
            authors=authors,
            categories=[],
            doi=doi,
            published_date=f"{year}-01-01" if year else "",
            url=ee or url,
            pdf="",
            publisher="DBLP",
            venue=f"{venue} {year}",
        )

    def _fill_abstracts_openalex(self, papers: List[Paper]) -> None:
        dois = [p.doi for p in papers if p.doi and not p.summary]
        if not dois:
            return
        logger.info(f"Filling abstracts via OpenAlex for {len(dois)} papers")
        doi_to_paper = {p.doi: p for p in papers if p.doi}

        for doi in dois:
            try:
                url = f"{OPENALEX_BASE}/doi:{doi}"
                resp = httpx.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                inv_index = data.get("abstract_inverted_index")
                if inv_index:
                    words = sorted(
                        [(pos, w) for w, positions in inv_index.items() for pos in positions]
                    )
                    abstract = " ".join(w for _, w in words)
                    paper = doi_to_paper.get(doi)
                    if paper:
                        paper.summary = abstract
            except Exception:
                continue

    def crawl_iter(self) -> Generator[Paper, None, None]:
        seen_dois: Set[str] = set()
        seen_titles: Set[str] = set()
        current_year = datetime.now(timezone.utc).year

        for conf in self.conferences:
            if not self._needs_update(conf):
                logger.debug(f"Skipping {conf.venue}, recently updated")
                continue

            for year in (current_year, current_year - 1):
                logger.info(f"Fetching {conf.venue} {year} from DBLP")
                hits = self._fetch_recent(conf.venue, year)

                batch: List[Paper] = []
                for hit in hits:
                    paper = self._parse_hit(hit, conf.venue)
                    if paper is None:
                        continue
                    dedup_key = paper.doi if paper.doi else paper.title.lower().strip()
                    if dedup_key in seen_dois:
                        continue
                    seen_dois.add(dedup_key)
                    batch.append(paper)

                self._fill_abstracts_openalex(batch)

                for paper in batch:
                    yield paper
                logger.info(f"Got {len(batch)} new papers from {conf.venue} {year}")

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
