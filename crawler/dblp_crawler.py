from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Generator, List, Set

import httpx

from crawler.models import Paper
from crawler.subs_store import Conference

logger = logging.getLogger(__name__)

DBLP_BASE = "https://dblp.uni-trier.de/search/publ/api"
OPENALEX_BASE = "https://api.openalex.org/works"

VENUE_MAP = {
    # AI
    "CVPR": "CVPR", "ICCV": "ICCV", "ECCV": "ECCV",
    "NeurIPS": "NeurIPS", "ICML": "ICML", "ICLR": "ICLR",
    "AAAI": "AAAI", "IJCAI": "IJCAI",
    "ACL": "ACL", "EMNLP": "EMNLP", "NAACL": "NAACL", "COLING": "COLING",
    "UAI": "UAI", "ECAI": "ECAI", "AAMAS": "AAMAS",
    "ICRA": "ICRA", "IROS": "IROS",
    "MICCAI": "MICCAI",
    # Data/IR
    "SIGMOD": "SIGMOD", "SIGKDD": "KDD", "ICDE": "ICDE",
    "SIGIR": "SIGIR", "VLDB": "VLDB",
    "WWW": "TheWebConf", "WSDM": "WSDM",
    "CIKM": "CIKM", "ICDM": "ICDM", "RecSys": "RecSys",
    # Graphics/Multimedia
    "ACMMM": "ACMMM", "SIGGRAPH": "SIGGRAPH",
    "INTERSPEECH": "INTERSPEECH", "ICASSP": "ICASSP",
    "ICME": "ICME",
    # Theory
    "STOC": "STOC", "FOCS": "FOCS", "SODA": "SODA",
    # SE
    "ICSE": "ICSE", "FSE": "FSE", "ASE": "ASE",
    "SOSP": "SOSP", "OSDI": "OSDI",
    # Network
    "SIGCOMM": "SIGCOMM", "NSDI": "NSDI", "INFOCOM": "INFOCOM",
    # Security
    "CCS": "CCS", "NDSS": "NDSS",
    # Architecture
    "ISCA": "ISCA", "MICRO": "MICRO", "HPCA": "HPCA",
    "ASPLOS": "ASPLOS", "SC": "SC", "DAC": "DAC",
    # HCI
    "CHI": "CHI", "CSCW": "CSCW", "UbiComp": "UbiComp",
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
                wait = (attempt + 1) * 3
                logger.warning(f"DBLP 获取第 {attempt+1}/3 次尝试失败: {e}，{wait}s 后重试")
                if attempt == 2:
                    logger.error(f"DBLP 获取 {venue} {year} 在 3 次重试后失败")
                else:
                    time.sleep(wait)
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
        logger.info(f"通过 OpenAlex 补充 {len(dois)} 篇论文的摘要")
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
                logger.info(f"从 DBLP 获取 {conf.venue} {year}")
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
                logger.info(f"从 {conf.venue} {year} 获取到 {len(batch)} 篇新论文")

            # 会议间间隔 2s，避免 DBLP 限流
            time.sleep(2)

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
