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
from datetime import datetime, timedelta, timezone

from backend.ai.digest import generate_digest
from backend.ai.enhance import enhance_single, load_research_profile
from backend.ai.keyword_expander import expand_keywords
from backend.crawler.arxiv_crawler import ArxivCrawler
from backend.crawler.author_crawler import AuthorCrawler
from backend.crawler.citation_crawler import CitationCrawler
from backend.crawler.crossref_crawler import CrossrefCrawler
from backend.crawler.dblp_crawler import DblpCrawler
from backend.crawler.openalex_crawler import OpenAlexCrawler
from backend.crawler.subs_store import Subscriptions

from backend.db import get_conn
from backend.paper_store import (
    AI_LANGUAGE,
    append_paper,
    get_ai_chain,
    _insert_ai_row,
)

logger = logging.getLogger("jobs")

_job_status: dict[str, dict] = {}
def _ai_workers() -> int:
    from backend.db import get_runtime_settings
    try:
        return int(get_runtime_settings().get("AI_MAX_WORKERS", os.environ.get("AI_MAX_WORKERS", "5")))
    except Exception:
        return 5
_ai_max_workers = _ai_workers()
_shutdown = False


def request_shutdown() -> None:
    """Flag background AI loops to stop early (called on SIGINT/SIGTERM)."""
    global _shutdown
    _shutdown = True

SUBS_PATH = "subscriptions.json"

# 并发任务（手动"全部爬取"）同时收尾时保护 subscriptions.json 的读-改-写
_subs_lock = threading.Lock()
_scheduled_at: dict[str, str] = {}   # 任务 → 下次计划运行时间（前端展示）
_scheduler_instance = None            # 供设置变更后 replan


def get_scheduled_at() -> dict:
    return dict(_scheduled_at)


def replan_scheduler():
    if _scheduler_instance is not None:
        _scheduler_instance.replan()


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
        _set_job_status(self.name, "running")
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
            try:
                from backend.crawler.openalex_client import quota_paused
                if quota_paused():
                    msg += " ⚠️OpenAlex限流暂停中(≤10分钟)，稍后手动重试"
            except Exception:
                pass
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
        """Build ArxivCrawler with categories and all known/ignored IDs excluded.

        Tracks the last successful run in the KV table; if the daemon was down
        for >= 2 days, enables submittedDate backfill so missed days are
        re-fetched instead of lost forever."""
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

        backfill_since = None
        kv = conn.execute(
            "SELECT value FROM subscriptions WHERE key = 'arxiv_last_success'"
        ).fetchone()
        if kv:
            try:
                from datetime import date
                last = date.fromisoformat(kv["value"][:10])
                gap = (date.today() - last).days
                if gap >= 2:
                    backfill_since = kv["value"][:10]
                    logger.info(f"[arxiv] 检测到断档 {gap} 天，启用回补（自 {backfill_since}）")
            except ValueError:
                pass

        return ArxivCrawler(
            categories=subs.arxiv_categories,
            existing_ids=existing_ids,
            backfill_since=backfill_since,
        )

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no categories"

    def _post_run(self, subs: Subscriptions, fetched_info: dict) -> None:
        from datetime import date
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO subscriptions (key, value) VALUES ('arxiv_last_success', ?)",
            (date.today().isoformat(),),
        )


