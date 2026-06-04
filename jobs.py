"""Crawler job orchestration with BaseCrawlerJob template pattern.

Each crawler type is a thin subclass that defines:
- _create_crawler(subs): build the crawler instance (or return None to skip)
- _skip_reason(subs): human-readable reason for skipping
- _post_run(subs, fetched_info): optional post-crawl bookkeeping

The base class handles the run/skip/error lifecycle.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from ai.digest import generate_digest
from ai.enhance import enhance_single, load_research_profile
from ai.keyword_expander import expand_keywords
from crawler.arxiv_crawler import ArxivCrawler
from crawler.author_crawler import AuthorCrawler
from crawler.crossref_crawler import CrossrefCrawler
from crawler.dblp_crawler import DblpCrawler
from crawler.openalex_crawler import OpenAlexCrawler
from crawler.subs_store import Subscriptions

from db import get_conn
from paper_store import (
    AI_LANGUAGE,
    append_paper,
    get_ai_chain,
    _insert_ai_row,
)

logger = logging.getLogger("jobs")

_job_status: dict[str, dict] = {}
_ai_max_workers = int(os.environ.get("AI_MAX_WORKERS", "10"))
_shutdown = False

SUBS_PATH = "subscriptions.json"


def _load_subs() -> Subscriptions:
    return Subscriptions.load(SUBS_PATH)


def _save_subs(subs: Subscriptions) -> None:
    subs.save(SUBS_PATH)


def get_job_status() -> dict:
    return _job_status


def _set_job_status(job: str, status: str, msg: str = ""):
    _job_status[job] = {
        "status": status,
        "message": msg,
        "updated": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseCrawlerJob(ABC):
    """Template method for crawler jobs.

    Subclasses override _create_crawler (required), _skip_reason, and
    _post_run to specialize behavior.
    """

    name: str = ""

    def run(self) -> None:
        """Execute the crawl job: fetch papers, filter via AI, store results.

        Two-phase design:
        1. Collect all papers from crawler (sequential — arXiv API rate-limited)
        2. Process with AI in parallel using ThreadPoolExecutor
        """
        logger.info(f"[{self.name}] ▶ 开始")
        try:
            subs = _load_subs()
            crawler = self._create_crawler(subs)
            if crawler is None:
                reason = self._skip_reason(subs)
                logger.info(f"[{self.name}] ⊘ 跳过: {reason}")
                _set_job_status(self.name, "skipped", reason)
                return

            # Phase 1: Collect all papers (sequential — crawler is rate-limited)
            all_papers = list(crawler.crawl_iter())
            fetched = len(all_papers)
            logger.info(f"[{self.name}] 爬取完成, {fetched} 篇待处理, 并行处理 (workers={_ai_max_workers})")

            # Phase 2: Parallel AI processing
            written = 0
            skipped = {"exists": 0, "ignored": 0, "filter_reject": 0, "ai_reject": 0, "error": 0}
            fetched_info = self._init_fetched_info()
            lock = threading.Lock()
            done_count = [0]
            start_time = time.monotonic()

            def _process_one(paper):
                nonlocal written
                self._track_fetched(fetched_info, paper)
                result = append_paper(paper, enhance=True)
                with lock:
                    done_count[0] += 1
                    if result == "written":
                        written += 1
                    else:
                        skipped[result] = skipped.get(result, 0) + 1
                    n = done_count[0]
                    if n % 20 == 0 or n == fetched:
                        elapsed = time.monotonic() - start_time
                        speed = n / elapsed if elapsed > 0 else 0
                        eta = (fetched - n) / speed if speed > 0 else 0
                        parts = [f"{written} 接受"]
                        if skipped.get("filter_reject"):
                            parts.append(f"{skipped['filter_reject']} 过滤")
                        if skipped.get("exists"):
                            parts.append(f"{skipped['exists']} 重复")
                        ignored_total = sum(v for k, v in skipped.items() if k not in ("exists",))
                        if ignored_total:
                            parts.append(f"{ignored_total} 拒绝")
                        logger.info(
                            f"[{self.name}] {n}/{fetched} ({speed:.1f}/s, ETA {eta:.0f}s) │ {' │ '.join(parts)}"
                        )
                return result

            with ThreadPoolExecutor(max_workers=_ai_max_workers) as executor:
                futures = {executor.submit(_process_one, p): p for p in all_papers}
                for future in as_completed(futures):
                    if _shutdown:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    try:
                        future.result()
                    except Exception as e:
                        p = futures[future]
                        with lock:
                            skipped["error"] = skipped.get("error", 0) + 1
                        logger.warning(f"[{self.name}] 处理异常 {getattr(p, 'id', '?')}: {e}")

            self._post_run(subs, fetched_info)
            total_rejected = fetched - written
            msg = f"{written} 接受, {total_rejected} 拒绝 (共 {fetched})"
            logger.info(f"[{self.name}] ✔ 完成: {msg}")
            _set_job_status(self.name, "done", msg)
        except Exception as e:
            logger.error(f"[{self.name}] ✖ 失败: {e}", exc_info=True)
            _set_job_status(self.name, "error", str(e))

    @abstractmethod
    def _create_crawler(self, subs: Subscriptions):
        """Return a crawler instance, or None to skip this run."""

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no config"

    def _init_fetched_info(self) -> dict:
        """Initialize tracking info for the crawl loop."""
        return {}

    def _track_fetched(self, info: dict, paper) -> None:
        """Track per-paper info during the crawl loop (e.g. fetched venues)."""

    def _post_run(self, subs: Subscriptions, fetched_info: dict) -> None:
        """Post-crawl bookkeeping (e.g. update last_updated timestamps)."""


# ---------------------------------------------------------------------------
# Concrete jobs
# ---------------------------------------------------------------------------

class ArxivJob(BaseCrawlerJob):
    name = "arxiv"

    def _create_crawler(self, subs: Subscriptions):
        """Build ArxivCrawler with categories and all known/ignored IDs excluded."""
        if not subs.arxiv_categories:
            return None
        conn = get_conn()
        rows = conn.execute(
            "SELECT id FROM papers WHERE source='arxiv'"
        ).fetchall()
        existing_ids = {row["id"] for row in rows}
        # Exclude previously filtered papers to avoid re-processing
        ignored_rows = conn.execute("SELECT paper_id FROM ignored_papers").fetchall()
        existing_ids |= {row["paper_id"] for row in ignored_rows}
        return ArxivCrawler(
            categories=subs.arxiv_categories, existing_ids=existing_ids
        )

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no categories"


class CrossrefJob(BaseCrawlerJob):
    name = "crossref"

    def _create_crawler(self, subs: Subscriptions):
        if not subs.crossref_journals:
            return None
        return CrossrefCrawler(journals=subs.crossref_journals)

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no journals"

    def _init_fetched_info(self) -> dict:
        """Initialize per-job tracking state for fetched papers."""
        return {"journals": set()}

    def _track_fetched(self, info: dict, paper) -> None:
        if paper.journal_title:
            info["journals"].add(paper.journal_title)

    def _post_run(self, subs: Subscriptions, fetched_info: dict) -> None:
        """Update last_updated timestamp for journals that had papers fetched."""
        fetched_journals = fetched_info.get("journals", set())
        if fetched_journals:
            now = datetime.now(timezone.utc).isoformat()
            for j in subs.crossref_journals:
                if j.name in fetched_journals:
                    j.last_updated = now
            _save_subs(subs)


class DblpJob(BaseCrawlerJob):
    name = "dblp"

    def _create_crawler(self, subs: Subscriptions):
        if not subs.conferences:
            return None
        return DblpCrawler(conferences=subs.conferences)

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no conferences"

    def _init_fetched_info(self) -> dict:
        return {"venues": set()}

    def _track_fetched(self, info: dict, paper) -> None:
        info["venues"].add(paper.venue)

    def _post_run(self, subs: Subscriptions, fetched_info: dict) -> None:
        fetched_venues = fetched_info.get("venues", set())
        if fetched_venues:
            now = datetime.now(timezone.utc).isoformat()
            for c in subs.conferences:
                if any(c.venue in v for v in fetched_venues):
                    c.last_updated = now
            _save_subs(subs)


class S2Job(BaseCrawlerJob):
    """Now backed by OpenAlex instead of Semantic Scholar."""
    name = "s2"

    def _create_crawler(self, subs: Subscriptions):
        """Expand seed keywords via LLM, then search via OpenAlex."""
        profile = load_research_profile()
        seed_keywords = subs.search_keywords or profile.get("keywords", [])
        if not seed_keywords:
            return None
        try:
            keywords = expand_keywords(
                direction=profile.get("direction", ""),
                seed_keywords=seed_keywords,
                quality_criteria=profile.get("quality_criteria", ""),
                liked=profile.get("liked_topics", []),
                disliked=profile.get("disliked_topics", []),
            )
        except Exception as e:
            logger.warning(f"关键词扩展失败，使用原始关键词: {e}")
            keywords = seed_keywords
        return OpenAlexCrawler(keywords=keywords, max_per_keyword=10)

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no keywords"


class AuthorJob(BaseCrawlerJob):
    name = "author"

    def _create_crawler(self, subs: Subscriptions):
        if not subs.authors:
            return None
        author_dicts = [
            {"authorId": a.author_id, "name": a.name}
            for a in subs.authors
        ]
        return AuthorCrawler(authors=author_dicts, papers_per_author=50)

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no authors"

    def _post_run(self, subs: Subscriptions, fetched_info: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for a in subs.authors:
            a.last_updated = now
        _save_subs(subs)


# ---------------------------------------------------------------------------
# Job registry
# ---------------------------------------------------------------------------

JOBS: dict[str, BaseCrawlerJob] = {
    "arxiv": ArxivJob(),
    "crossref": CrossrefJob(),
    "dblp": DblpJob(),
    "s2": S2Job(),
    "author": AuthorJob(),
}


# ---------------------------------------------------------------------------
# Backward-compatible top-level functions (used by api.py)
# ---------------------------------------------------------------------------

def run_arxiv_job():
    JOBS["arxiv"].run()


def run_crossref_job():
    JOBS["crossref"].run()


def run_dblp_job():
    JOBS["dblp"].run()


def run_s2_job():
    JOBS["s2"].run()


def run_author_job():
    JOBS["author"].run()


# ---------------------------------------------------------------------------
# Retro-enhance (SQLite-based)
# ---------------------------------------------------------------------------

def run_retro_enhance():
    """Enhance papers that have no AI results yet."""
    logger.info("[retro-enhance] ▶ 开始")
    try:
        chain, profile = get_ai_chain()

        conn = get_conn()
        paper_cols = ", ".join(f"p.{c}" for c in [
            "id", "source", "title", "summary",
            "authors", "categories",
            "doi", "published_date", "url", "pdf",
            "publisher", "journal_title", "issn",
            "comment", "article_type",
            "venue", "acceptance", "citation_count", "version",
        ])
        sql = (
            f"SELECT {paper_cols} "
            f"FROM papers p LEFT JOIN ai_results ai ON p.id = ai.paper_id "
            f"WHERE ai.paper_id IS NULL AND (p.summary != '' OR p.title != '')"
        )
        rows = conn.execute(sql).fetchall()

        if not rows:
            logger.info("[retro-enhance] ⊘ 无需增强的论文")
            return

        # Convert rows to dicts, decoding JSON fields
        json_fields = {"authors", "categories", "issn"}
        to_enhance: list[dict] = []
        for row in rows:
            d = {}
            for key in row.keys():
                val = row[key]
                if key in json_fields and val is not None:
                    try:
                        val = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        pass
                d[key] = val
            to_enhance.append(d)

        logger.info(f"[retro-enhance] {len(to_enhance)} 篇待增强")
        enhanced_count = 0

        with ThreadPoolExecutor(max_workers=_ai_max_workers) as executor:
            futures = {
                executor.submit(enhance_single, p, chain, profile, AI_LANGUAGE): p
                for p in to_enhance
            }
            for future in as_completed(futures):
                if _shutdown:
                    break
                p = futures[future]
                try:
                    result = future.result()
                    if result:
                        ai_data = result.get("AI", result)
                        _insert_ai_row(p["id"], ai_data)
                        enhanced_count += 1
                except Exception as e:
                    logger.warning(
                        f"[retro-enhance] 失败 {p.get('id', '?')}: {e}"
                    )
                if enhanced_count % 10 == 0:
                    logger.info(
                        f"[retro-enhance] {enhanced_count}/{len(to_enhance)}"
                    )

        logger.info(f"[retro-enhance] ✔ 完成: {enhanced_count} 篇已增强")
    except Exception as e:
        logger.error(f"[retro-enhance] ✖ 失败: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Digest job (unchanged — digest.py will be updated separately)
# ---------------------------------------------------------------------------

def run_digest_job():
    logger.info("[digest] ▶ 开始")
    try:
        path = generate_digest()
        if path:
            logger.info(f"[digest] ✔ 已保存: {path}")
        else:
            logger.info("[digest] ⊘ 今日无新论文")
    except Exception as e:
        logger.error(f"[digest] ✖ 失败: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Scheduler (unchanged logic, same timers)
# ---------------------------------------------------------------------------

JOB_FUNCS = {
    "arxiv": run_arxiv_job,
    "crossref": run_crossref_job,
    "dblp": run_dblp_job,
    "s2": run_s2_job,
    "author": run_author_job,
}


class Scheduler:
    """Periodic job scheduler using threading.Timer.

    Runs arxiv every 3 hours, other sources every 24 hours.
    After each arxiv run, triggers retro-enhance and digest generation.
    """

    def __init__(self):
        self._timers: list[threading.Timer] = []
        self._running = False

    def start(self):
        self._running = True
        self._run_and_reschedule("arxiv", interval_hours=3)
        self._run_and_reschedule("crossref", interval_hours=24)
        self._run_and_reschedule("dblp", interval_hours=24)
        self._run_and_reschedule("s2", interval_hours=24)
        self._run_and_reschedule("author", interval_hours=24)

    def stop(self):
        self._running = False
        for t in self._timers:
            t.cancel()
        logger.info("[调度器] 已停止")

    def _run_and_reschedule(self, job_name: str, interval_hours: int):
        """Execute a job and schedule its next run. After arxiv, also runs retro-enhance and digest."""
        if not self._running:
            return
        try:
            JOB_FUNCS[job_name]()
        except Exception as e:
            logger.error(f"定时任务 {job_name} 执行错误: {e}")

        if job_name == "arxiv":
            try:
                run_retro_enhance()
            except Exception as e:
                logger.error(f"回溯增强执行错误: {e}")
            try:
                from api import _retro_knowledge_extract
                _retro_knowledge_extract()
            except Exception as e:
                logger.error(f"知识卡片抽取执行错误: {e}")
            try:
                from api import _retro_fulltext_analyze
                _retro_fulltext_analyze()
            except Exception as e:
                logger.error(f"正文分析执行错误: {e}")
            try:
                run_digest_job()
            except Exception as e:
                logger.error(f"摘要生成执行错误: {e}")

        if self._running:
            t = threading.Timer(
                interval_hours * 3600,
                self._run_and_reschedule,
                args=[job_name, interval_hours],
            )
            t.daemon = True
            t.start()
            self._timers.append(t)
