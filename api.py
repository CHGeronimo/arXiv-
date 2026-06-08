from __future__ import annotations

import json
import logging
import logging.handlers
import os
import threading
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from crawler.subs_store import Subscriptions, Journal, Conference, Author

from paper_store import (
    append_paper, find_paper_by_id, load_all_papers,
    reset_ai_chain,
)
from db import get_conn, queue_write, sync_write
from jobs import (
    get_job_status, run_arxiv_job, run_crossref_job, run_dblp_job,
    run_s2_job, run_author_job, run_retro_enhance, run_digest_job,
)


# ── Logging setup ──────────────────────────────────────────────────
_LOG_DIR = os.environ.get("LOG_DIR", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_log_fmt = logging.Formatter(
    "%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(_LOG_DIR, "arxivsci.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setFormatter(_log_fmt)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_log_fmt)

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
# Clear any handlers added by basicConfig or Flask reloader
_root_logger.handlers.clear()
_root_logger.addHandler(_file_handler)
_root_logger.addHandler(_console_handler)
# Prevent basicConfig from adding another StreamHandler
logging.getLogger().propagate = False

_log_path = os.path.abspath(os.path.join(_LOG_DIR, "arxivsci.log"))
_root_logger.info(f"日志文件: {_log_path}")

app = Flask(__name__, static_folder=".", static_url_path="")

SUBS_PATH = "subscriptions.json"
CARD_COLS = ["paper_id", "problem", "method_extracted", "result_extracted", "keywords", "relation_to_profile"]


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
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    source_counts: dict[str, int] = {}
    for row in conn.execute("SELECT source, COUNT(*) as cnt FROM papers GROUP BY source"):
        source_counts[row[0]] = row[1]
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
    if not paper_id:
        return jsonify({"error": "paper_id required"}), 400

    rating = data.get("rating", "")
    relevance = data.get("relevance")
    novelty = data.get("novelty")
    note = data.get("note", "")

    if rating and rating not in ("like", "dislike"):
        return jsonify({"error": "invalid rating"}), 400

    sync_write(
        "INSERT OR REPLACE INTO feedback (paper_id, rating, relevance, novelty, note, updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
        (paper_id, rating or None, relevance, novelty, note or None),
    )
    _update_profile_from_feedback(paper_id, rating)
    return jsonify({"status": "saved"})


@app.route("/api/feedback", methods=["GET"])
def get_feedback():
    conn = get_conn()
    rows = conn.execute("SELECT paper_id, rating, relevance, novelty, note, updated_at FROM feedback").fetchall()
    result = {}
    for row in rows:
        result[row[0]] = {
            "rating": row[1], "relevance": row[2],
            "novelty": row[3], "note": row[4], "updated_at": row[5],
        }
    return jsonify(result)


# ── Knowledge Cards (L1) ──────────────────────────────────────────

@app.route("/api/knowledge-cards", methods=["GET"])
def get_knowledge_cards():
    query = request.args.get("q", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
    except (ValueError, TypeError):
        per_page = 50

    conn = get_conn()
    if query:
        like_q = f"%{query}%"
        rows = conn.execute("""
            SELECT kc.paper_id, kc.problem, kc.method_extracted, kc.result_extracted,
                   kc.keywords, kc.relation_to_profile, kc.extracted_at, p.title, p.source
            FROM knowledge_cards kc JOIN papers p ON kc.paper_id = p.id
            WHERE kc.keywords LIKE ? OR kc.problem LIKE ? OR kc.method_extracted LIKE ? OR kc.result_extracted LIKE ?
            ORDER BY kc.extracted_at DESC
        """, (like_q, like_q, like_q, like_q)).fetchall()
    else:
        rows = conn.execute("""
            SELECT kc.paper_id, kc.problem, kc.method_extracted, kc.result_extracted,
                   kc.keywords, kc.relation_to_profile, kc.extracted_at, p.title, p.source
            FROM knowledge_cards kc JOIN papers p ON kc.paper_id = p.id
            ORDER BY kc.extracted_at DESC
        """).fetchall()

    cards = []
    for row in rows:
        keywords = row["keywords"]
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except (json.JSONDecodeError, TypeError):
                keywords = []
        cards.append({
            "paper_id": row["paper_id"], "problem": row["problem"],
            "method_extracted": row["method_extracted"], "result_extracted": row["result_extracted"],
            "keywords": keywords, "relation_to_profile": row["relation_to_profile"],
            "extracted_at": row["extracted_at"], "title": row["title"], "source": row["source"],
        })

    total = len(cards)
    start = (page - 1) * per_page
    return jsonify({"cards": cards[start:start + per_page], "total": total, "page": page})


@app.route("/api/paper/<paper_id>/card", methods=["GET"])
def get_paper_card(paper_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM knowledge_cards WHERE paper_id = ?", (paper_id,)).fetchone()
    if row is None:
        return jsonify({"card": None})
    keywords = row["keywords"]
    if isinstance(keywords, str):
        try:
            keywords = json.loads(keywords)
        except (json.JSONDecodeError, TypeError):
            keywords = []
    return jsonify({"card": {
        "paper_id": row["paper_id"], "problem": row["problem"],
        "method_extracted": row["method_extracted"], "result_extracted": row["result_extracted"],
        "keywords": keywords, "relation_to_profile": row["relation_to_profile"],
        "extracted_at": row["extracted_at"],
    }})


@app.route("/api/trigger/knowledge-extract", methods=["POST"])
def trigger_knowledge_extract():
    threading.Thread(target=_retro_knowledge_extract, daemon=True).start()
    return jsonify({"status": "triggered", "job": "knowledge-extract"})


def _retro_knowledge_extract():
    from ai.knowledge_extractor import extract_knowledge_card
    from ai.enhance import load_research_profile

    conn = get_conn()
    profile = load_research_profile()
    rows = conn.execute("""
        SELECT a.paper_id, a.tldr, a.motivation, a.method, a.result, a.conclusion, p.title, p.summary
        FROM ai_results a JOIN papers p ON a.paper_id = p.id
        LEFT JOIN knowledge_cards kc ON a.paper_id = kc.paper_id
        WHERE kc.paper_id IS NULL AND a.recommendation != 'ignore'
    """).fetchall()

    logger = logging.getLogger("knowledge-extract")
    logger.info(f"知识卡片抽取: {len(rows)} 篇待处理")

    for i, row in enumerate(rows):
        paper = {
            "id": row["paper_id"], "title": row["title"], "summary": row["summary"],
            "AI": {"tldr": row["tldr"], "motivation": row["motivation"], "method": row["method"], "result": row["result"], "conclusion": row["conclusion"]},
        }
        card = extract_knowledge_card(paper, profile)
        if card:
            queue_write(
                "INSERT OR REPLACE INTO knowledge_cards (paper_id, problem, method_extracted, result_extracted, keywords, relation_to_profile) VALUES (?,?,?,?,?,?)",
                (card["paper_id"], card["problem"], card["method_extracted"], card["result_extracted"], card["keywords"], card["relation_to_profile"]),
            )
        if (i + 1) % 50 == 0:
            logger.info(f"知识卡片进度: {i + 1}/{len(rows)}")
    logger.info(f"知识卡片抽取完成: {len(rows)} 篇已处理")

    if len(rows) > 0:
        from ai.knowledge_clustering import run_clustering
        n = run_clustering()
        logger.info(f"自动触发聚类完成: {n} 个聚类")


# ── Fulltext Analysis ─────────────────────────────────────────────

@app.route("/api/trigger/fulltext-analyze", methods=["POST"])
def trigger_fulltext_analyze():
    threading.Thread(target=_retro_fulltext_analyze, daemon=True).start()
    return jsonify({"status": "triggered", "job": "fulltext-analyze"})


def _retro_fulltext_analyze():
    from ai.fulltext_analyzer import analyze_fulltext
    from ai.enhance import load_research_profile

    conn = get_conn()
    profile = load_research_profile()
    rows = conn.execute("""
        SELECT a.paper_id, a.tldr, a.motivation, a.method, a.result, a.conclusion,
               p.title, p.summary, p.source, p.id
        FROM ai_results a JOIN papers p ON a.paper_id = p.id
        LEFT JOIN fulltext_analysis ft ON a.paper_id = ft.paper_id
        WHERE ft.paper_id IS NULL AND a.recommendation IN ('must-read', 'recommended')
              AND p.source = 'arxiv'
    """).fetchall()

    logger = logging.getLogger("fulltext-analyze")
    logger.info(f"正文深度分析: {len(rows)} 篇待处理")

    analyzed = 0
    for i, row in enumerate(rows):
        paper = {
            "id": row["id"], "source": row["source"],
            "title": row["title"], "summary": row["summary"],
            "AI": {"tldr": row["tldr"], "motivation": row["motivation"],
                   "method": row["method"], "result": row["result"], "conclusion": row["conclusion"]},
        }
        result = analyze_fulltext(paper, profile)
        if result:
            queue_write(
                "INSERT OR REPLACE INTO fulltext_analysis (paper_id, method_implementation, experimental_design, key_results_detail, limitations, reproducibility, relevance_to_profile, analyzed_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (result["paper_id"], result["method_implementation"], result["experimental_design"],
                 result["key_results_detail"], result["limitations"], result["reproducibility"],
                 result["relevance_to_profile"]),
            )
            analyzed += 1
        if (i + 1) % 10 == 0:
            logger.info(f"正文分析进度: {i + 1}/{len(rows)} ({analyzed} 篇已分析)")

    logger.info(f"正文深度分析完成: {analyzed}/{len(rows)}")


@app.route("/api/paper/<paper_id>/fulltext", methods=["GET"])
def get_paper_fulltext(paper_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM fulltext_analysis WHERE paper_id = ?", (paper_id,)).fetchone()
    if row is None:
        return jsonify({"analysis": None})
    return jsonify({"analysis": dict(row)})


# ── Knowledge Graph (L2) ──────────────────────────────────────────

@app.route("/api/knowledge-graph", methods=["GET"])
def get_knowledge_graph():
    conn = get_conn()
    saved = conn.execute("SELECT * FROM knowledge_clusters").fetchall()
    if saved:
        clusters = [dict(r) for r in saved]
    else:
        from ai.knowledge_clustering import compute_clusters
        clusters = compute_clusters()
    nodes, edges = [], []
    for i, c in enumerate(clusters):
        pids = json.loads(c["paper_ids"]) if isinstance(c["paper_ids"], str) else c["paper_ids"]
        kws = json.loads(c["method_keywords"]) if isinstance(c["method_keywords"], str) else c["method_keywords"]
        nodes.append({"id": i, "name": c["cluster_name"], "size": len(pids), "keywords": kws[:5]})
    for i in range(len(clusters)):
        ki = set(json.loads(clusters[i]["method_keywords"]) if isinstance(clusters[i]["method_keywords"], str) else clusters[i]["method_keywords"])
        for j in range(i + 1, len(clusters)):
            kj = set(json.loads(clusters[j]["method_keywords"]) if isinstance(clusters[j]["method_keywords"], str) else clusters[j]["method_keywords"])
            shared = ki & kj
            if shared:
                edges.append({"source": i, "target": j, "weight": len(shared), "keywords": sorted(shared)})
    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/trigger/clustering", methods=["POST"])
def trigger_clustering():
    threading.Thread(target=_run_clustering_job, daemon=True).start()
    return jsonify({"status": "triggered"})


def _run_clustering_job():
    from ai.knowledge_clustering import run_clustering
    run_clustering()


# ── Trend Radar (L3a) ─────────────────────────────────────────────

@app.route("/api/trend-radar", methods=["GET"])
def get_latest_trend():
    conn = get_conn()
    row = conn.execute("SELECT * FROM trend_reports ORDER BY week_start DESC LIMIT 1").fetchone()
    if not row:
        return jsonify({"report": None})
    return jsonify({"report": dict(row)})


@app.route("/api/trend-radar/<week>", methods=["GET"])
def get_trend_by_week(week: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM trend_reports WHERE week_start = ?", (week,)).fetchone()
    if not row:
        return jsonify({"report": None})
    return jsonify({"report": dict(row)})


@app.route("/api/trigger/trend", methods=["POST"])
def trigger_trend():
    from ai.trend_analyzer import generate_trend_report
    threading.Thread(target=generate_trend_report, daemon=True).start()
    return jsonify({"status": "triggered"})


# ── Logs ───────────────────────────────────────────────────────────

@app.route("/api/logs", methods=["GET"])
def get_logs():
    n = min(500, max(1, int(request.args.get("lines", 100))))
    log_path = os.path.join(_LOG_DIR, "arxivsci.log")
    if not os.path.exists(log_path):
        return jsonify({"logs": []})
    with open(log_path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()[-n:]
    return jsonify({"logs": [l.rstrip("\n") for l in lines]})


# ── Idea Check (L3b) ───────────────────────────────────────────────

@app.route("/api/idea-check", methods=["POST"])
def idea_check():
    data = request.get_json() or {}
    idea = data.get("idea", "").strip()
    if not idea:
        return jsonify({"error": "idea is required"}), 400
    from ai.idea_checker import check_idea
    result = check_idea(idea)
    if result is None:
        return jsonify({"error": "analysis failed"}), 500
    return jsonify({"analysis": result})


# ── Category Recommendation ────────────────────────────────────────

ARXIV_CATEGORY_MAP = {
    "cs.AI": "Artificial Intelligence", "cs.AR": "Hardware Architecture",
    "cs.CC": "Computational Complexity", "cs.CE": "Computational Engineering",
    "cs.CG": "Computational Geometry", "cs.CL": "Computation and Language",
    "cs.CR": "Cryptography and Security", "cs.CV": "Computer Vision",
    "cs.CY": "Computers and Society", "cs.DB": "Databases",
    "cs.DC": "Distributed Computing", "cs.DL": "Digital Libraries",
    "cs.DM": "Discrete Mathematics", "cs.DS": "Data Structures and Algorithms",
    "cs.ET": "Emerging Technologies", "cs.FL": "Formal Languages",
    "cs.GL": "General Literature", "cs.GR": "Graphics",
    "cs.GT": "Computer Science and Game Theory", "cs.HC": "Human-Computer Interaction",
    "cs.IR": "Information Retrieval", "cs.IT": "Information Theory",
    "cs.LG": "Machine Learning", "cs.LO": "Logic in Computer Science",
    "cs.MA": "Multiagent Systems", "cs.MM": "Multimedia",
    "cs.MS": "Mathematical Software", "cs.NA": "Numerical Analysis",
    "cs.NE": "Neural and Evolutionary Computing", "cs.NI": "Networking and Internet Architecture",
    "cs.OH": "Other Computer Science", "cs.OS": "Operating Systems",
    "cs.PF": "Performance", "cs.PL": "Programming Languages",
    "cs.RO": "Robotics", "cs.SC": "Symbolic Computation",
    "cs.SD": "Sound", "cs.SE": "Software Engineering",
    "cs.SI": "Social and Information Networks", "cs.SY": "Systems and Control",
    "astro-ph.CO": "Cosmology", "astro-ph.EP": "Earth and Planetary Astrophysics",
    "astro-ph.GA": "Astrophysics of Galaxies", "astro-ph.HE": "High Energy Astrophysical Phenomena",
    "astro-ph.IM": "Astrophysics Instrumentation", "astro-ph.SR": "Solar and Stellar Astrophysics",
    "cond-mat.dis-nn": "Disordered Systems and Neural Networks",
    "cond-mat.mes-hall": "Mesoscale and Nanoscale Physics",
    "cond-mat.mtrl-sci": "Materials Science", "cond-mat.other": "Other Condensed Matter",
    "cond-mat.quant-gas": "Quantum Gases", "cond-mat.soft": "Soft Condensed Matter",
    "cond-mat.stat-mech": "Statistical Mechanics", "cond-mat.str-el": "Strongly Correlated Electrons",
    "cond-mat.supr-con": "Superconductivity",
    "gr-qc": "General Relativity and Quantum Cosmology",
    "hep-ex": "High Energy Physics - Experiment", "hep-lat": "High Energy Physics - Lattice",
    "hep-ph": "High Energy Physics - Phenomenology", "hep-th": "High Energy Physics - Theory",
    "math-ph": "Mathematical Physics",
    "nlin.AO": "Adaptation and Self-Organizing Systems", "nlin.CD": "Cellular Automata",
    "nlin.CG": "Chaotic Dynamics", "nlin.PS": "Pattern Formation and Solitons",
    "nlin.SI": "Exactly Solvable and Integrable Systems",
    "nucl-ex": "Nuclear Experiment", "nucl-th": "Nuclear Theory",
    "physics.acc-ph": "Accelerator Physics", "physics.ao-ph": "Atmospheric and Oceanic Physics",
    "physics.app-ph": "Applied Physics", "physics.atm-clus": "Atomic and Molecular Clusters",
    "physics.atom-ph": "Atomic Physics", "physics.bio-ph": "Biological Physics",
    "physics.chem-ph": "Chemical Physics", "physics.class-ph": "Classical Physics",
    "physics.comp-ph": "Computational Physics", "physics.data-an": "Data Analysis Statistics and Probability",
    "physics.flu-dyn": "Fluid Dynamics", "physics.gen-ph": "General Physics",
    "physics.geo-ph": "Geophysics", "physics.hist-ph": "History and Philosophy of Physics",
    "physics.ins-det": "Instrumentation and Detectors", "physics.med-ph": "Medical Physics",
    "physics.optics": "Optics", "physics.soc-ph": "Physics and Society",
    "physics.ed-ph": "Physics Education", "physics.plasm-ph": "Plasma Physics",
    "physics.pop-ph": "Popular Physics", "physics.space-ph": "Space Physics",
    "quant-ph": "Quantum Physics",
    "math.AG": "Algebraic Geometry", "math.AT": "Algebraic Topology",
    "math.AP": "Analysis of PDEs", "math.CT": "Category Theory",
    "math.CA": "Classical Analysis and ODEs", "math.CO": "Combinatorics",
    "math.AC": "Commutative Algebra", "math.CV": "Complex Variables",
    "math.DG": "Differential Geometry", "math.DS": "Dynamical Systems",
    "math.FA": "Functional Analysis", "math.GM": "General Mathematics",
    "math.GN": "General Topology", "math.GT": "Geometric Topology",
    "math.GR": "Group Theory", "math.HO": "History and Overview",
    "math.IT": "Information Theory", "math.KT": "K-Theory and Homology",
    "math.LO": "Logic", "math.MP": "Mathematical Physics",
    "math.MG": "Metric Geometry", "math.NT": "Number Theory",
    "math.NA": "Numerical Analysis", "math.OA": "Operator Algebras",
    "math.OC": "Optimization and Control", "math.PR": "Probability",
    "math.QA": "Quantum Algebra", "math.RT": "Representation Theory",
    "math.RA": "Rings and Algebras", "math.SP": "Spectral Theory",
    "math.ST": "Statistics Theory", "math.SG": "Symplectic Geometry",
    "q-bio.BM": "Biomolecules", "q-bio.CB": "Cell Behavior",
    "q-bio.GN": "Genomics", "q-bio.MN": "Molecular Networks",
    "q-bio.NC": "Neurons and Cognition", "q-bio.OT": "Other Quantitative Biology",
    "q-bio.PE": "Populations and Evolution", "q-bio.QM": "Quantitative Methods",
    "q-bio.SC": "Subcellular Processes", "q-bio.TO": "Tissues and Organs",
    "q-fin.CP": "Computational Finance", "q-fin.EC": "Economics",
    "q-fin.GN": "General Finance", "q-fin.MF": "Mathematical Finance",
    "q-fin.PM": "Portfolio Management", "q-fin.PR": "Pricing of Securities",
    "q-fin.RM": "Risk Management", "q-fin.ST": "Statistical Finance",
    "q-fin.TR": "Trading and Market Microstructure",
    "stat.AP": "Applications", "stat.CO": "Computation",
    "stat.ML": "Machine Learning", "stat.ME": "Methodology",
    "stat.OT": "Other Statistics", "stat.TH": "Theory",
    "eess.AS": "Audio and Speech Processing", "eess.IV": "Image and Video Processing",
    "eess.SP": "Signal Processing", "eess.SY": "Systems and Control",
    "econ.EM": "Econometrics", "econ.GN": "General Economics",
    "econ.TH": "Theoretical Economics",
}

@app.route("/api/recommend-categories", methods=["POST"])
def recommend_categories():
    """Use LLM to recommend arXiv categories based on research direction."""
    data = request.get_json() or {}
    direction = data.get("direction", "").strip()
    keywords = data.get("keywords", [])
    if not direction and not keywords:
        return jsonify({"error": "direction or keywords required"}), 400

    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel, Field
    import os

    class CategoryRecommendation(BaseModel):
        primary: list[str] = Field(description="5-10 most relevant arXiv category codes (e.g. cs.CV, cs.LG)")
        secondary: list[str] = Field(description="3-5 tangentially relevant category codes")

    cat_list = "\n".join(f"- {code}: {name}" for code, name in ARXIV_CATEGORY_MAP.items())

    prompt = f"""Given a researcher's direction and keywords, select the most relevant arXiv categories. Return your answer as json with "primary" and "secondary" fields.

Research Direction: {direction}
Keywords: {', '.join(keywords) if keywords else 'N/A'}

Available arXiv categories:
{cat_list}

Select categories that would contain papers relevant to this researcher."""

    try:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        llm = ChatOpenAI(model=model_name).with_structured_output(CategoryRecommendation, method="json_mode")
        from langchain_core.prompts import ChatPromptTemplate
        chain = ChatPromptTemplate.from_template(prompt) | llm
        try:
            result = chain.invoke({})
            primary = result.primary if isinstance(result.primary, list) else [result.primary]
            secondary = result.secondary if isinstance(result.secondary, list) else [result.secondary]
        except Exception as parse_err:
            # DeepSeek sometimes returns strings instead of lists; extract manually
            import json, re
            err_str = str(parse_err)
            json_match = re.search(r'\{.*\}', err_str)
            if json_match:
                raw = json.loads(json_match.group())
                primary = raw.get("primary", []) if isinstance(raw.get("primary"), list) else [raw.get("primary", "")] if raw.get("primary") else []
                secondary = raw.get("secondary", []) if isinstance(raw.get("secondary"), list) else [raw.get("secondary", "")] if raw.get("secondary") else []
            else:
                primary, secondary = [], []
        all_codes = set(ARXIV_CATEGORY_MAP.keys())
        primary = [c for c in primary if c in all_codes]
        secondary = [c for c in secondary if c in all_codes]
        return jsonify({"primary": primary, "secondary": secondary})
    except Exception as e:
        logging.getLogger(__name__).error(f"分类推荐失败: {e}")
        return jsonify({"error": str(e)}), 500


def _update_profile_from_feedback(paper_id: str, rating: str):
    """Extract topics from a liked/disliked paper and update research_profile.json.

    Uses LLM to extract 5-7 topic phrases from the paper's AI analysis,
    then appends them to liked_topics or disliked_topics in the profile.
    Keeps the most recent 50 entries per list, deduplicated.
    """
    if rating not in ("like", "dislike"):
        return

    conn = get_conn()
    row = conn.execute(
        "SELECT method, motivation FROM ai_results WHERE paper_id = ?", (paper_id,)
    ).fetchone()
    if not row or (not row["method"] and not row["motivation"]):
        return

    method = row["method"] or ""
    motivation = row["motivation"] or ""
    if not method.strip() and not motivation.strip():
        return

    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=os.environ.get("TOPIC_MODEL", "deepseek-v4-pro"), temperature=0.2)
        resp = llm.invoke(
            f"Extract 5-7 short topic phrases (2-5 words each) from this paper's method and motivation. "
            f"Return ONLY a JSON array of strings, no explanation.\n\n"
            f"Method: {method[:500]}\nMotivation: {motivation[:300]}"
        )
        topics = json.loads(resp.content)
        if not isinstance(topics, list):
            return
        topics = [t.strip() for t in topics if isinstance(t, str) and t.strip()][:7]
    except Exception as e:
        logging.getLogger(__name__).warning(f"主题提取失败 {paper_id}: {e}")
        return

    if not topics:
        return

    profile_path = Path("research_profile.json")
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        return

    key = "liked_topics" if rating == "like" else "disliked_topics"
    current = profile.get(key, [])

    existing_lower = {t.lower() for t in current}
    for t in topics:
        if t.lower() not in existing_lower:
            current.append(t)
            existing_lower.add(t.lower())

    profile[key] = current[-50:]
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    logging.getLogger(__name__).info(f"Profile updated: {key} += {topics}")


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
    entries = []
    for pid in ids:
        paper = find_paper_by_id(pid)
        if paper:
            entries.append(_bibtex_for(paper))
    if not entries:
        return jsonify({"error": "no papers found"}), 404
    return "\n\n".join(entries), 200, {"Content-Type": "application/x-bibtex"}


# ── Paper deletion ───────────────────────────────────────────────

@app.route("/api/paper/<paper_id>", methods=["DELETE"])
def delete_paper(paper_id: str):
    """Delete a single paper and all related data (CASCADE). Records as ignored."""
    conn = get_conn()
    cur = conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
    conn.execute("INSERT OR REPLACE INTO ignored_papers (paper_id, reason) VALUES (?, ?)",
                 (paper_id, "user_deleted"))
    conn.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    logging.getLogger(__name__).info(f"已删除论文 {paper_id}")
    return jsonify({"deleted": paper_id})


@app.route("/api/papers/before/<date_str>", methods=["DELETE"])
def delete_papers_before_date(date_str: str):
    """Delete all papers published before the given date (YYYY-MM-DD). Records as ignored."""
    conn = get_conn()
    ids = [r[0] for r in conn.execute("SELECT id FROM papers WHERE published_date < ?", (date_str,)).fetchall()]
    if ids:
        conn.execute("DELETE FROM papers WHERE published_date < ?", (date_str,))
        conn.executemany("INSERT OR REPLACE INTO ignored_papers (paper_id, reason) VALUES (?, ?)",
                         [(pid, "purge_before_date") for pid in ids])
        conn.commit()
    logging.getLogger(__name__).info(f"已删除 {len(ids)} 篇 {date_str} 之前的论文")
    return jsonify({"deleted_count": len(ids), "before": date_str})


@app.route("/api/papers/purge", methods=["POST"])
def purge_papers():
    """Delete papers matching criteria: skip-rated, older-than-N-days, or specific recommendation."""
    data = request.get_json() or {}
    conn = get_conn()
    count = 0
    ignored_ids = []

    if data.get("skip_rated"):
        rows = conn.execute(
            "SELECT p.id FROM papers p JOIN ai_results a ON p.id = a.paper_id WHERE a.recommendation = 'ignore'"
        ).fetchall()
        ids = [r[0] for r in rows]
        if ids:
            conn.execute("DELETE FROM papers WHERE id IN (" + ",".join("?" * len(ids)) + ")", ids)
            ignored_ids.extend(ids)
            count += len(ids)

    if data.get("older_than_days"):
        cutoff = f"datetime('now', '-{int(data['older_than_days'])} days')"
        rows = conn.execute(f"SELECT id FROM papers WHERE published_date < date({cutoff})").fetchall()
        ids = [r[0] for r in rows]
        if ids:
            conn.execute("DELETE FROM papers WHERE id IN (" + ",".join("?" * len(ids)) + ")", ids)
            ignored_ids.extend(ids)
            count += len(ids)

    if ignored_ids:
        conn.executemany("INSERT OR REPLACE INTO ignored_papers (paper_id, reason) VALUES (?, ?)",
                         [(pid, "purge") for pid in ignored_ids])
        conn.commit()

    conn.commit()
    logging.getLogger(__name__).info(f"Purged {count} papers")
    return jsonify({"purged": count})


# ── Ignored papers audit ─────────────────────────────────────────

@app.route("/api/ignored", methods=["GET"])
def get_ignored_papers():
    """View papers that were filtered out (quick_filter_reject or AI ignore)."""
    conn = get_conn()
    reason = request.args.get("reason", "")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(200, max(1, int(request.args.get("per_page", 50))))

    if reason:
        if reason == 'ai_ignore':
            where = "WHERE reason NOT IN ('quick_filter_reject', 'user_deleted', 'purge', 'purge_before_date')"
            total = conn.execute(f"SELECT COUNT(*) FROM ignored_papers {where}").fetchone()[0]
            rows = conn.execute(
                f"SELECT paper_id, reason, ignored_at FROM ignored_papers {where} ORDER BY ignored_at DESC LIMIT ? OFFSET ?",
                (per_page, (page - 1) * per_page),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) FROM ignored_papers WHERE reason = ?", (reason,)).fetchone()[0]
            rows = conn.execute(
                "SELECT paper_id, reason, ignored_at FROM ignored_papers WHERE reason = ? ORDER BY ignored_at DESC LIMIT ? OFFSET ?",
                (reason, per_page, (page - 1) * per_page),
            ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM ignored_papers").fetchone()[0]
        rows = conn.execute(
            "SELECT paper_id, reason, ignored_at FROM ignored_papers ORDER BY ignored_at DESC LIMIT ? OFFSET ?",
            (per_page, (page - 1) * per_page),
        ).fetchall()

    # Group by category for stats
    stats = conn.execute("""
        SELECT
            CASE
                WHEN reason = 'quick_filter_reject' THEN 'quick_filter_reject'
                WHEN reason IN ('user_deleted', 'purge', 'purge_before_date') THEN reason
                ELSE 'ai_ignore'
            END as category,
            COUNT(*) as cnt
        FROM ignored_papers GROUP BY category ORDER BY cnt DESC
    """).fetchall()

    return jsonify({
        "ignored": [{"paper_id": r[0], "reason": r[1], "ignored_at": r[2]} for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "stats": [{"reason": s[0], "count": s[1]} for s in stats],
    })


@app.route("/api/ignored/stats", methods=["GET"])
def get_ignored_stats():
    """Summary stats of ignored papers."""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM ignored_papers").fetchone()[0]
    stats = conn.execute("""
        SELECT
            CASE
                WHEN reason = 'quick_filter_reject' THEN 'quick_filter_reject'
                WHEN reason IN ('user_deleted', 'purge', 'purge_before_date') THEN reason
                ELSE 'ai_ignore'
            END as category,
            COUNT(*) as cnt
        FROM ignored_papers GROUP BY category ORDER BY cnt DESC
    """).fetchall()
    return jsonify({
        "total_ignored": total,
        "by_reason": [{"reason": s[0], "count": s[1]} for s in stats],
    })