class CrossrefJob(BaseCrawlerJob):
    name = "crossref"

    def _create_crawler(self, subs: Subscriptions):
        if not subs.crossref_journals:
            return None
        conn = get_conn()
        known = {r["id"] for r in conn.execute("SELECT id FROM papers")}
        known |= {r["paper_id"] for r in conn.execute("SELECT paper_id FROM ignored_papers")}
        return CrossrefCrawler(journals=subs.crossref_journals, known_ids=known)

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no journals"

    def _init_fetched_info(self) -> dict:
        """Initialize per-job tracking state for fetched papers."""
        return {"journals": set()}

    def _track_fetched(self, info: dict, paper) -> None:
        if paper.journal_title:
            info["journals"].add(paper.journal_title)

    def _post_run(self, subs: Subscriptions, fetched_info: dict) -> None:
        """Update last_updated timestamps for journals that had papers fetched."""
        fetched_journals = fetched_info.get("journals", set())
        if not fetched_journals:
            return
        with _subs_lock:
            fresh = _load_subs()  # 重读，避免覆盖其他并发任务刚写入的更新
            now = datetime.now(timezone.utc).isoformat()
            for j in fresh.crossref_journals:
                if j.name in fetched_journals:
                    j.last_updated = now
            _save_subs(fresh)


class DblpJob(BaseCrawlerJob):
    name = "dblp"

    def _create_crawler(self, subs: Subscriptions):
        if not subs.conferences:
            return None
        from backend.db import get_runtime_settings
        return DblpCrawler(
            conferences=subs.conferences,
            rotate_days=int(get_runtime_settings()["DBLP_ROTATE_DAYS"]),
        )

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no conferences"

    def _init_fetched_info(self) -> dict:
        return {"venues": set()}

    def _track_fetched(self, info: dict, paper) -> None:
        info["venues"].add(paper.venue)

    def _post_run(self, subs: Subscriptions, fetched_info: dict) -> None:
        fetched_venues = fetched_info.get("venues", set())
        if not fetched_venues:
            return
        with _subs_lock:
            fresh = _load_subs()
            now = datetime.now(timezone.utc).isoformat()
            for c in fresh.conferences:
                if any(c.venue in v for v in fetched_venues):
                    c.last_updated = now
            _save_subs(fresh)


class S2Job(BaseCrawlerJob):
    """Now backed by OpenAlex instead of Semantic Scholar."""
    name = "s2"

    def _create_crawler(self, subs: Subscriptions):
        """Expand seed keywords via LLM, then search via OpenAlex."""
        profile = load_research_profile()
        user_keywords = subs.search_keywords or []
        # When use_profile_keywords is True, search_keywords already contains
        # the user's selected subset of profile keywords — don't re-add all of them.
        # When False, user set custom keywords — still merge profile keywords.
        if subs.use_profile_keywords:
            seed_keywords = list(dict.fromkeys(user_keywords))  # deduplicate, preserve order
        else:
            profile_keywords = profile.get("keywords", [])
            seen = set()
            seed_keywords = []
            for kw in user_keywords + profile_keywords:
                kl = kw.lower()
                if kl not in seen:
                    seen.add(kl)
                    seed_keywords.append(kw)
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
        from backend.db import get_runtime_settings
        return OpenAlexCrawler(
            keywords=keywords, max_per_keyword=20,
            rotate_days=int(get_runtime_settings()["S2_ROTATE_DAYS"]),
        )

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
        with _subs_lock:
            fresh = _load_subs()
            now = datetime.now(timezone.utc).isoformat()
            for a in fresh.authors:
                a.last_updated = now
            _save_subs(fresh)


