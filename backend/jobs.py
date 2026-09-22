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
import queue
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

from backend.db import get_conn, sync_write
from backend.paper_store import (
    AI_LANGUAGE,
    append_paper,
    get_ai_chain,
    _insert_ai_row,
    _insert_knowledge_card,
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


def _set_job_status(job: str, status: str, msg: str = "", progress: dict | None = None):
    """progress 可选结构化进度：{done, total, speed_pmin, eta_min}——
    前端 ⚡ 任务中心画进度条用；消息文本保持人类可读。"""
    entry = {
        "status": status,
        "message": msg,
        "updated": datetime.now(timezone.utc).isoformat(),
    }
    if progress:
        entry["progress"] = progress
    _job_status[job] = entry


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

            # 流水线：抓取生产者与 AI 消费者并行——边抓边分析，不再等全部抓完
            # （背压队列 maxsize=50：抓取过快时生产者自然等待，内存有界）
            paper_q: "queue.Queue" = queue.Queue(maxsize=50)
            fetched_box = [0]      # 已被工作线程取走（处理中/已处理）
            yielded_box = [0]      # 爬虫已产出（含队列中未取走的）
            producer_done = threading.Event()
            written = 0
            skipped = {"exists": 0, "ignored": 0, "filter_reject": 0, "ai_reject": 0, "error": 0}
            fetched_info = self._init_fetched_info()
            lock = threading.Lock()
            done_count = [0]
            last_log_t = [time.monotonic()]
            samples = [(time.monotonic(), 0)]  # (t, n) 采样，近 3 分钟窗口算即时速度
            start_time = time.monotonic()

            def _produce():
                try:
                    for paper in crawler.crawl_iter():
                        paper_q.put(paper)
                        yielded_box[0] += 1
                except Exception as e:
                    logger.error(f"[{self.name}] 爬取阶段异常（已抓取部分继续处理）: {e}", exc_info=True)
                finally:
                    producer_done.set()
                    logger.info(f"[{self.name}] 抓取完成, 共产出 {yielded_box[0]} 篇（处理 {fetched_box[0]}）")
                    for _ in range(_ai_max_workers):
                        paper_q.put(None)

            def _track(paper):
                self._track_fetched(fetched_info, paper)
                with lock:
                    fetched_box[0] += 1

            def _process_one(paper):
                nonlocal written
                result = append_paper(paper, enhance=True)
                with lock:
                    done_count[0] += 1
                    if result == "written":
                        written += 1
                    else:
                        skipped[result] = skipped.get(result, 0) + 1
                    n = done_count[0]
                    # 每 10 篇一条 + 至少间隔 3s 节流；速度用近 3 分钟窗口（全程均值
                    # 会被早期慢段带偏）；进度同步任务状态，🔄 菜单实时可见
                    now = time.monotonic()
                    fetched_now = max(fetched_box[0], yielded_box[0])
                    is_final = producer_done.is_set() and n == fetched_box[0] and paper_q.empty()
                    if (n % 10 == 0 or is_final) and (now - last_log_t[0] >= 3 or is_final):
                        last_log_t[0] = now
                        samples.append((now, n))
                        while len(samples) > 2 and samples[1][0] < now - 180:
                            samples.pop(0)
                        if len(samples) >= 2 and now - samples[0][0] >= 5:
                            dt = now - samples[0][0]
                            recent = (n - samples[0][1]) / dt  # 篇/秒（近窗口）
                        else:
                            recent = n / max(0.001, now - start_time)
                        eta = (fetched_now - n) / recent if recent > 0 else 0
                        elapsed = now - start_time
                        parts = [f"{written} 接受"]
                        if skipped.get("filter_reject"):
                            parts.append(f"{skipped['filter_reject']} 过滤")
                        if skipped.get("exists"):
                            parts.append(f"{skipped['exists']} 重复")
                        ignored_total = sum(v for k, v in skipped.items() if k not in ("exists",))
                        if ignored_total:
                            parts.append(f"{ignored_total} 拒绝")
                        # 手动多任务并行时共享 GLM 限流器，各任务速度减半——提示出来
                        _snap = dict(get_job_status())
                        others = [k for k, v in _snap.items()
                                  if k != self.name and isinstance(v, dict) and v.get("status") == "running"]
                        if others:
                            parts.append(f"与 {','.join(others)} 并行抢LLM限额")
                        if producer_done.is_set() and fetched_now:
                            prog = (f"{n}/{fetched_now} · {recent * 60:.1f}篇/分 · ETA {eta / 60:.0f}分"
                                    f" · 已用 {int(elapsed // 60)}:{int(elapsed % 60):02d}")
                        else:
                            prog = f"已处理 {n}（抓取中，已得 {fetched_now} 篇）"
                        logger.info(f"[{self.name}] {prog} │ {' │ '.join(parts)}")
                        prog_obj = {"done": n, "speed_pmin": round(recent * 60, 1)}
                        if producer_done.is_set() and fetched_now:
                            prog_obj.update({"total": fetched_now, "eta_min": round(eta / 60)})
                        _set_job_status(self.name, "running", f"{prog} │ {' │ '.join(parts)}", progress=prog_obj)
                return result

            def _worker():
                while not _shutdown:
                    paper = paper_q.get()
                    try:
                        if paper is None:
                            return
                        _track(paper)
                        try:
                            _process_one(paper)
                        except Exception as e:
                            with lock:
                                skipped["error"] = skipped.get("error", 0) + 1
                            logger.warning(f"[{self.name}] 处理异常 {getattr(paper, 'id', '?')}: {e}")
                    finally:
                        paper_q.task_done()

            logger.info(f"[{self.name}] ▶ 开始（流水线：边抓边分析, workers={_ai_max_workers}）")
            producer = threading.Thread(target=_produce, daemon=True, name=f"{self.name}-crawl")
            producer.start()
            workers = [threading.Thread(target=_worker, daemon=True, name=f"{self.name}-ai-{i}")
                       for i in range(_ai_max_workers)]
            for t in workers:
                t.start()
            for t in workers:
                t.join()
            if _shutdown:
                logger.info(f"[{self.name}] ⊘ 收到停机信号，提前结束")
                return

            # error>0（LLM 故障等未落库未拉黑）时不推进 last_updated——
            # 否则 arxiv /new 窗口翻篇，失败论文从源头永久丢失（审计 P1）
            if skipped.get("error"):
                logger.warning(f"[{self.name}] {skipped['error']} 篇处理失败，"
                               f"不推进抓取水位（下轮重抓）")
            else:
                self._post_run(subs, fetched_info)
            fetched = fetched_box[0]  # join 后所有论文都已被取走，此即总数
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
    # 期刊渐进回溯（如已设定 BACKFILL_MONTHS）
    try:
        run_backfill_nightly()
    except Exception as e:
        logger.warning(f"夜间回溯跳过: {e}")
    # 抓取批完成后渐进收敛旧版本
    try:
        run_auto_convergence()
    except Exception as e:
        logger.warning(f"自动收敛跳过: {e}")


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
            _set_job_status("enhance", "done", "无需增强的论文")
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
        _set_job_status("enhance", "running", f"{len(to_enhance)} 篇待增强",
                        progress={"done": 0, "total": len(to_enhance)})
        enhanced_count = 0
        _re_done = [0]

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
                _re_done[0] += 1
                if _re_done[0] % 10 == 0 or _re_done[0] == len(to_enhance):
                    logger.info(
                        f"[retro-enhance] {_re_done[0]}/{len(to_enhance)}"
                    )
                    _set_job_status("enhance", "running", f"{_re_done[0]}/{len(to_enhance)}（成功 {enhanced_count}）",
                                    progress={"done": _re_done[0], "total": len(to_enhance)})

        logger.info(f"[retro-enhance] ✔ 完成: {enhanced_count} 篇已增强")
        _set_job_status("enhance", "done", f"{enhanced_count}/{len(to_enhance)} 篇已增强")
    except Exception as e:
        logger.error(f"[retro-enhance] ✖ 失败: {e}", exc_info=True)
        _set_job_status("enhance", "error", str(e)[:160])


# ---------------------------------------------------------------------------
# Digest job (unchanged — digest.py will be updated separately)
# ---------------------------------------------------------------------------

_RERUN_LOCK_PATH = "data/.rerun.lock"  # 测试可指向临时文件


def run_journal_backfill(months: int = 6, nightly: int = 0):
    """期刊历史回溯（渐进式）：设定目标月数后每晚自动推进。

    手动触发（nightly=0）：一次性跑完（原行为，不推荐大量期刊）。
    渐进模式（nightly>0）：只处理 nightly 本期刊，剩余留待后续夜间调度。
    进度存储在 KV（backfill_progress），⚡ 任务中心可见。
    """
    import fcntl
    from pathlib import Path as _P
    _P("data").mkdir(exist_ok=True)
    lock_fh = open("data/.backfill.lock", "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        _set_job_status("journal_backfill", "error", "另一实例正在回溯")
        lock_fh.close()
        return
    try:
        from datetime import datetime as _dt, timedelta as _td
        from backend.db import get_runtime_settings, get_conn as _gc
        from backend.crawler.crossref_crawler import CrossrefCrawler

        subs = _load_subs()
        journals = subs.crossref_journals or []
        if not journals:
            _set_job_status("journal_backfill", "done", "无订阅期刊")
            return

        # 读取或初始化进度
        conn = _gc()
        prog_row = conn.execute(
            "SELECT value FROM subscriptions WHERE key='backfill_progress'").fetchone()
        import json as _j
        prog = _j.loads(prog_row[0]) if prog_row else {"cursor": 0, "months": months, "done": 0}
        if prog.get("months") != months:
            prog = {"cursor": 0, "months": months, "done": 0}  # 目标变了→重置
        cursor = int(prog.get("cursor", 0))
        if cursor >= len(journals):
            _set_job_status("journal_backfill", "done",
                            f"回溯完成: {len(journals)} 本期刊 × {months} 个月 ✓")
            return

        from_date = (_dt.now() - _td(days=months * 30)).strftime("%Y-%m-%d")
        batch = journals[cursor:cursor + nightly] if nightly > 0 else journals[cursor:]
        batch_label = f"期刊 {cursor + 1}-{min(cursor + len(batch), len(journals))}/{len(journals)}"
        _set_job_status("journal_backfill", "running",
                        f"{batch_label} × {months} 个月（{from_date} 起）")
        logger.info(f"[backfill] ▶ {batch_label} × {months} 个月")

        known = {r[0] for r in conn.execute("SELECT id FROM papers")}
        ignored = {r[0] for r in conn.execute("SELECT paper_id FROM ignored_papers")}
        crawler = CrossrefCrawler(journals, known_ids=known | ignored)

        # 流水线：生产者（逐期刊回溯）→ AI worker
        paper_q = queue.Queue(maxsize=50)
        producer_done = threading.Event()
        done_count = [0]
        new_count = [0]
        lock = threading.Lock()
        last_log = [time.monotonic()]

        def _produce():
            try:
                for j in batch:
                    if _shutdown:
                        break
                    items = crawler._fetch_backfill(j.issn, from_date, max_rows=500)
                    logger.info(f"[backfill] {j.name}: {len(items)} 篇")
                    for item in items:
                        paper = crawler._parse_item(item, j)
                        if paper and paper.article_type == "research":
                            paper_q.put(paper)
            except Exception as e:
                logger.error(f"[backfill] 抓取异常: {e}", exc_info=True)
            finally:
                producer_done.set()
                for _ in range(_ai_max_workers):
                    paper_q.put(None)

        def _worker():
            while not _shutdown:
                paper = paper_q.get()
                try:
                    if paper is None:
                        return
                    result = append_paper(paper, enhance=True)
                    with lock:
                        done_count[0] += 1
                        if result == "written":
                            new_count[0] += 1
                        now = time.monotonic()
                        if done_count[0] % 10 == 0 and now - last_log[0] >= 3:
                            last_log[0] = now
                            msg = f"{batch_label}: {done_count[0]} 篇处理 · {new_count[0]} 入库"
                            logger.info(f"[backfill] {msg}")
                            _set_job_status("journal_backfill", "running", msg,
                                            progress={"done": cursor + len(batch), "total": len(journals)})
                finally:
                    paper_q.task_done()

        producer = threading.Thread(target=_produce, daemon=True)
        producer.start()
        workers = [threading.Thread(target=_worker, daemon=True) for _ in range(_ai_max_workers)]
        for w in workers:
            w.start()
        for w in workers:
            w.join()

        # 更新进度
        new_cursor = cursor + len(batch)
        conn.execute(
            "INSERT OR REPLACE INTO subscriptions (key, value) VALUES ('backfill_progress', ?)",
            (_j.dumps({"cursor": new_cursor, "months": months, "done": new_count[0]}),))
        conn.commit()
        sync_write("SELECT 1")

        remaining_n = len(journals) - new_cursor
        if remaining_n > 0:
            msg = f"{batch_label}: {new_count[0]} 篇入库，剩余 {remaining_n} 本期刊待回溯"
        else:
            msg = f"回溯全部完成: {len(journals)} 本 × {months} 个月，共 {prog.get('done',0) + new_count[0]} 篇入库"
        _set_job_status("journal_backfill", "done", msg)
        logger.info(f"[backfill] ✔ {msg}")
    except Exception as e:
        logger.error(f"[backfill] ✖ {e}", exc_info=True)
        _set_job_status("journal_backfill", "error", str(e)[:160])
    finally:
        try:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)
            lock_fh.close()
        except Exception:
            pass


def run_backfill_nightly():
    """夜间调度：读取 BACKFILL_MONTHS 设置，渐进推进期刊回溯。"""
    from backend.db import get_runtime_settings
    st = get_runtime_settings()
    months = int(st.get("BACKFILL_MONTHS", 0))
    if months <= 0:
        return  # 未启用
    nightly = int(st.get("BACKFILL_NIGHTLY", 5))
    # 检查是否已完成
    conn = get_conn()
    row = conn.execute("SELECT value FROM subscriptions WHERE key='backfill_progress'").fetchone()
    if row:
        import json as _j
        prog = _j.loads(row[0])
        subs = _load_subs()
        if prog.get("cursor", 0) >= len(subs.crossref_journals or []):
            return  # 已完成
    logger.info(f"[backfill] 夜间渐进: {months} 个月 × {nightly} 本/晚")
    run_journal_backfill(months=months, nightly=nightly)


def run_stale_rerun():
    """重跑旧流程结果（跨进程单实例）：daemon 与游离进程同时跑会双倍并发
    打穿限流（2026-09-19 实锤 1302 风暴），fcntl 锁保证全局仅一个实例。"""
    import fcntl
    from pathlib import Path as _P
    _P(_RERUN_LOCK_PATH).parent.mkdir(exist_ok=True)
    lock_fh = open(_RERUN_LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        _set_job_status("enhance_rerun", "error", "另一实例正在重跑（跨进程锁），勿重复触发")
        logger.warning("[rerun] ✘ 另一实例运行中，本次跳过")
        lock_fh.close()
        return
    try:
        _run_stale_rerun_impl()
    finally:
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        lock_fh.close()


def _run_stale_rerun_impl():
    """重跑旧流程处理过的论文：按 PIPELINE_VERSION 识别落后结果，逐篇重新
    增强 + 知识卡片。中断续跑天然支持——重跑过的已打新版本，再次触发只补剩余。"""
    from backend.ai.enhance import PIPELINE_VERSION
    _set_job_status("enhance_rerun", "running", "扫描旧流程结果…")
    logger.info(f"[rerun] ▶ 开始（目标版本 {PIPELINE_VERSION}）")
    try:
        chain, profile = get_ai_chain()
        conn = get_conn()
        # 只重跑"正式在册"的论文：已被过滤的不烧配额——
        # ① 在 ignored 池（用户删除/历史 ai_ignore/重跑降级）的跳过
        # ② ai 判 ignore 的降级行跳过（papers 表里有行但已被判出局）
        rows = conn.execute(
            """SELECT p.id, p.title, p.summary, p.authors, p.categories,
                      p.doi, p.published_date, p.url, p.pdf, p.venue,
                      p.citation_count, p.source
               FROM papers p
               JOIN ai_results a ON p.id = a.paper_id
               LEFT JOIN ignored_papers ig ON ig.paper_id = p.id
               WHERE (a.pipeline_version IS NULL OR a.pipeline_version != ?)
                 AND ig.paper_id IS NULL
                 AND COALESCE(a.recommendation, '') != 'ignore'
               ORDER BY p.created_at DESC""",
            (PIPELINE_VERSION,),
        ).fetchall()
        skipped = conn.execute(
            """SELECT COUNT(*) FROM papers p
               JOIN ai_results a ON p.id = a.paper_id
               LEFT JOIN ignored_papers ig ON ig.paper_id = p.id
               WHERE (a.pipeline_version IS NULL OR a.pipeline_version != ?)
                 AND (ig.paper_id IS NOT NULL OR a.recommendation = 'ignore')""",
            (PIPELINE_VERSION,),
        ).fetchone()[0]
        if skipped:
            logger.info(f"[rerun] {skipped} 篇已被过滤（ignore/忽略池），按规则跳过不重跑")
        total = len(rows)
        if not total:
            _set_job_status("enhance_rerun", "done", "无旧流程结果，全部最新")
            logger.info("[rerun] ⊘ 无需重跑")
            return
        logger.info(f"[rerun] {total} 篇旧流程结果待重跑（约 {total * 15 // 60 // 5}–{total * 25 // 60 // 5} 分钟）")

        done = [0]
        redo = [0]
        lock = threading.Lock()
        last_log_t = [time.monotonic()]
        start_time = time.monotonic()

        def _rerun_one(row):
            paper = dict(row)
            if isinstance(paper.get("authors"), str):
                try:
                    paper["authors"] = json.loads(paper["authors"])
                except json.JSONDecodeError:
                    paper["authors"] = []
            if isinstance(paper.get("categories"), str):
                try:
                    paper["categories"] = json.loads(paper["categories"])
                except json.JSONDecodeError:
                    paper["categories"] = []
            enhanced = enhance_single(paper, chain, profile, os.environ.get("LANGUAGE", "Chinese"))
            ai = (enhanced or {}).get("AI", {})
            if not ai.get("_llm_failed") and ai.get("tldr"):
                _insert_ai_row(paper["id"], ai)  # 写入时自动打上 PIPELINE_VERSION
                try:
                    _insert_knowledge_card(paper["id"], {**paper, "AI": ai})
                except Exception as e:
                    logger.warning(f"[rerun] 知识卡片失败 {paper['id']}: {e}")
                if ai.get("recommendation") == "ignore":
                    conn_local = get_conn()
                    conn_local.execute(
                        "INSERT OR REPLACE INTO ignored_papers (paper_id, reason) VALUES (?,?)",
                        (paper["id"], "ai_ignore"))
                    conn_local.commit()
                with lock:
                    redo[0] += 1
            with lock:
                done[0] += 1
                n = done[0]
                now = time.monotonic()
                if n % 10 == 0 or n == total:
                    if now - last_log_t[0] >= 3 or n == total:
                        last_log_t[0] = now
                        elapsed = now - start_time
                        speed = n / max(0.001, elapsed)
                        eta = (total - n) / max(0.0001, speed)
                        msg = f"{n}/{total} · {speed * 60:.1f}篇/分 · ETA {eta / 60:.0f}分（成功重跑 {redo[0]}）"
                        logger.info(f"[rerun] {msg}")
                        _set_job_status("enhance_rerun", "running", msg,
                                        progress={"done": n, "total": total,
                                                  "speed_pmin": round(speed * 60, 1),
                                                  "eta_min": round(eta / 60)})

        with ThreadPoolExecutor(max_workers=_ai_max_workers) as ex:
            futures = [ex.submit(_rerun_one, r) for r in rows]
            for f in as_completed(futures):
                if _shutdown:
                    ex.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    f.result()
                except Exception as e:
                    with lock:
                        done[0] += 0
                    logger.warning(f"[rerun] 处理异常: {e}")
        sync_write("SELECT 1")
        _set_job_status("enhance_rerun", "done",
                        f"重跑完成 {redo[0]}/{total}（中断可续：再次触发只补剩余）")
        logger.info(f"[rerun] ✔ 完成: {redo[0]}/{total} 重跑成功")
    except Exception as e:
        logger.error(f"[rerun] ✖ 失败: {e}", exc_info=True)
        _set_job_status("enhance_rerun", "error", str(e)[:160])


def _stale_counts() -> dict:
    """各层旧版本计数（♻️ 菜单/自动收敛用）。只数正式在册的。"""
    from backend.ai.enhance import ENHANCE_VER, CARD_VER
    conn = get_conn()
    enhance = conn.execute("""
        SELECT COUNT(*) FROM papers p
        JOIN ai_results a ON p.id = a.paper_id
        LEFT JOIN ignored_papers ig ON ig.paper_id = p.id
        WHERE (a.pipeline_version IS NULL OR a.pipeline_version != ?)
          AND ig.paper_id IS NULL AND COALESCE(a.recommendation,'') != 'ignore'
    """, (ENHANCE_VER,)).fetchone()[0]
    card = conn.execute("""
        SELECT COUNT(*) FROM papers p
        JOIN ai_results a ON p.id = a.paper_id
        LEFT JOIN ignored_papers ig ON ig.paper_id = p.id
        LEFT JOIN knowledge_cards kc ON kc.paper_id = p.id
        WHERE (kc.paper_id IS NULL OR kc.card_version IS NULL OR kc.card_version != ?)
          AND ig.paper_id IS NULL AND COALESCE(a.recommendation,'') != 'ignore'
    """, (CARD_VER,)).fetchone()[0]
    return {"enhance": enhance, "card": card}


def run_card_rerun(batch_limit: int = 0, deadline: float | None = None):
    """组件级重跑：只重提知识卡片（关思考 ~3s/篇，不动增强结果）。"""
    from backend.ai.enhance import CARD_VER
    _set_job_status("card_rerun", "running", "扫描卡片旧版本…")
    try:
        from backend.ai.knowledge_extractor import extract_knowledge_card
        from backend.ai.enhance import load_research_profile
        conn = get_conn()
        profile = load_research_profile()
        rows = conn.execute("""
            SELECT a.paper_id, a.tldr, a.motivation, a.method, a.result, a.conclusion,
                   p.title, p.summary
            FROM papers p
            JOIN ai_results a ON p.id = a.paper_id
            LEFT JOIN ignored_papers ig ON ig.paper_id = p.id
            LEFT JOIN knowledge_cards kc ON kc.paper_id = p.id
            WHERE (kc.paper_id IS NULL OR kc.card_version IS NULL OR kc.card_version != ?)
              AND ig.paper_id IS NULL AND COALESCE(a.recommendation,'') != 'ignore'
            ORDER BY CASE a.recommendation WHEN 'must-read' THEN 0
                     WHEN 'recommended' THEN 1 ELSE 2 END, p.created_at DESC
        """, (CARD_VER,)).fetchall()
        if batch_limit > 0:
            rows = rows[:batch_limit]
        total = len(rows)
        if not total:
            _set_job_status("card_rerun", "done", "无旧版卡片")
            return
        done = [0]
        for i, row in enumerate(rows):
            if deadline and time.monotonic() > deadline:
                logger.info(f"[card-rerun] ⏰ 到点，{done[0]}/{total} 后提前停止")
                break
            paper = {"id": row["paper_id"], "title": row["title"], "summary": row["summary"],
                     "AI": {"tldr": row["tldr"], "motivation": row["motivation"],
                            "method": row["method"], "result": row["result"], "conclusion": row["conclusion"]}}
            card = extract_knowledge_card(paper, profile)
            if card:
                # 直接写已提取的卡片（不经过 _insert_knowledge_card 二次提取）
                from backend.ai.enhance import CARD_VER
                from backend.paper_store import CARD_COLS, queue_write
                card["card_version"] = CARD_VER
                cols = ", ".join(CARD_COLS)
                ph = ", ".join(f":{c}" for c in CARD_COLS)
                queue_write(f"INSERT OR REPLACE INTO knowledge_cards ({cols}) VALUES ({ph})",
                            tuple(card.get(c) for c in CARD_COLS))
            done[0] += 1
            if done[0] % 20 == 0 or done[0] == total:
                _set_job_status("card_rerun", "running", f"{done[0]}/{total}",
                                progress={"done": done[0], "total": total})
        sync_write("SELECT 1")
        _set_job_status("card_rerun", "done", f"卡片重提完成 {total} 篇")
        logger.info(f"[card-rerun] ✔ {total} 张卡片重提")
    except Exception as e:
        logger.error(f"[card-rerun] ✖ {e}", exc_info=True)
        _set_job_status("card_rerun", "error", str(e)[:160])


def run_auto_convergence():
    """夜间自动收敛：抓取批完后调用。

    依据百分比+时间上限渐进收敛，不固定篇数：
    - 批量 = max(1, 旧版量 × CONVERGE_PCT%)——积压大时起步快（几何收敛），
      接近清零时自然放慢
    - 单轮时间 ≤ CONVERGE_MAX_MIN 分钟，到点即停（不挤占其他任务配额）
    优先级：卡片重提（3s/篇）→ 增强重跑（15-25s/篇）。
    """
    try:
        from backend.db import get_runtime_settings
        st = get_runtime_settings()
        pct = max(1, min(50, int(st.get("CONVERGE_PCT", 10))))
        max_min = max(5, min(120, int(st.get("CONVERGE_MAX_MIN", 30))))
        deadline = time.monotonic() + max_min * 60
        stale = _stale_counts()

        if stale["card"]:
            batch = max(1, stale["card"] * pct // 100)
            logger.info(f"[收敛] 卡片旧版 {stale['card']} 篇 × {pct}% → 本轮 ≤{batch} 篇，限时 {max_min}分")
            run_card_rerun(batch_limit=batch, deadline=deadline)
            return

        if stale["enhance"]:
            batch = max(1, stale["enhance"] * pct // 100)
            logger.info(f"[收敛] 增强旧版 {stale['enhance']} 篇 × {pct}% → 本轮 ≤{batch} 篇，限时 {max_min}分")
            from backend.ai.enhance import PIPELINE_VERSION
            conn = get_conn()
            rows = conn.execute("""
                SELECT p.id FROM papers p
                JOIN ai_results a ON p.id = a.paper_id
                LEFT JOIN ignored_papers ig ON ig.paper_id = p.id
                WHERE (a.pipeline_version IS NULL OR a.pipeline_version != ?)
                  AND ig.paper_id IS NULL AND COALESCE(a.recommendation,'') != 'ignore'
                ORDER BY CASE a.recommendation WHEN 'must-read' THEN 0
                         WHEN 'recommended' THEN 1 ELSE 2 END, p.created_at DESC
                LIMIT ?
            """, (PIPELINE_VERSION, batch)).fetchall()
            if rows:
                _converge_enhance([r["id"] for r in rows], deadline=deadline)
    except Exception as e:
        logger.warning(f"[收敛] 跳过: {e}")


def _converge_enhance(pids: list, deadline: float | None = None):
    """增强收敛的限量执行（deadline 到点即停）。"""
    chain, profile = get_ai_chain()
    conn = get_conn()
    _done = 0
    for pid in pids:
        if deadline and time.monotonic() > deadline:
            logger.info(f"[收敛] ⏰ 时间到点，{_done}/{len(pids)} 后提前停止")
            break
        row = conn.execute("SELECT id, title, summary, authors, categories FROM papers WHERE id=?", (pid,)).fetchone()
        if not row:
            continue
        paper = dict(row)
        if isinstance(paper.get("authors"), str):
            try: paper["authors"] = json.loads(paper["authors"])
            except Exception: paper["authors"] = []
        if isinstance(paper.get("categories"), str):
            try: paper["categories"] = json.loads(paper["categories"])
            except Exception: paper["categories"] = []
        enhanced = enhance_single(paper, chain, profile, AI_LANGUAGE)
        ai = (enhanced or {}).get("AI", {})
        if not ai.get("_llm_failed") and ai.get("tldr"):
            _insert_ai_row(pid, ai)
            try:
                _insert_knowledge_card(pid, {**paper, "AI": ai})
            except Exception:
                pass
        _done += 1
    sync_write("SELECT 1")
    logger.info(f"[收敛] 增强补跑 {_done}/{len(pids)} 篇完成")


def run_digest_job():
    logger.info("[digest] ▶ 开始")
    _set_job_status("digest", "running", "简报生成中…")
    try:
        path = generate_digest()
        if path:
            logger.info(f"[digest] ✔ 已保存: {path}")
            _set_job_status("digest", "done", f"已保存 {path}")
        else:
            logger.info(f"[digest] ⊘ 今日无新论文")
            _set_job_status("digest", "done", "今日无新论文")
    except Exception as e:
        logger.error(f"[digest] ✖ 失败: {e}", exc_info=True)
        _set_job_status("digest", "error", str(e)[:160])


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

    Automatic runs start daily at NIGHT_START (default 02:00, any hour
    0-23 allowed), with jobs spread STAGGER_MINUTES apart
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
            logger.info("[调度器] RUN_ON_START=1，启动时立即执行全部任务（此后仍按每日计划）")
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
        running = {n for n, s in dict(_job_status).items() if s.get("status") == "running"}
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
