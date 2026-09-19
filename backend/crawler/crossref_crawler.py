from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Generator, List, Set

import httpx

from backend.crawler.models import Paper
from backend.crawler.openalex_client import openalex_get
from backend.crawler.subs_store import Journal

logger = logging.getLogger(__name__)

CROSSREF_BASE = "https://api.crossref.org"
# polite pool 联系邮箱（可选）：设置 CROSSREF_EMAIL 环境变量后自动附加
_contact = os.environ.get("CROSSREF_EMAIL", "").strip()
MAILTO = f"mailto={_contact}" if _contact else ""


class CrossrefCrawler:
    def __init__(self, journals: List[Journal], fetch_interval_hours: int = 24,
                 known_ids: Set[str] | None = None):
        self.journals = journals
        self.fetch_interval_hours = fetch_interval_hours
        # 已入库/已忽略的论文 ID：爬取层直接跳过——否则每晚会为 ~6700 篇已知
        # 论文下载元数据并逐 DOI 调 OpenAlex 回填摘要（实测 4671 请求/晚，
        # 回填结果因论文已存在根本不写库，纯烧配额）
        self.known_ids = known_ids or set()

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
            f"&filter={issn_filter}"
        ) + (f"&{MAILTO}" if MAILTO else "")
        for attempt in range(3):
            try:
                resp = httpx.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("items", [])
            except Exception as e:
                logger.warning(f"Crossref fetch attempt {attempt+1}/3 failed: {e}")
                if attempt == 2:
                    logger.error(f"Crossref fetch failed for ISSN {issn_list} after 3 retries")
        return []

    def _classify_article(self, item: dict) -> str:
        doi = item.get("DOI", "")
        # Nature: d41586=news, s41586=research
        if "/d41586-" in doi:
            return "news"
        if "/s41586-" in doi:
            return "research"
        # Generic: has abstract = likely research
        if item.get("abstract"):
            return "research"
        # Many publishers (IEEE, ACM) don't provide abstracts to Crossref
        # but their items are still research articles. Use type as fallback.
        item_type = item.get("type", "").lower()
        if "journal" in item_type or "article" in item_type:
            return "research"
        return "news"

    _SKIP_PREFIXES = (
        "Author Correction:",
        "Publisher Correction:",
        "Erratum:",
        "Corrigendum:",
        "Correction:",
    )

    def _is_noise(self, title: str) -> bool:
        return any(title.startswith(p) for p in self._SKIP_PREFIXES)

    def _parse_item(self, item: dict, journal: Journal) -> Paper | None:
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        if not title:
            return None
        if self._is_noise(title):
            return None
        if self._classify_article(item) != "research":
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
            article_type=self._classify_article(item),
        )

    def _fill_abstracts_openalex(self, papers: List[Paper]) -> None:
        dois = [p.doi for p in papers if p.doi and not p.summary]
        if not dois:
            return
        logger.info(f"通过 OpenAlex 补充 {len(dois)} 篇论文的摘要")
        doi_to_paper = {p.doi: p for p in papers if p.doi}

        for doi in dois:
            data = openalex_get(f"https://api.openalex.org/works/doi:{doi}")
            if not data:
                continue
            inv_index = data.get("abstract_inverted_index")
            if inv_index:
                words = sorted(
                    [(pos, w) for w, positions in inv_index.items() for pos in positions]
                )
                abstract = " ".join(w for _, w in words)
                paper = doi_to_paper.get(doi)
                if paper:
                    paper.summary = abstract

    def crawl_iter(self) -> Generator[Paper, None, None]:
        seen_dois: Set[str] = set()

        for journal in self.journals:
            if not self._needs_update(journal):
                logger.debug(f"Skipping {journal.name}, recently updated")
                continue

            logger.info(f"Fetching {journal.name} (ISSN: {journal.issn})")
            items = self._fetch_recent([journal.issn])

            batch: List[Paper] = []
            for item in items:
                paper = self._parse_item(item, journal)
                if paper is None:
                    continue
                dedup_key = paper.doi if paper.doi else paper.title.lower().strip()
                if dedup_key in seen_dois:
                    continue
                if paper.id in self.known_ids or dedup_key in self.known_ids:
                    continue  # 已知论文：跳过回填与后续处理
                seen_dois.add(dedup_key)
                batch.append(paper)

            self._fill_abstracts_openalex(batch)

            for paper in batch:
                yield paper
            logger.info(f"从 {journal.name} 获取到 {len(batch)} 篇新论文")

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