class CitationJob(BaseCrawlerJob):
    """Citation-following discovery: expand must-read/liked anchors via OpenAlex."""
    name = "citations"

    def _create_crawler(self, subs: Subscriptions):
        if os.environ.get("CITATION_ENABLED", "on").strip().lower() in ("off", "0", "false"):
            return None
        limit = int(os.environ.get("CITATION_ANCHORS_PER_RUN", "10"))
        conn = get_conn()
        rows = conn.execute("""
            SELECT p.id, p.doi, p.title FROM papers p
            LEFT JOIN feedback f ON f.paper_id = p.id
            WHERE p.doi IS NOT NULL AND p.doi != ''
              AND (
                EXISTS (SELECT 1 FROM ai_results a WHERE a.paper_id = p.id AND a.recommendation = 'must-read')
                OR f.rating = 'like'
              )
            ORDER BY p.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        anchors = [dict(r) for r in rows]
        if not anchors:
            return None
        logger.info(f"[citations] 本轮锚点 {len(anchors)} 篇（must-read ∪ 用户点赞，含 DOI）")
        return CitationCrawler(
            anchors=anchors,
            max_per_anchor=int(os.environ.get("CITATION_MAX_PER_ANCHOR", "15")),
        )

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "disabled or no must-read/liked anchors with DOI"


# ---------------------------------------------------------------------------
# Job registry
# ---------------------------------------------------------------------------

JOBS: dict[str, BaseCrawlerJob] = {
    "arxiv": ArxivJob(),
    "crossref": CrossrefJob(),
    "dblp": DblpJob(),
    "s2": S2Job(),
    "author": AuthorJob(),
    "citations": CitationJob(),
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


def run_citations_job():
    JOBS["citations"].run()


def run_trend_auto(today=None):
    """Trend 滚动更新：每晚刷新当期周报+月报（趋势页永远新鲜，
    周期切换时的最后一次刷新自然成为历史存档）；
    每月 1 日额外归档上月完整月报（带上界，防跨期污染）。
    today 参数仅为可测试性。"""
    from datetime import date as _date, timedelta as _td
    today = today or _date.today()
    from backend.ai.trend_analyzer import generate_trend_report_period
    _set_job_status("trend_auto", "running")
    done = []
    try:
        r = generate_trend_report_period("weekly")
        done.append(f"周报{r['week_start'][:10]}({r['paper_count']}篇)" if r else "周报: 本周无论文")
        r = generate_trend_report_period("monthly")
        done.append(f"月报{r['week_start']}({r['paper_count']}篇)" if r else "月报: 本月无论文")
        if today.day == 1:
            prev_month_key = (today.replace(day=1) - _td(days=1)).strftime("%Y-%m")
            month_start = today.strftime("%Y-%m-%d")
            r = generate_trend_report_period("monthly", prev_month_key, window_end=month_start)
            done.append(f"归档{r['week_start']}({r['paper_count']}篇)" if r else f"归档{prev_month_key}: 无论文")
        _set_job_status("trend_auto", "done", ", ".join(done))
        logger.info(f"[trend_auto] ✔ {', '.join(done)}")
    except Exception as e:
        logger.error(f"[trend_auto] ✖ 失败: {e}", exc_info=True)
        _set_job_status("trend_auto", "error", str(e)[:120])


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
                    if result and result.get("AI", {}).get("_llm_failed"):
                        continue  # LLM 故障：不写 ignore 结果，下轮重试
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
# Scheduler
# ---------------------------------------------------------------------------

JOB_FUNCS = {
    "arxiv": run_arxiv_job,
    "crossref": run_crossref_job,
    "dblp": run_dblp_job,
    "s2": run_s2_job,
    "author": run_author_job,
    "citations": run_citations_job,
    "trend_auto": run_trend_auto,
}


class Scheduler:
    """Nightly job scheduler.

    Automatic runs happen only in the early-morning window starting at
    NIGHT_START (default 02:00), with jobs spread STAGGER_MINUTES apart
    (default 30) so the long arxiv analysis chain and the OpenAlex-heavy
    DBLP/S2 crawls never collide. Manual triggers via /api/trigger/* bypass
    the scheduler entirely and run immediately at any time (their OpenAlex
    calls are still globally throttled by crawler.openalex_client).

    Set RUN_ON_START=1 to run the full pipeline once immediately on daemon
    start (old behavior).
    """

    def __init__(self):
        self._timers: list[threading.Timer] = []
        self._running = False
        global _scheduler_instance
        _scheduler_instance = self

    def start(self):
        from backend.db import get_runtime_settings
        self._running = True
        if get_runtime_settings()["RUN_ON_START"]:
            logger.info("[调度器] RUN_ON_START=1，启动时立即执行全部任务（此后仍按凌晨计划）")
            for job_name in JOB_FUNCS:
                self._run_and_schedule_next(job_name)
        else:
            for job_name in JOB_FUNCS:
                self._schedule_next(job_name)

    def stop(self):
        self._running = False
        for t in self._timers:
            t.cancel()
        logger.info("[调度器] 已停止")

    def _next_run_at(self, job_name: str) -> datetime:
        """Next nightly run time: NIGHT_START + job_index × STAGGER_MINUTES,
        today if still ahead, otherwise tomorrow. 设置动态读取——前端改动即时生效。"""
        from backend.db import get_runtime_settings
        s = get_runtime_settings()
        now = datetime.now()
        order = list(JOB_FUNCS)
        offset = order.index(job_name) * float(s["STAGGER_MINUTES"])
        base = now.replace(hour=int(s["NIGHT_START"]), minute=0, second=0, microsecond=0)
        target = base + timedelta(minutes=offset)
        if target <= now:
            target += timedelta(days=1)
        return target

    def _schedule_next(self, job_name: str):
        if not self._running:
            return
        target = self._next_run_at(job_name)
        delay = max(1.0, (target - datetime.now()).total_seconds())
        t = threading.Timer(delay, self._run_and_schedule_next, args=[job_name])
        t.daemon = True
        t.start()
        self._timers.append(t)
        _scheduled_at[job_name] = target.strftime("%Y-%m-%d %H:%M")
        logger.info(f"[调度器] {job_name} 计划于 {target:%Y-%m-%d %H:%M} 自动运行（手动触发不受限，随时可跑）")

    def replan(self):
        """设置变更后重排时间表：取消现有定时器（运行中任务除外，其完成时自会重排）。"""
        if not self._running:
            return
        for t in self._timers:
            t.cancel()
        self._timers.clear()
        running = {n for n, s in _job_status.items() if s.get("status") == "running"}
        for job_name in JOB_FUNCS:
            if job_name not in running:
                self._schedule_next(job_name)
        logger.info(f"[调度器] 已按新设置重排时间表（{len(JOB_FUNCS) - len(running)} 个任务，运行中 {len(running)} 个不变）")

    def _run_and_schedule_next(self, job_name: str):
        """Execute a job (with arxiv's chained analysis pipeline), then
        schedule tomorrow night's run.

        互斥保护：若上一夜间任务仍在运行（爬虫卡在重试等情况），
        推迟 15 分钟而不是并发叠加——昨晚 DBLP/S2/引文三任务叠着打
        OpenAlex 直接触发了日级限流。手动触发不受此限制。
        """
        if not self._running:
            return
        busy = [n for n, s in _job_status.items()
                if n != job_name and s.get("status") == "running"]
        if busy:
            logger.info(f"[调度器] {busy} 仍在运行，{job_name} 推迟 15 分钟再试（避免并发挤兑 OpenAlex）")
            t = threading.Timer(15 * 60, self._run_and_schedule_next, args=[job_name])
            t.daemon = True
            t.start()
            self._timers.append(t)
            return

        try:
            JOB_FUNCS[job_name]()
        except Exception as e:
            logger.error(f"夜间任务 {job_name} 执行错误: {e}")

        if job_name == "arxiv":
            try:
                run_retro_enhance()
            except Exception as e:
                logger.error(f"回溯增强执行错误: {e}")
            try:
                from backend.api import _retro_knowledge_extract
                _retro_knowledge_extract()
            except Exception as e:
                logger.error(f"知识卡片抽取执行错误: {e}")
            try:
                from backend.api import _retro_fulltext_analyze
                _retro_fulltext_analyze()
            except Exception as e:
                logger.error(f"正文分析执行错误: {e}")
            try:
                run_digest_job()
            except Exception as e:
                logger.error(f"摘要生成执行错误: {e}")

        self._schedule_next(job_name)
