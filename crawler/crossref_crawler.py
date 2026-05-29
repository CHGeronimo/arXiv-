from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import List, Set

import httpx

from crawler.models import Paper
from crawler.subs_store import Journal

logger = logging.getLogger(__name__)

CROSSREF_BASE = "https://api.crossref.org"
MAILTO = "mailto=daily-arxiv@proton.me"


class CrossrefCrawler:
    def __init__(self, journals: List[Journal], fetch_interval_hours: int = 24):
        self.journals = journals
        self.fetch_interval_hours = fetch_interval_hours

    def _needs_update(self, journal: Journal) -> bool:
        if journal.last_updated is None:
            return True
        try:
            last = datetime.fromisoformat(journal.last_updated.replace("Z", "+00:00"))
            diff = datetime.now(timezone.utc) - last
            return diff.total_seconds() >= self.fetch_interval_hours * 3600
        except Exception:
            return True

    def _fetch_recent(self, issn_list: List[str]) -> List[dict]:
        issn_filter = ",".join(f"issn:{i}" for i in issn_list)
        url = (
            f"{CROSSREF_BASE}/works"
            f"?rows=100&sort=created&order=desc"
            f"&filter={issn_filter}&{MAILTO}"
        )
        try:
            resp = httpx.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("items", [])
        except Exception as e:
            logger.error(f"Crossref fetch failed for ISSN {issn_list}: {e}")
            return []

    def _parse_item(self, item: dict, journal: Journal) -> Paper | None:
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        if not title:
            return None

        abstract = item.get("abstract", "")
        abstract = re.sub(r"<[^>]+>", "", abstract)

        authors: List[str] = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            authors.append(f"{given} {family}".strip())

        issn_list = item.get("ISSN", [])
        doi = item.get("DOI", "")

        published = item.get("published", {})
        pub_date = ""
        if published:
            parts = published.get("date-parts", [[]])
            if parts and parts[0]:
                y = parts[0][0]
                m = parts[0][1] if len(parts[0]) > 1 else 1
                d = parts[0][2] if len(parts[0]) > 2 else 1
                pub_date = f"{y:04d}-{m:02d}-{d:02d}"

        url_list = item.get("link", [])
        url = url_list[0].get("URL", "") if url_list else ""
        if not url and doi:
            url = f"https://doi.org/{doi}"

        return Paper(
            id=doi or f"crossref-{abs(hash(title))}",
            source="crossref",
            title=title,
            summary=abstract,
            authors=authors,
            categories=[],
            doi=doi,
            published_date=pub_date,
            url=url,
            pdf="",
            publisher=item.get("publisher", ""),
            journal_title=journal.name,
            issn=issn_list,
        )

    def crawl(self) -> List[Paper]:
        papers: List[Paper] = []
        seen_dois: Set[str] = set()

        for journal in self.journals:
            if not self._needs_update(journal):
                logger.debug(f"Skipping {journal.name}, recently updated")
                continue

            logger.info(f"Fetching {journal.name} (ISSN: {journal.issn})")
            items = self._fetch_recent([journal.issn])

            count = 0
            for item in items:
                paper = self._parse_item(item, journal)
                if paper and paper.doi not in seen_dois:
                    seen_dois.add(paper.doi)
                    papers.append(paper)
                    count += 1

            logger.info(f"Got {count} new papers from {journal.name}")

        return papers
