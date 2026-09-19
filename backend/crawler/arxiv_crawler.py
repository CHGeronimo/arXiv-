from __future__ import annotations

import logging
import re
from typing import Generator, List, Set

import arxiv
import httpx
from bs4 import BeautifulSoup

from backend.crawler.models import Paper

logger = logging.getLogger(__name__)


class ArxivCrawler:
    """Fetches new papers from arXiv /list/<cat>/new listing pages.

    Parses the HTML listing to get paper IDs that appeared in the latest
    update, filters out already-known IDs, then fetches metadata via
    the arxiv Python package.
    """
    def __init__(
        self,
        categories: List[str],
        existing_ids: Set[str] | None = None,
        delay_seconds: float = 1.0,
        num_retries: int = 5,
        backfill_since: str | None = None,
    ):
        self.categories = categories
        self.existing_ids = existing_ids or set()
        self.backfill_since = backfill_since  # "YYYY-MM-DD"，断档回补起点
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=delay_seconds,
            num_retries=num_retries,
        )

    def _parse_new_list(self, html: str, target_cats: Set[str]) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        dlpage = soup.find("div", id="dlpage")
        if not dlpage:
            return []

        anchors = []
        for li in dlpage.find_all("li"):
            a = li.find("a")
            if a and a.get("href") and "item" in a.get("href", ""):
                try:
                    anchors.append(int(a["href"].split("item")[-1]))
                except ValueError:
                    pass

        paper_ids: List[str] = []
        for dt in dlpage.find_all("dt"):
            paper_anchor = dt.find("a", attrs={"name": re.compile(r"^item")})
            if not paper_anchor:
                continue
            try:
                paper_num = int(paper_anchor["name"].split("item")[-1])
            except ValueError:
                continue
            if anchors and paper_num >= anchors[-1]:
                continue

            abstract_link = dt.find("a", title="Abstract")
            if not abstract_link:
                continue
            arxiv_id = abstract_link["href"].split("/")[-1]

            dd = dt.find_next_sibling("dd")
            if not dd:
                continue
            subjects = dd.find(class_="list-subjects")
            if subjects:
                primary = subjects.find(class_="primary-subject")
                cats_text = primary.get_text() if primary else subjects.get_text()
                cats_in_paper = set(re.findall(r"\(([^)]+)\)", cats_text))
                if not cats_in_paper.intersection(target_cats):
                    continue
            paper_ids.append(arxiv_id)

        return paper_ids

    def fetch_new_ids(self) -> List[str]:
        all_ids: List[str] = []
        seen: Set[str] = set()
        target_cats = set(self.categories)

        with httpx.Client(follow_redirects=True, timeout=30) as client:
            for cat in self.categories:
                try:
                    resp = client.get(f"https://arxiv.org/list/{cat}/new")
                    resp.raise_for_status()
                    ids = self._parse_new_list(resp.text, target_cats)
                    for pid in ids:
                        if pid not in seen:
                            seen.add(pid)
                            all_ids.append(pid)
                    logger.info(f"  {cat}: {len(ids)} 篇")
                except Exception as e:
                    logger.error(f"获取 {cat}/new 失败: {e}")

        return all_ids

    def fetch_metadata_iter(self, paper_ids: List[str]) -> Generator[Paper, None, None]:
        """Fetch metadata in batches of up to 100 IDs per API call.

        Much faster than per-paper queries — arXiv API supports batch id_list.
        """
        batch_size = 100
        for i in range(0, len(paper_ids), batch_size):
            batch = paper_ids[i:i + batch_size]
            try:
                search = arxiv.Search(id_list=batch)
                fetched_in_batch = {}
                for result in self.client.results(search):
                    # arxiv.Client may return IDs with version suffix (e.g. 2606.04493v1)
                    # Normalize to base ID for matching
                    raw_id = result.entry_id.split("/")[-1]
                    base_id = re.sub(r"v\d+$", "", raw_id)
                    fetched_in_batch[base_id] = result

                for pid in batch:
                    result = fetched_in_batch.get(pid)
                    if result is None:
                        logger.warning(f"元数据缺失 {pid}")
                        continue
                    yield Paper(
                        id=pid,
                        source="arxiv",
                        title=result.title,
                        summary=result.summary,
                        authors=[a.name for a in result.authors],
                        categories=result.categories,
                        doi=result.doi or "",
                        published_date=result.published.isoformat()[:10],
                        url=f"https://arxiv.org/abs/{pid}",
                        pdf=f"https://arxiv.org/pdf/{pid}",
                        publisher="arXiv",
                        comment=result.comment,
                    )
                logger.debug(f"元数据批次 {i//batch_size + 1}: {len(fetched_in_batch)}/{len(batch)} 篇")
            except Exception as e:
                logger.error(f"元数据批次失败 ({i//batch_size + 1}): {e}")

    def _backfill_ids(self) -> List[str]:
        """Query the arXiv API by submittedDate range for days the new-listing
        crawl may have missed (daemon downtime). /list/<cat>/new only shows the
        latest announcement — skipped days are gone forever without this."""
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        start = self.backfill_since.replace("-", "")
        ids: List[str] = []
        for cat in self.categories:
            try:
                search = arxiv.Search(
                    query=f"cat:{cat} AND submittedDate:[{start}0000 TO {today}2359]",
                    max_results=400,
                    sort_by=arxiv.SortCriterion.SubmittedDateDescending,
                )
                for result in self.client.results(search):
                    raw = result.entry_id.split("/")[-1]
                    ids.append(re.sub(r"v\d+$", "", raw))
            except Exception as e:
                logger.warning(f"arXiv 回补 {cat} 失败: {e}")
        return ids

    def crawl_iter(self) -> Generator[Paper, None, None]:
        ids = self.fetch_new_ids()
        if self.backfill_since:
            backfilled = self._backfill_ids()
            before = len(set(ids))
            ids = list(dict.fromkeys(ids + backfilled))
            logger.info(f"[arxiv] 回补窗口 {self.backfill_since} → 今天: 新增 {len(set(ids)) - before} 个 ID")
        new_ids = [i for i in ids if i not in self.existing_ids]
        logger.info(f"[arxiv] 共 {len(ids)} 篇, {len(new_ids)} 篇新增 (跳过 {len(ids) - len(new_ids)} 篇已知)")
        yield from self.fetch_metadata_iter(new_ids)

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
