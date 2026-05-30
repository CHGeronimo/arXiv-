#!/usr/bin/env python3
"""arxivSCI-daily daemon: persistent service with dual-source subscription."""

import argparse
import json
import logging
import os
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from ai.digest import generate_digest
from ai.enhance import enhance_single, build_chain, load_research_profile
from ai.quick_filter import build_quick_filter, quick_filter_paper
from crawler.arxiv_crawler import ArxivCrawler
from crawler.author_crawler import AuthorCrawler
from crawler.crossref_crawler import CrossrefCrawler
from crawler.dblp_crawler import DblpCrawler
from crawler.s2_crawler import S2Crawler
from crawler.models import Paper
from crawler.subs_store import Subscriptions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("daemon")
logging.getLogger("arxiv").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# ── Flask App ──────────────────────────────────────────────────────

app = Flask(__name__, static_folder=".", static_url_path="")

BASE_DIR = Path(".")
SUBS_PATH = "subscriptions.json"
DATA_DIR = Path("data")
FEEDBACK_FILE = BASE_DIR / "feedback.json"


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
    source_filter = request.args.get("source", "all")
    article_type = request.args.get("type", "all")
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = min(5000, max(1, int(request.args.get("per_page", 50))))
    except (ValueError, TypeError):
        per_page = 50

    papers = []
    if DATA_DIR.exists():
        seen_ids: set[str] = set()
        seen_dois: set[str] = set()
        # AI-enhanced files first (preferred)
        for f in sorted(DATA_DIR.glob("*.jsonl"), reverse=True):
            if "_AI_" in f.name:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            p = json.loads(line.strip())
                            pid = p.get("id", "")
                            doi = p.get("doi", "")
                            if pid in seen_ids:
                                continue
                            if doi and doi in seen_dois:
                                continue
                            seen_ids.add(pid)
                            if doi:
                                seen_dois.add(doi)
                            papers.append(p)
                        except json.JSONDecodeError:
                            pass
        # Raw files (only add if not already seen)
        for f in sorted(DATA_DIR.glob("*.jsonl"), reverse=True):
            if "_AI_" not in f.name:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        try:
                            p = json.loads(line.strip())
                            pid = p.get("id", "")
                            doi = p.get("doi", "")
                            if pid in seen_ids:
                                continue
                            if doi and doi in seen_dois:
                                continue
                            seen_ids.add(pid)
                            if doi:
                                seen_dois.add(doi)
                            papers.append(p)
                        except json.JSONDecodeError:
                            pass

    if source_filter != "all":
        papers = [p for p in papers if p.get("source") == source_filter]

    if article_type != "all":
        papers = [p for p in papers if p.get("article_type") == article_type]

    total = len(papers)
    start = (page - 1) * per_page
    return jsonify({
        "papers": papers[start:start + per_page],
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@app.route("/api/stats")
def get_stats():
    total = len(_written_ids)
    source_counts: dict[str, int] = {}
    if DATA_DIR.exists():
        for f in DATA_DIR.glob("*.jsonl"):
            if "_AI_" in f.name:
                continue
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        p = json.loads(line.strip())
                        s = p.get("source", "unknown")
                        source_counts[s] = source_counts.get(s, 0) + 1
                    except json.JSONDecodeError:
                        pass
    subs = _load_subs()
    return jsonify({
        "total_papers": total,
        "by_source": source_counts,
        "arxiv_categories": subs.arxiv_categories,
        "crossref_journals": len(subs.crossref_journals),
    })


@app.route("/api/subscriptions", methods=["PUT"])
def put_subscriptions():
    data = request.get_json()
    if not data:
        return jsonify({"error": "empty body"}), 400
    try:
        cats = data.get("arxiv", {}).get("categories", [])
        journals_data = data.get("crossref", {}).get("journals", [])
        conferences_data = data.get("conferences", [])
        search_keywords = data.get("search", {}).get("keywords", [])
        authors_data = data.get("authors", [])
        from crawler.subs_store import Journal, Conference, Author
        journals = [
            Journal(issn=j["issn"], name=j["name"], last_updated=j.get("lastUpdated"))
            for j in journals_data
        ]
        conferences = [
            Conference(venue=c["venue"], last_updated=c.get("lastUpdated"))
            for c in conferences_data
        ]
        authors = [
            Author(
                name=a["name"],
                author_id=a.get("authorId", a.get("author_id", "")),
                affiliation=a.get("affiliation", ""),
                paper_count=a.get("paperCount", a.get("paper_count", 0)),
                last_updated=a.get("lastUpdated"),
            )
            for a in authors_data
        ]
        subs = Subscriptions(
            arxiv_categories=cats,
            crossref_journals=journals,
            conferences=conferences,
            search_keywords=search_keywords,
            authors=authors,
        )
        _save_subs(subs)
        logger.info(f"Subscriptions updated: {len(cats)} cats, {len(journals)} journals, {len(conferences)} conferences, {len(authors)} authors")
        return jsonify(subs.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/profile", methods=["GET"])
def get_profile():
    profile_path = Path("research_profile.json")
    if profile_path.exists():
        return jsonify(json.loads(profile_path.read_text(encoding="utf-8")))
    return jsonify({"direction": "", "keywords": [], "quality_criteria": ""})


@app.route("/api/profile", methods=["PUT"])
def put_profile():
    data = request.get_json()
    if not data:
        return jsonify({"error": "empty body"}), 400
    Path("research_profile.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    global _ai_chain, _ai_profile
    _ai_chain = None
    _ai_profile = None
    logger.info("Research profile updated, AI chain reset")
    return jsonify(data)


@app.route("/api/trigger/<job>", methods=["POST"])
def trigger_job(job: str):
    if job not in ("arxiv", "crossref", "dblp", "s2", "author"):
        return jsonify({"error": "unknown job"}), 400
    job_funcs = {
        "arxiv": run_arxiv_job,
        "crossref": run_crossref_job,
        "dblp": run_dblp_job,
        "s2": run_s2_job,
        "author": run_author_job,
    }
    threading.Thread(target=job_funcs[job], daemon=True).start()
    logger.info(f"Manually triggered {job} job")
    return jsonify({"status": "triggered", "job": job})


@app.route("/api/trigger/enhance", methods=["POST"])
def trigger_enhance():
    threading.Thread(target=run_retro_enhance, daemon=True).start()
    logger.info("Manually triggered retro-enhance job")
    return jsonify({"status": "triggered", "job": "enhance"})


@app.route("/api/jobs", methods=["GET"])
def get_job_status():
    return jsonify(_job_status)


@app.route("/api/digest/<date_str>", methods=["GET"])
def get_digest(date_str: str):
    digest_path = Path("digests") / f"{date_str}.md"
    if digest_path.exists():
        return digest_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/markdown"}
    return jsonify({"error": "digest not found"}), 404


@app.route("/api/digests", methods=["GET"])
def list_digests():
    digest_dir = Path("digests")
    if not digest_dir.exists():
        return jsonify({"digests": []})
    digests = sorted(digest_dir.glob("*.md"), reverse=True)
    return jsonify({"digests": [d.stem for d in digests]})


def _update_profile_from_feedback(paper_id: str, rating: str):
    """Update liked/disliked topics based on feedback."""
    profile_path = BASE_DIR / "research_profile.json"
    if not profile_path.exists():
        return
    with open(profile_path, "r") as f:
        profile = json.load(f)

    # Find paper to extract topics
    paper = None
    for f in DATA_DIR.glob("*_AI_enhanced_*.jsonl"):
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    p = json.loads(line.strip())
                    if p.get("id") == paper_id:
                        paper = p
                        break
                except json.JSONDecodeError:
                    pass
        if paper:
            break

    if not paper:
        return

    title = paper.get("title", "")

    if rating == "useful":
        liked = profile.get("liked_topics", [])
        if title not in liked:
            liked.append(title)
        profile["liked_topics"] = liked[-20:]
    else:
        disliked = profile.get("disliked_topics", [])
        if title not in disliked:
            disliked.append(title)
        profile["disliked_topics"] = disliked[-20:]

    # Reset AI chain to pick up updated profile
    global _ai_chain, _ai_profile
    _ai_chain = None
    _ai_profile = None

    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


@app.route("/api/feedback", methods=["POST"])
def save_feedback():
    data = request.json or {}
    paper_id = data.get("paper_id", "")
    rating = data.get("rating", "")
    if not paper_id or rating not in ("useful", "not_useful"):
        return jsonify({"error": "invalid"}), 400

    feedback = {}
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, "r") as f:
            feedback = json.load(f)
    feedback[paper_id] = rating
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(feedback, f, indent=2, ensure_ascii=False)

    _update_profile_from_feedback(paper_id, rating)
    return jsonify({"status": "saved"})


@app.route("/api/feedback", methods=["GET"])
def get_feedback():
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, "r") as f:
            return jsonify(json.load(f))
    return jsonify({})


@app.route("/api/author/search", methods=["GET"])
def search_author_api():
    query = request.args.get("query", "").strip()
    if not query or len(query) < 2:
        return jsonify({"authors": []})
    from crawler.author_crawler import search_authors, resolve_orcid_to_author
    # If query looks like an ORCID, resolve it
    if query.startswith("0000-") or "orcid.org" in query:
        author = resolve_orcid_to_author(query)
        return jsonify({"authors": [author] if author else []})
    results = search_authors(query, limit=10)
    return jsonify({"authors": results})


def _bibtex_for(paper: dict) -> str:
    authors = " and ".join(paper.get("authors") or [])
    year = (paper.get("published_date") or "")[:4]
    key = (paper.get("id") or "unknown").replace("/", "_").replace(":", "_")[:40]
    title = paper.get("title") or ""
    venue = paper.get("venue") or paper.get("journal_title") or ""
    doi = paper.get("doi") or ""
    lines = [f"@article{{{key},"]
    if title: lines.append(f"  title = {{{title}}},")
    if authors: lines.append(f"  author = {{{authors}}},")
    if year: lines.append(f"  year = {{{year}}},")
    if venue: lines.append(f"  journal = {{{venue}}},")
    if doi: lines.append(f"  doi = {{{doi}}},")
    url = paper.get("url") or ""
    if url: lines.append(f"  url = {{{url}}},")
    lines.append("}")
    return "\n".join(lines)


@app.route("/api/export/bibtex", methods=["POST"])
def export_bibtex():
    data = request.get_json()
    ids = data.get("ids", []) if data else []
    if not ids:
        return jsonify({"error": "no ids provided"}), 400
    papers_map: dict[str, dict] = {}
    if DATA_DIR.exists():
        for f in DATA_DIR.glob("*.jsonl"):
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        p = json.loads(line.strip())
                        pid = p.get("id", "")
                        if pid and pid in ids:
                            papers_map[pid] = p
                    except json.JSONDecodeError:
                        pass
    entries = []
    for pid in ids:
        p = papers_map.get(pid)
        if p:
            entries.append(_bibtex_for(p))
    if not entries:
        return jsonify({"error": "no papers found"}), 404
    return "\n\n".join(entries), 200, {"Content-Type": "application/x-bibtex"}



# ── Crawl Logic ────────────────────────────────────────────────────

_ai_chain = None
_ai_profile = None
_ai_language = "Chinese"

def _get_ai_chain():
    global _ai_chain, _ai_profile
    if _ai_chain is None:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        _ai_chain = build_chain(model_name)
        _ai_profile = load_research_profile()
        logger.info(f"AI chain initialized: {model_name}")
    return _ai_chain, _ai_profile


def _get_quick_chain():
    global _quick_chain
    if _quick_chain is None:
        _quick_chain = build_quick_filter()
        logger.info("Quick filter chain initialized")
    return _quick_chain

_written_ids: set[str] = set()
_enhanced_ids: set[str] = set()
_ids_lock = threading.Lock()
_job_status: dict[str, dict] = {}
_ai_max_workers = int(os.environ.get("AI_MAX_WORKERS", "3"))
_quick_chain = None
_shutdown = False


def _set_job_status(job: str, status: str, msg: str = ""):
    _job_status[job] = {"status": status, "message": msg, "updated": datetime.now(timezone.utc).isoformat()}


def _load_existing_ids() -> set[str]:
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


def _load_enhanced_ids() -> set[str]:
    """Load IDs of papers that already have AI enhancement."""
    enhanced: set[str] = set()
    if not DATA_DIR.exists():
        return enhanced
    for f in DATA_DIR.glob("*_AI_enhanced_*.jsonl"):
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    data = json.loads(line.strip())
                    pid = data.get("id") or data.get("doi", "")
                    if pid:
                        enhanced.add(pid)
                except (json.JSONDecodeError, KeyError):
                    pass
    return enhanced


def _append_paper(paper: Paper, date_str: str | None = None, enhance: bool = False) -> bool:
    """Append a single paper to JSONL. Returns True if written (new)."""
    with _ids_lock:
        if paper.id in _written_ids:
            return False

    date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    DATA_DIR.mkdir(exist_ok=True)

    if enhance:
        # Skip if already enhanced
        if paper.id in _enhanced_ids:
            with _ids_lock:
                _written_ids.add(paper.id)
            return False

        paper_dict = json.loads(paper.to_jsonl())

        # Step 1: Quick filter
        quick_chain = _get_quick_chain()
        chain, profile = _get_ai_chain()
        if not quick_filter_paper(paper_dict, quick_chain, profile):
            # Not relevant — write with skip marker
            paper_dict["AI"] = {
                "tldr": "", "motivation": "", "method": "", "result": "", "conclusion": "",
                "title_zh": "", "summary_zh": "",
                "quality_score": 0, "relevance_score": 0, "recommendation": "skip",
                "skip_reason": "Filtered by quick relevance check",
            }
            ai_path = DATA_DIR / f"{date_str}_AI_enhanced_{_ai_language}.jsonl"
            with open(ai_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(paper_dict, ensure_ascii=False) + "\n")
            with _ids_lock:
                _written_ids.add(paper.id)
            _enhanced_ids.add(paper.id)
            return True

        # Step 2: Full enhancement for relevant papers
        try:
            enhanced = enhance_single(paper_dict, chain, profile, _ai_language)
            if enhanced:
                ai_path = DATA_DIR / f"{date_str}_AI_enhanced_{_ai_language}.jsonl"
                with open(ai_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(enhanced, ensure_ascii=False) + "\n")
                with _ids_lock:
                    _written_ids.add(paper.id)
                _enhanced_ids.add(paper.id)
                return True
        except Exception as e:
            logger.warning(f"AI enhance failed for {paper.id}: {e}")

    filepath = DATA_DIR / f"{date_str}.jsonl"
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(paper.to_jsonl() + "\n")
    with _ids_lock:
        _written_ids.add(paper.id)
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
    _set_job_status("arxiv", "running")
    logger.info("Starting arXiv crawl job (streaming)")
    try:
        subs = _load_subs()
        if not subs.arxiv_categories:
            logger.info("No arXiv categories subscribed, skipping")
            _set_job_status("arxiv", "skipped", "no categories")
            return
        existing = _load_existing_ids()
        crawler = ArxivCrawler(
            categories=subs.arxiv_categories,
            existing_ids=existing,
        )
        fetched, written = 0, 0
        for paper in crawler.crawl_iter():
            fetched += 1
            if _append_paper(paper, enhance=True):
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
            logger.info("No Crossref journals subscribed, skipping")
            _set_job_status("crossref", "skipped", "no journals")
            return
        crawler = CrossrefCrawler(journals=subs.crossref_journals)
        fetched, written = 0, 0
        fetched_journals: set[str] = set()
        for paper in crawler.crawl_iter():
            fetched += 1
            if paper.journal_title:
                fetched_journals.add(paper.journal_title)
            if _append_paper(paper, enhance=True):
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
            logger.info("No conferences subscribed, skipping DBLP")
            _set_job_status("dblp", "skipped", "no conferences")
            return
        crawler = DblpCrawler(conferences=subs.conferences)
        fetched, written = 0, 0
        fetched_venues: set[str] = set()
        for paper in crawler.crawl_iter():
            fetched += 1
            fetched_venues.add(paper.venue)
            if _append_paper(paper, enhance=True):
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
            profile = load_research_profile()
            keywords = profile.get("keywords", [])
        if not keywords:
            logger.info("No search keywords, skipping S2")
            _set_job_status("s2", "skipped", "no keywords")
            return
        crawler = S2Crawler(keywords=keywords, max_per_keyword=20)
        fetched, written = 0, 0
        for paper in crawler.crawl_iter():
            fetched += 1
            if _append_paper(paper, enhance=True):
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
            logger.info("No subscribed authors, skipping")
            _set_job_status("author", "skipped", "no authors")
            return
        author_dicts = [
            {
                "authorId": a.author_id,
                "name": a.name,
            }
            for a in subs.authors
        ]
        crawler = AuthorCrawler(authors=author_dicts, papers_per_author=50)
        fetched, written = 0, 0
        for paper in crawler.crawl_iter():
            fetched += 1
            if _append_paper(paper, enhance=True):
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
        chain, profile = _get_ai_chain()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ai_path = DATA_DIR / f"{today}_AI_enhanced_{_ai_language}.jsonl"

        # Collect unenhanced papers
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
                executor.submit(enhance_single, p, chain, profile, _ai_language): p
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


# ── Scheduler ──────────────────────────────────────────────────────


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
            if job_name == "arxiv":
                run_arxiv_job()
            elif job_name == "crossref":
                run_crossref_job()
            elif job_name == "dblp":
                run_dblp_job()
            elif job_name == "s2":
                run_s2_job()
            elif job_name == "author":
                run_author_job()
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

    global _written_ids, _enhanced_ids
    _written_ids = _load_existing_ids()
    _enhanced_ids = _load_enhanced_ids()
    logger.info(f"Loaded {len(_written_ids)} existing paper IDs, {len(_enhanced_ids)} already enhanced")

    sched = Scheduler()

    def _signal_handler(sig, frame):
        logger.info("Shutting down...")
        sched.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    sched_thread = threading.Thread(target=sched.start, daemon=True)
    sched_thread.start()
    logger.info("Scheduler started: arXiv every 3h, Crossref/DBLP/S2 every 24h")

    logger.info(f"Starting server on port {args.port}")
    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
