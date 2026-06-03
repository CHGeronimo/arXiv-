from __future__ import annotations

import logging
import re
from typing import Generator, List, Set

import arxiv
import httpx
from bs4 import BeautifulSoup

from crawler.models import Paper

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
        delay_seconds: float = 5.0,
        num_retries: int = 5,
    ):
        self.categories = categories
        self.existing_ids = existing_ids or set()
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
        for pid in paper_ids:
            if pid in self.existing_ids:
                continue
            try:
                search = arxiv.Search(id_list=[pid])
                result = next(self.client.results(search))
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
            except Exception as e:
                logger.error(f"获取元数据失败 {pid}: {e}")

    def crawl_iter(self) -> Generator[Paper, None, None]:
        ids = self.fetch_new_ids()
        new_ids = [i for i in ids if i not in self.existing_ids]
        logger.info(f"[arxiv] 共 {len(ids)} 篇, {len(new_ids)} 篇新增 (跳过 {len(ids) - len(new_ids)} 篇已知)")
        yield from self.fetch_metadata_iter(new_ids)

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
