from __future__ import annotations

import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from ai.digest import generate_digest
from ai.enhance import enhance_single
from crawler.arxiv_crawler import ArxivCrawler
from crawler.author_crawler import AuthorCrawler
from crawler.crossref_crawler import CrossrefCrawler
from crawler.dblp_crawler import DblpCrawler
from crawler.s2_crawler import S2Crawler
from crawler.subs_store import Subscriptions

from paper_store import (
    append_paper, get_ai_chain, get_quick_chain, reset_ai_chain,
    _enhanced_ids, _written_ids, _ids_lock, DATA_DIR,
)

logger = logging.getLogger("jobs")

_job_status: dict[str, dict] = {}
_ai_max_workers = int(os.environ.get("AI_MAX_WORKERS", "3"))
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


def run_arxiv_job():
    _set_job_status("arxiv", "running")
    logger.info("Starting arXiv crawl job (streaming)")
    try:
        subs = _load_subs()
        if not subs.arxiv_categories:
            logger.info("No arXiv categories subscribed, skipping")
            _set_job_status("arxiv", "skipped", "no categories")
            return
        from paper_store import load_existing_ids
        existing = load_existing_ids()
        crawler = ArxivCrawler(categories=subs.arxiv_categories, existing_ids=existing)
        fetched, written = 0, 0
        for paper in crawler.crawl_iter():
            fetched += 1
            if append_paper(paper, enhance=True):
                written += 1
            if fetched % 20 == 0:
                logger.info(f"arXiv progress: {fetched} fetched, {written} written")
        logger.info(f"arXiv job done: {fetched} fetched, {written} new written")
        _set_job_status("arxiv", "done", f"{fetched} fetched, {written} written")
    except Exception as e:
        logger.error(f"arXiv job failed: {e}", exc_info=True)
        _set_job_status("arxiv", "error", str(e))


def run_crossref_job():
    _set_job_status("crossref", "running")
    logger.info("Starting Crossref crawl job (streaming)")
    try:
        subs = _load_subs()
        if not subs.crossref_journals:
            _set_job_status("crossref", "skipped", "no journals")
            return
        crawler = CrossrefCrawler(journals=subs.crossref_journals)
        fetched, written = 0, 0
        fetched_journals: set[str] = set()
        for paper in crawler.crawl_iter():
            fetched += 1
            if paper.journal_title:
                fetched_journals.add(paper.journal_title)
            if append_paper(paper, enhance=True):
                written += 1
            if fetched % 20 == 0:
                logger.info(f"Crossref progress: {fetched} fetched, {written} written")
        if fetched_journals:
            now = datetime.now(timezone.utc).isoformat()
            for j in subs.crossref_journals:
                if j.name in fetched_journals:
                    j.last_updated = now
            _save_subs(subs)
        logger.info(f"Crossref job done: {fetched} fetched, {written} new written")
        _set_job_status("crossref", "done", f"{fetched} fetched, {written} written")
    except Exception as e:
        logger.error(f"Crossref job failed: {e}", exc_info=True)
        _set_job_status("crossref", "error", str(e))


def run_dblp_job():
    _set_job_status("dblp", "running")
    logger.info("Starting DBLP crawl job")
    try:
        subs = _load_subs()
        if not subs.conferences:
            _set_job_status("dblp", "skipped", "no conferences")
            return
        crawler = DblpCrawler(conferences=subs.conferences)
        fetched, written = 0, 0
        fetched_venues: set[str] = set()
        for paper in crawler.crawl_iter():
            fetched += 1
            fetched_venues.add(paper.venue)
            if append_paper(paper, enhance=True):
                written += 1
            if fetched % 20 == 0:
                logger.info(f"DBLP progress: {fetched} fetched, {written} written")
        if fetched_venues:
            now = datetime.now(timezone.utc).isoformat()
            for c in subs.conferences:
                if any(c.venue in v for v in fetched_venues):
                    c.last_updated = now
            _save_subs(subs)
        logger.info(f"DBLP job done: {fetched} fetched, {written} new written")
        _set_job_status("dblp", "done", f"{fetched} fetched, {written} written")
    except Exception as e:
        logger.error(f"DBLP job failed: {e}", exc_info=True)
        _set_job_status("dblp", "error", str(e))


