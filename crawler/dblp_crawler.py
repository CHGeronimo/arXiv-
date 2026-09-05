"""crawler/dblp_crawler.py — Conference paper fetching via OpenAlex (replaces DBLP API).

OpenAlex provides stable venue-based search without DBLP's 500/429 errors.
Requests go through the shared throttled client (openalex_client) so this
crawler stays polite even when other OpenAlex crawlers run concurrently.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Generator, List, Set

from crawler.models import Paper
from crawler.openalex_client import openalex_get
from crawler.subs_store import Conference

logger = logging.getLogger(__name__)

OPENALEX_BASE = "https://api.openalex.org/works"

# Map user-facing venue names to OpenAlex source display names for matching
VENUE_MAP = {
    "CVPR": "CVPR", "ICCV": "ICCV", "ECCV": "ECCV",
    "NeurIPS": "NeurIPS", "ICML": "ICML", "ICLR": "ICLR",
    "AAAI": "AAAI", "IJCAI": "IJCAI",
    "ACL": "ACL", "EMNLP": "EMNLP", "NAACL": "NAACL", "COLING": "COLING",
    "UAI": "UAI", "ECAI": "ECAI", "AAMAS": "AAMAS",
    "ICRA": "ICRA", "IROS": "IROS",
    "MICCAI": "MICCAI",
    "SIGMOD": "SIGMOD", "SIGKDD": "KDD", "ICDE": "ICDE",
    "SIGIR": "SIGIR", "VLDB": "VLDB",
    "WWW": "TheWebConf", "WWW_conf": "The Web Conference",
    "WSDM": "WSDM",
    "CIKM": "CIKM", "ICDM": "ICDM", "RecSys": "RecSys",
    "ACMMM": "ACM Multimedia", "SIGGRAPH": "SIGGRAPH",
    "INTERSPEECH": "INTERSPEECH", "ICASSP": "ICASSP",
    "ICME": "ICME",
    "STOC": "STOC", "FOCS": "FOCS", "SODA": "SODA",
    "ICSE": "ICSE", "FSE": "FSE", "ASE": "ASE",
    "SOSP": "SOSP", "OSDI": "OSDI",
    "SIGCOMM": "SIGCOMM", "NSDI": "NSDI", "INFOCOM": "INFOCOM",
    "CCS": "CCS", "NDSS": "NDSS",
    "EUROCRYPT": "EUROCRYPT", "S&P": "IEEE S&P", "CRYPTO": "CRYPTO",
    "USENIXSecurity": "USENIX Security",
    "ISCA": "ISCA", "MICRO": "MICRO", "HPCA": "HPCA",
    "ASPLOS": "ASPLOS", "SC": "SC", "DAC": "DAC",
    "CHI": "CHI", "CSCW": "CSCW", "UbiComp": "UbiComp",
    "UIST": "UIST",
    "MobiCom": "MobiCom", "RTSS": "RTSS",
}


class DblpCrawler:
    def __init__(self, conferences: List[Conference], fetch_interval_hours: int = 24,
                 rotate_days: int = 0):
        self.conferences = conferences
        self.fetch_interval_hours = fetch_interval_hours
        # OpenAlex 按请求计费（1000 credits/天，全量 75 会议×2年=150 请求/天会
        # 烧穿额度）——按天轮换：每天只抓 1/rotate_days 的会议，7 天扫全量
        self.rotate_days = rotate_days

    def _needs_update(self, conf: Conference) -> bool:
        if conf.last_updated is None:
            return True
        try:
            last = datetime.fromisoformat(conf.last_updated.replace("Z", "+00:00"))
            diff = datetime.now(timezone.utc) - last
            return diff.total_seconds() >= self.fetch_interval_hours * 3600
        except Exception:
            return True

    def _fetch_venue(self, venue: str, year: int) -> List[dict]:
        openalex_venue = VENUE_MAP.get(venue, venue)
        params = {
            "filter": f"from_publication_date:{year}-01-01,to_publication_date:{year}-12-31,type:article",
            "search": openalex_venue,
            "per_page": 100,
            "sort": "relevance_score:desc",
            "select": "id,doi,title,abstract_inverted_index,authorships,primary_location,publication_year,cited_by_count,concepts",
        }
        data = openalex_get(OPENALEX_BASE, params) or {}
        results = data.get("results") or []
        # Post-filter: only keep papers whose venue matches
        matched = []
        for item in results:
            loc = item.get("primary_location") or {}
            source = loc.get("source") or {}
            source_name = (source.get("display_name") or "").lower()
            if openalex_venue.lower() in source_name or source_name in openalex_venue.lower():
                matched.append(item)
        return matched

    def _decode_abstract(self, inv_index: dict | None) -> str:
        if not inv_index:
            return ""
        length = max(max(pos) for pos in inv_index.values()) + 1
        words = [""] * length
        for word, positions in inv_index.items():
            for pos in positions:
                words[pos] = word
        return " ".join(words)

    def _parse_paper(self, item: dict, venue: str) -> Paper | None:
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
        url = f"https://doi.org/{doi}" if doi else (openalex_id or "")
        pdf = loc.get("pdf_url") or ""

        pub_year = item.get("publication_year")
        pub_date = f"{pub_year}-01-01" if pub_year else ""

        citation_count = item.get("cited_by_count") or 0

        return Paper(
            id=paper_id,
            source="dblp",
            title=title,
            summary=abstract,
            authors=authors,
            categories=[],
            doi=doi,
            published_date=pub_date,
            url=url,
            pdf=pdf,
            venue=f"{venue} {pub_year}" if pub_year else venue,
            citation_count=citation_count if isinstance(citation_count, int) else 0,
        )

    def crawl_iter(self) -> Generator[Paper, None, None]:
        seen_dois: Set[str] = set()
        current_year = datetime.now(timezone.utc).year

        conferences = self.conferences
        if self.rotate_days > 1:
            day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
            conferences = [c for i, c in enumerate(self.conferences)
                           if (day_of_year + i) % self.rotate_days == 0]
            logger.info(f"会议轮换: 今日 {len(conferences)}/{len(self.conferences)} 个（每 {self.rotate_days} 天全量一轮）")

        for conf in conferences:
            if not self._needs_update(conf):
                logger.debug(f"Skipping {conf.venue}, recently updated")
                continue

            for year in (current_year, current_year - 1):
                logger.info(f"从 OpenAlex 获取 {conf.venue} {year}")
                items = self._fetch_venue(conf.venue, year)

                batch: List[Paper] = []
                for item in items:
                    paper = self._parse_paper(item, conf.venue)
                    if paper is None:
                        continue
                    dedup_key = paper.doi if paper.doi else paper.title.lower().strip()
                    if dedup_key in seen_dois:
                        continue
                    seen_dois.add(dedup_key)
                    batch.append(paper)

                for paper in batch:
                    yield paper
                logger.info(f"从 {conf.venue} {year} 获取到 {len(batch)} 篇新论文")

            time.sleep(0.2)

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
