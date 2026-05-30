#!/usr/bin/env python3
"""arxivSCI-daily daemon: persistent service with dual-source subscription."""

import argparse
import json
import logging
import signal
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from crawler.arxiv_crawler import ArxivCrawler
from crawler.crossref_crawler import CrossrefCrawler
from crawler.models import Paper
from crawler.subs_store import Subscriptions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("daemon")

# ── Flask App ──────────────────────────────────────────────────────

app = Flask(__name__, static_folder=".", static_url_path="")

SUBS_PATH = "subscriptions.json"
DATA_DIR = Path("data")


def _load_subs() -> Subscriptions:
    return Subscriptions.load(SUBS_PATH)


def _save_subs(subs: Subscriptions) -> None:
    subs.save(SUBS_PATH)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


@app.route("/api/subscriptions", methods=["GET"])
def get_subscriptions():
    subs = _load_subs()
    return jsonify(subs.to_dict())


@app.route("/api/papers", methods=["GET"])
def get_papers():
    papers = []
    if DATA_DIR.exists():
        for f in sorted(DATA_DIR.glob("*.jsonl"), reverse=True):
            if "_AI_" in f.name:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            papers.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            pass
        # Also load raw (non-AI) files for papers not yet enhanced
        ai_ids = {p.get("id") for p in papers}
        for f in sorted(DATA_DIR.glob("*.jsonl"), reverse=True):
            if "_AI_" not in f.name:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            p = json.loads(line.strip())
                            if p.get("id") not in ai_ids:
                                papers.append(p)
                        except json.JSONDecodeError:
                            pass
    return jsonify({"papers": papers[:500]})


@app.route("/api/subscriptions", methods=["PUT"])
def put_subscriptions():
    data = request.get_json()
    if not data:
        return jsonify({"error": "empty body"}), 400
    try:
        cats = data.get("arxiv", {}).get("categories", [])
        journals_data = data.get("crossref", {}).get("journals", [])
        from crawler.subs_store import Journal
        journals = [
            Journal(
                issn=j["issn"],
                name=j["name"],
                last_updated=j.get("lastUpdated"),
            )
            for j in journals_data
        ]
        subs = Subscriptions(arxiv_categories=cats, crossref_journals=journals)
        _save_subs(subs)
        logger.info(f"Subscriptions updated: {len(cats)} cats, {len(journals)} journals")
        return jsonify(subs.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── Crawl Logic ────────────────────────────────────────────────────


def _load_existing_ids() -> set:
    existing: set[str] = set()
    if not DATA_DIR.exists():
        return existing
    for f in DATA_DIR.glob("*.jsonl"):
        if "_AI_" in f.name:
            continue
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    pid = data.get("id") or data.get("doi", "")
                    if pid:
                        existing.add(pid)
                except json.JSONDecodeError:
                    pass
    return existing


def _append_paper(paper: Paper, date_str: str | None = None) -> bool:
    """Append a single paper to JSONL. Returns True if written (new)."""
    date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    DATA_DIR.mkdir(exist_ok=True)
    filepath = DATA_DIR / f"{date_str}.jsonl"

    existing_ids: set[str] = set()
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line.strip())
                    existing_ids.add(d.get("id", ""))
                except json.JSONDecodeError:
                    pass

    if paper.id in existing_ids:
        return False

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(paper.to_jsonl() + "\n")
    return True


def _write_papers(papers: list, date_str: str | None = None) -> int:
    if not papers:
        return 0
    written = 0
    for p in papers:
        if _append_paper(p, date_str):
            written += 1
    return written


def run_arxiv_job():
    logger.info("Starting arXiv crawl job (streaming)")
    try:
        subs = _load_subs()
        if not subs.arxiv_categories:
            logger.info("No arXiv categories subscribed, skipping")
            return
        existing = _load_existing_ids()
        crawler = ArxivCrawler(
            categories=subs.arxiv_categories,
            existing_ids=existing,
        )
        fetched, written = 0, 0
        for paper in crawler.crawl_iter():
            fetched += 1
            if _append_paper(paper):
                written += 1
            if fetched % 20 == 0:
                logger.info(f"arXiv progress: {fetched} fetched, {written} written")
        logger.info(f"arXiv job done: {fetched} fetched, {written} new written")
    except Exception as e:
        logger.error(f"arXiv job failed: {e}", exc_info=True)


def run_crossref_job():
    logger.info("Starting Crossref crawl job (streaming)")
    try:
        subs = _load_subs()
        if not subs.crossref_journals:
            logger.info("No Crossref journals subscribed, skipping")
            return
        crawler = CrossrefCrawler(journals=subs.crossref_journals)
        fetched, written = 0, 0
        fetched_journals: set[str] = set()
        for paper in crawler.crawl_iter():
            fetched += 1
            if paper.journal_title:
                fetched_journals.add(paper.journal_title)
            if _append_paper(paper):
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
    except Exception as e:
        logger.error(f"Crossref job failed: {e}", exc_info=True)


def run_enhance_job():
    logger.info("Starting AI enhance job")
    try:
        import subprocess
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        raw_file = DATA_DIR / f"{today}.jsonl"
        if not raw_file.exists():
            logger.info(f"No raw file for {today}, skipping enhance")
            return
        result = subprocess.run(
            [sys.executable, "enhance.py", f"--data ../data/{today}.jsonl"],
            cwd="ai",
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            logger.error(f"Enhance failed: {result.stderr[-500:]}")
        else:
            logger.info("AI enhance job done")
    except Exception as e:
        logger.error(f"Enhance job failed: {e}", exc_info=True)


# ── Scheduler ──────────────────────────────────────────────────────


class Scheduler:
    def __init__(self):
        self._timers: list[threading.Timer] = []
        self._running = False

    def start(self):
        self._running = True
        self._run_and_reschedule("arxiv", interval_hours=3)
        self._run_and_reschedule("crossref", interval_hours=24)

    def stop(self):
        self._running = False
        for t in self._timers:
            t.cancel()
        logger.info("Scheduler stopped")

    def _run_and_reschedule(self, job_name: str, interval_hours: int):
        if not self._running:
            return
        try:
            if job_name == "arxiv":
                run_arxiv_job()
            elif job_name == "crossref":
                run_crossref_job()
        except Exception as e:
            logger.error(f"Scheduled {job_name} job error: {e}")

        if job_name == "arxiv":
            try:
                run_enhance_job()
            except Exception as e:
                logger.error(f"Enhance after arxiv error: {e}")

        if self._running:
            t = threading.Timer(
                interval_hours * 3600,
                self._run_and_reschedule,
                args=[job_name, interval_hours],
            )
            t.daemon = True
            t.start()
            self._timers.append(t)


# ── Main ───────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="arxivSCI-daily daemon")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--config", default="subscriptions.json", help="Subscriptions file")
    args = parser.parse_args()

    global SUBS_PATH
    SUBS_PATH = args.config

    if not Path(SUBS_PATH).exists():
        _save_subs(Subscriptions())
        logger.info(f"Created default {SUBS_PATH}")

    sched = Scheduler()

    def _signal_handler(sig, frame):
        logger.info("Shutting down...")
        sched.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    sched_thread = threading.Thread(target=sched.start, daemon=True)
    sched_thread.start()
    logger.info("Scheduler started: arXiv every 3h, Crossref every 24h")

    logger.info(f"Starting server on port {args.port}")
    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