def run_s2_job():
    _set_job_status("s2", "running")
    logger.info("Starting S2 search job")
    try:
        subs = _load_subs()
        keywords = subs.search_keywords
        if not keywords:
            from ai.enhance import load_research_profile
            profile = load_research_profile()
            keywords = profile.get("keywords", [])
        if not keywords:
            _set_job_status("s2", "skipped", "no keywords")
            return
        crawler = S2Crawler(keywords=keywords, max_per_keyword=20)
        fetched, written = 0, 0
        for paper in crawler.crawl_iter():
            fetched += 1
            if append_paper(paper, enhance=True):
                written += 1
            if fetched % 20 == 0:
                logger.info(f"S2 progress: {fetched} fetched, {written} written")
        logger.info(f"S2 job done: {fetched} fetched, {written} new written")
        _set_job_status("s2", "done", f"{fetched} fetched, {written} written")
    except Exception as e:
        logger.error(f"S2 search job failed: {e}", exc_info=True)
        _set_job_status("s2", "error", str(e))


def run_author_job():
    _set_job_status("author", "running")
    logger.info("Starting author crawl job")
    try:
        subs = _load_subs()
        if not subs.authors:
            _set_job_status("author", "skipped", "no authors")
            return
        author_dicts = [
            {"authorId": a.author_id, "name": a.name}
            for a in subs.authors
        ]
        crawler = AuthorCrawler(authors=author_dicts, papers_per_author=50)
        fetched, written = 0, 0
        for paper in crawler.crawl_iter():
            fetched += 1
            if append_paper(paper, enhance=True):
                written += 1
            if fetched % 20 == 0:
                logger.info(f"Author crawl progress: {fetched} fetched, {written} written")
        now = datetime.now(timezone.utc).isoformat()
        for a in subs.authors:
            a.last_updated = now
        _save_subs(subs)
        logger.info(f"Author job done: {fetched} fetched, {written} new written")
        _set_job_status("author", "done", f"{fetched} fetched, {written} written")
    except Exception as e:
        logger.error(f"Author job failed: {e}", exc_info=True)
        _set_job_status("author", "error", str(e))


def run_retro_enhance():
    logger.info("Starting retro-enhance for papers without AI data")
    try:
        chain, profile = get_ai_chain()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        import json
        from paper_store import AI_LANGUAGE, _enhanced_ids, _written_ids, _ids_lock

        ai_path = DATA_DIR / f"{today}_AI_enhanced_{AI_LANGUAGE}.jsonl"
        to_enhance = []
        for f in sorted(DATA_DIR.glob("*.jsonl")):
            if "_AI_" in f.name:
                continue
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        p = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    pid = p.get("id", "")
                    if pid in _enhanced_ids or pid in _written_ids:
                        continue
                    if not p.get("summary") and not p.get("title"):
                        continue
                    to_enhance.append(p)

        if not to_enhance:
            logger.info("No papers to retro-enhance")
            return

        logger.info(f"Retro-enhance: {len(to_enhance)} papers to process")
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
                        with open(ai_path, "a", encoding="utf-8") as af:
                            af.write(json.dumps(result, ensure_ascii=False) + "\n")
                        pid = p.get("id", "")
                        with _ids_lock:
                            _written_ids.add(pid)
                        _enhanced_ids.add(pid)
                        enhanced_count += 1
                except Exception as e:
                    logger.warning(f"Retro-enhance failed for {p.get('id','?')}: {e}")
                if enhanced_count % 10 == 0:
                    logger.info(f"Retro-enhance progress: {enhanced_count}/{len(to_enhance)}")

        logger.info(f"Retro-enhance done: {enhanced_count} papers enhanced")
    except Exception as e:
        logger.error(f"Retro-enhance job failed: {e}", exc_info=True)


def run_digest_job():
    logger.info("Starting digest generation")
    try:
        path = generate_digest()
        if path:
            logger.info(f"Digest generated: {path}")
        else:
            logger.info("No papers to digest today")
    except Exception as e:
        logger.error(f"Digest job failed: {e}", exc_info=True)


JOB_FUNCS = {
    "arxiv": run_arxiv_job,
    "crossref": run_crossref_job,
    "dblp": run_dblp_job,
    "s2": run_s2_job,
    "author": run_author_job,
}


class Scheduler:
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
        logger.info("Scheduler stopped")

    def _run_and_reschedule(self, job_name: str, interval_hours: int):
        if not self._running:
            return
        try:
            JOB_FUNCS[job_name]()
        except Exception as e:
            logger.error(f"Scheduled {job_name} job error: {e}")

        if job_name == "arxiv":
            try:
                run_retro_enhance()
            except Exception as e:
                logger.error(f"Retro-enhance after arxiv error: {e}")
            try:
                run_digest_job()
            except Exception as e:
                logger.error(f"Digest after arxiv error: {e}")

        if self._running:
            t = threading.Timer(
                interval_hours * 3600,
                self._run_and_reschedule,
                args=[job_name, interval_hours],
            )
            t.daemon = True
            t.start()
            self._timers.append(t)
