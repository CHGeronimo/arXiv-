from __future__ import annotations

import json
import threading
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from crawler.subs_store import Subscriptions, Journal, Conference, Author

from paper_store import (
    append_paper, find_paper_by_id, load_all_papers,
    reset_ai_chain, DATA_DIR,
)
from jobs import (
    get_job_status, run_arxiv_job, run_crossref_job, run_dblp_job,
    run_s2_job, run_author_job, run_retro_enhance, run_digest_job,
)

app = Flask(__name__, static_folder=".", static_url_path="")

BASE_DIR = Path(".")
FEEDBACK_FILE = BASE_DIR / "feedback.json"
SUBS_PATH = "subscriptions.json"


def _load_subs() -> Subscriptions:
    return Subscriptions.load(SUBS_PATH)


def _save_subs(subs: Subscriptions) -> None:
    subs.save(SUBS_PATH)


# ── Static ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


# ── Papers ────────────────────────────────────────────────────────

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

    papers = load_all_papers()

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
    from paper_store import _written_ids
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


# ── Subscriptions ─────────────────────────────────────────────────

@app.route("/api/subscriptions", methods=["GET"])
def get_subscriptions():
    return jsonify(_load_subs().to_dict())


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
        return jsonify(subs.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── Profile ───────────────────────────────────────────────────────

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
    reset_ai_chain()
    return jsonify(data)


# ── Jobs / Triggers ───────────────────────────────────────────────

@app.route("/api/trigger/<job>", methods=["POST"])
def trigger_job(job: str):
    job_funcs = {
        "arxiv": run_arxiv_job,
        "crossref": run_crossref_job,
        "dblp": run_dblp_job,
        "s2": run_s2_job,
        "author": run_author_job,
    }
    if job not in job_funcs:
        return jsonify({"error": "unknown job"}), 400
    threading.Thread(target=job_funcs[job], daemon=True).start()
    return jsonify({"status": "triggered", "job": job})


@app.route("/api/trigger/enhance", methods=["POST"])
def trigger_enhance():
    threading.Thread(target=run_retro_enhance, daemon=True).start()
    return jsonify({"status": "triggered", "job": "enhance"})


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    return jsonify(get_job_status())


# ── Digest ────────────────────────────────────────────────────────

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


# ── Feedback ──────────────────────────────────────────────────────

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


def _update_profile_from_feedback(paper_id: str, rating: str):
    profile_path = BASE_DIR / "research_profile.json"
    if not profile_path.exists():
        return
    with open(profile_path, "r") as f:
        profile = json.load(f)

    paper = find_paper_by_id(paper_id)
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

    reset_ai_chain()
    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


# ── Author Search ─────────────────────────────────────────────────

@app.route("/api/author/search", methods=["GET"])
def search_author_api():
    query = request.args.get("query", "").strip()
    if not query or len(query) < 2:
        return jsonify({"authors": []})
    from crawler.author_crawler import search_authors, resolve_orcid_to_author
    if query.startswith("0000-") or "orcid.org" in query:
        author = resolve_orcid_to_author(query)
        return jsonify({"authors": [author] if author else []})
    results = search_authors(query, limit=10)
    return jsonify({"authors": results})


# ── BibTeX Export ─────────────────────────────────────────────────

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
