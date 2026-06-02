"""Paper storage backed by SQLite via db module.

Replaces the previous JSONL-based storage with SQLite queries.
AI chain management remains unchanged.
"""

from __future__ import annotations

import json
import logging

from ai.enhance import enhance_single, build_chain, load_research_profile
from ai.knowledge_extractor import extract_knowledge_card
from ai.quick_filter import build_quick_filter, quick_filter_paper
from crawler.models import Paper
from db import get_conn, queue_write, ignore_paper, is_ignored
from ccf_map import CCF_MAP

logger = logging.getLogger("paper_store")

AI_LANGUAGE = "Chinese"

_SKIP_REASON_MAP = {
    "low_relevance": "low_relevance",
    "weak_method": "weak_method",
    "no_empirical": "no_empirical",
    "domain_mismatch": "domain_mismatch",
    "poor_quality": "poor_quality",
}

# ---------------------------------------------------------------------------
# AI chain lazy init (unchanged from original)
# ---------------------------------------------------------------------------

_ai_chain = None
_ai_profile = None
_quick_chain = None


def get_ai_chain():
    """Lazy-init the main AI enhancement chain and research profile."""
    global _ai_chain, _ai_profile
    if _ai_chain is None:
        import os
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        _ai_chain = build_chain(model_name)
        _ai_profile = load_research_profile()
        logger.info(f"AI chain initialized: {model_name}")
    return _ai_chain, _ai_profile


def reset_ai_chain():
    """Clear cached AI chain and profile so they are rebuilt on next use."""
    global _ai_chain, _ai_profile
    _ai_chain = None
    _ai_profile = None


def get_quick_chain():
    """Lazy-init the quick relevance filter chain."""
    global _quick_chain
    if _quick_chain is None:
        _quick_chain = build_quick_filter()
        logger.info("Quick filter chain initialized")
    return _quick_chain


# ---------------------------------------------------------------------------
# Column definitions (must match db.py schema)
# ---------------------------------------------------------------------------

PAPER_COLS = [
    "id", "source", "title", "summary",
    "authors", "categories",
    "doi", "published_date", "url", "pdf",
    "publisher", "journal_title", "issn",
    "comment", "article_type",
    "venue", "acceptance", "citation_count", "ccf_tier", "version",
]

AI_COLS = [
    "paper_id",
    "tldr", "motivation", "method", "result", "conclusion",
    "title_zh", "summary_zh",
    "quality_score", "relevance_score",
    "recommendation", "skip_reason",
]

_JSON_FIELDS = {"authors", "categories", "issn"}


# ---------------------------------------------------------------------------
# Existence checks
# ---------------------------------------------------------------------------

def _paper_exists(paper_id: str) -> bool:
    """Return True if a paper with the given id already exists."""
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM papers WHERE id = ?", (paper_id,)
    ).fetchone()
    return row is not None


def _ai_exists(paper_id: str) -> bool:
    """Return True if an AI result exists for the given paper_id."""
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM ai_results WHERE paper_id = ?", (paper_id,)
    ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Insert helpers (async via queue_write)
# ---------------------------------------------------------------------------

def _insert_paper_row(p: dict) -> None:
    """Queue an INSERT OR IGNORE for a paper dict.

    JSON-encodes authors, categories, and issn fields.
    Missing keys default to None.
    """
    row: dict = {}
    for col in PAPER_COLS:
        val = p.get(col)
        if col in _JSON_FIELDS and val is not None:
            val = json.dumps(val, ensure_ascii=False)
        row[col] = val

    if not row.get("ccf_tier"):
        row["ccf_tier"] = _match_ccf(row.get("venue", ""), row.get("journal_title", "")) or None

    placeholders = ", ".join(f":{c}" for c in PAPER_COLS)
    cols = ", ".join(PAPER_COLS)
    sql = f"INSERT OR IGNORE INTO papers ({cols}) VALUES ({placeholders})"
    queue_write(sql, tuple(row[c] for c in PAPER_COLS))


def _insert_ai_row(paper_id: str, ai: dict) -> None:
    """Queue an INSERT OR REPLACE for an AI result row."""
    row: dict = {"paper_id": paper_id}
    for col in AI_COLS[1:]:  # skip paper_id, already set
        row[col] = ai.get(col)

    placeholders = ", ".join(f":{c}" for c in AI_COLS)
    cols = ", ".join(AI_COLS)
    sql = f"INSERT OR REPLACE INTO ai_results ({cols}) VALUES ({placeholders})"
    queue_write(sql, tuple(row[c] for c in AI_COLS))


CARD_COLS = ["paper_id", "problem", "method_extracted", "result_extracted", "keywords", "relation_to_profile"]


def _insert_knowledge_card(paper_id: str, paper: dict) -> None:
    card = extract_knowledge_card(paper)
    if card is None:
        return
    cols = ", ".join(CARD_COLS)
    placeholders = ", ".join(f":{c}" for c in CARD_COLS)
    sql = f"INSERT OR REPLACE INTO knowledge_cards ({cols}) VALUES ({placeholders})"
    queue_write(sql, tuple(card.get(c) for c in CARD_COLS))


# ---------------------------------------------------------------------------
# Core append
# ---------------------------------------------------------------------------

def append_paper(paper: Paper, enhance: bool = False) -> str | None:
    """Insert a paper into the store, optionally running AI enhancement.

    Args:
        paper: Paper dataclass instance.
        enhance: If True, run quick filter and AI enhancement.

    Returns:
        "written" if inserted, or the rejection reason string:
        "exists", "ignored", "filter_reject", "ai_reject", "error".
    """
    if _paper_exists(paper.id):
        return "exists"
    if is_ignored(paper.id):
        return "ignored"

    paper_dict = json.loads(paper.to_jsonl())

    if enhance:
        if _ai_exists(paper.id):
            _insert_paper_row(paper_dict)
            return "written"

        quick_chain = get_quick_chain()
        chain, profile = get_ai_chain()
        if not quick_filter_paper(paper_dict, quick_chain, profile):
            logger.debug(f"Quick filter rejected: {paper.id}")
            ignore_paper(paper.id, "quick_filter_reject")
            return "filter_reject"

        try:
            enhanced = enhance_single(paper_dict, chain, profile, AI_LANGUAGE)
            if enhanced:
                ai_data = enhanced.get("AI", enhanced)
                if ai_data.get("recommendation") in ("skip", "ignore"):
                    raw_reason = ai_data.get("skip_reason", "") or "low_relevance"
                    reason = _SKIP_REASON_MAP.get(raw_reason, "low_relevance")
                    ignore_paper(paper.id, reason)
                    logger.debug(f"AI rated ignore ({reason}): {paper.id}")
                    return "ai_reject"
                _insert_paper_row(paper_dict)
                _insert_ai_row(paper.id, ai_data)
                try:
                    _insert_knowledge_card(paper.id, enhanced)
                except Exception as e:
                    logger.warning(f"Knowledge card failed for {paper.id}: {e}")
                return "written"
        except Exception as e:
            logger.warning(f"AI enhance failed for {paper.id}: {e}")
            return "error"

    _insert_paper_row(paper_dict)
    return "written"


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a joined papers+ai_results row to a dict.

    Paper fields are flattened; AI fields are nested under an "AI" key
    only if at least one AI field has a non-default value.
    """
    import sqlite3

    d: dict = {}
    for col in PAPER_COLS:
        val = row[col]
        if col in _JSON_FIELDS and val is not None:
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
        d[col] = val

    # Build AI sub-dict only if there is meaningful AI data
    has_ai = False
    ai: dict = {}
    for col in AI_COLS[1:]:  # skip paper_id
        val = row[col]
        ai[col] = val
        # Non-default means some AI processing happened
        if val is not None and val != "" and val != 0:
            has_ai = True

    if has_ai:
        d["AI"] = ai

    ccf = d.get("ccf_tier")
    if not ccf:
        ccf = _match_ccf(d.get("venue", ""), d.get("journal_title", ""))
    d["ccf_tier"] = ccf
    return d


_IEEE_ABBREV = {
    # Maps IEEE/ACM full journal names to CCF_MAP abbreviations.
    # CCF_MAP uses abbreviated keys (e.g. "IEEE TPAMI"), but crawled papers
    # have full names (e.g. "IEEE Transactions on Pattern Analysis...").
    "IEEE TRANSACTIONS ON PATTERN ANALYSIS AND MACHINE INTELLIGENCE": "IEEE TPAMI",
    "IEEE TRANSACTIONS ON KNOWLEDGE AND DATA ENGINEERING": "IEEE TKDE",
    "IEEE TRANSACTIONS ON INFORMATION FORENSICS AND SECURITY": "IEEE TIFS",
    "IEEE TRANSACTIONS ON SOFTWARE ENGINEERING": "IEEE TSE",
    "IEEE TRANSACTIONS ON COMPUTERS": "TC",
    "IEEE TRANSACTIONS ON PARALLEL AND DISTRIBUTED SYSTEMS": "IEEE TPDS",
    "IEEE TRANSACTIONS ON IMAGE PROCESSING": "IEEE TIP",
    "IEEE TRANSACTIONS ON NEURAL NETWORKS AND LEARNING SYSTEMS": "IEEE TNNLS",
    "IEEE TRANSACTIONS ON MULTIMEDIA": "IEEE TMM",
    "IEEE TRANSACTIONS ON MOBILE COMPUTING": "IEEE TMC",
    "IEEE TRANSACTIONS ON COMMUNICATIONS": "IEEE TCOMM",
    "IEEE TRANSACTIONS ON WIRELESS COMMUNICATIONS": "IEEE TWC",
    "IEEE TRANSACTIONS ON INFORMATION THEORY": "IEEE TIT",
    "IEEE TRANSACTIONS ON VISUALIZATION AND COMPUTER GRAPHICS": "IEEE TVCG",
    "IEEE TRANSACTIONS ON DEPENDABLE AND SECURE COMPUTING": "IEEE TDSC",
    "IEEE TRANSACTIONS ON CLOUD COMPUTING": "IEEE TCC",
    "IEEE TRANSACTIONS ON CYBERNETICS": "IEEE TCYB",
    "IEEE TRANSACTIONS ON INTELLIGENT TRANSPORTATION SYSTEMS": "IEEE TITS",
    "IEEE TRANSACTIONS ON GEOSCIENCE AND REMOTE SENSING": "IEEE TGRS",
    "IEEE TRANSACTIONS ON ROBOTICS": "IEEE TRO",
    "IEEE TRANSACTIONS ON AUTOMATION SCIENCE AND ENGINEERING": "IEEE TASE",
    "IEEE TRANSACTIONS ON COMPUTER-AIDED DESIGN OF INTEGRATED CIRCUITS AND SYSTEMS": "IEEE TCAD",
    "IEEE TRANSACTIONS ON CIRCUITS AND SYSTEMS FOR VIDEO TECHNOLOGY": "IEEE TCSVT",
    "IEEE TRANSACTIONS ON SIGNAL PROCESSING": "IEEE TSP",
    "IEEE TRANSACTIONS ON FUZZY SYSTEMS": "IEEE TFS",
    "IEEE TRANSACTIONS ON EVOLUTIONARY COMPUTATION": "IEEE TEC",
    "IEEE TRANSACTIONS ON INTELLIGENT SYSTEMS": "IEEE TIS",
    "IEEE TRANSACTIONS ON SERVICES COMPUTING": "IEEE TSC",
    "IEEE TRANSACTIONS ON NETWORK AND SERVICE MANAGEMENT": "IEEE TNSM",
    "IEEE TRANSACTIONS ON INSTRUMENTATION AND MEASUREMENT": "IEEE TIM",
    "IEEE INTERNET OF THINGS JOURNAL": "IEEE TIOT",
    "IEEE JOURNAL ON SELECTED AREAS IN COMMUNICATIONS": "IEEE JSAC",
    "IEEE ACCESS": "IEEE ACCESS",
    "IEEE SENSORS JOURNAL": "IEEE SENSORS JOURNAL",
    "ACM TRANSACTIONS ON GRAPHICS": "ACM TOG",
    "ACM TRANSACTIONS ON INFORMATION SYSTEMS": "ACM TOIS",
    "ACM TRANSACTIONS ON DATABASE SYSTEMS": "ACM TODS",
    "ACM TRANSACTIONS ON COMPUTER-HUMAN INTERACTION": "ACM TOCHI",
    "ACM TRANSACTIONS ON PROGRAMMING LANGUAGES AND SYSTEMS": "ACM TOPLAS",
    "ACM TRANSACTIONS ON SOFTWARE ENGINEERING AND METHODOLOGY": "ACM TOSEM",
    "ACM TRANSACTIONS ON MATHEMATICAL SOFTWARE": "ACM TOMS",
    "ACM TRANSACTIONS ON MULTIMEDIA COMPUTING COMMUNICATIONS AND APPLICATIONS": "ACM TOMM",
    "ACM TRANSACTIONS ON THE WEB": "ACM TWEB",
    "ACM TRANSACTIONS ON SENSOR NETWORKS": "ACM TOSN",
    "ACM TRANSACTIONS ON ALGORITHMS": "ACM TALG",
    "ACM TRANSACTIONS ON EMBEDDED COMPUTING SYSTEMS": "ACM TECS",
    "ACM TRANSACTIONS ON COMPUTER SYSTEMS": "ACM TOCS",
    "ACM TRANSACTIONS ON INTELLIGENT SYSTEMS AND TECHNOLOGY": "ACM TIST",
    "ACM TRANSACTIONS ON ARCHITECTURE AND CODE OPTIMIZATION": "ACM TACO",
    "ACM TRANSACTIONS ON PRIVACY AND SECURITY": "ACM TOPS",
    "ACM TRANSACTIONS ON RECONFIGURABLE TECHNOLOGY AND SYSTEMS": "ACM TRETS",
    "ACM COMPUTING SURVEYS": "ACM CSUR",
    "ACM TRANSACTIONS ON GRAPHICS": "TOG",
    "IEEE TRANSACTIONS ON INTELLIGENT TRANSPORTATION SYSTEMS": "TITS",
    "IEEE TRANSACTIONS ON MOBILE COMPUTING": "TMC",
    "IEEE TRANSACTIONS ON GEOSCIENCE AND REMOTE SENSING": "TGRS",
}


def _normalize_venue(field: str) -> str:
    """Normalize IEEE/ACM full journal names to CCF standard abbreviations.

    Tries exact match first, then substring containment for long names.
    """
    up = field.upper().rstrip(".")
    if up in _IEEE_ABBREV:
        return _IEEE_ABBREV[up]
    # Partial match for long IEEE/ACM names
    for full, abbrev in _IEEE_ABBREV.items():
        if full in up or up in full:
            return abbrev
    return field


def _match_ccf(venue: str, journal_title: str) -> str:
    """Match venue or journal_title against CCF_MAP using 4 strategies:

    1. Direct key lookup in CCF_MAP
    2. Normalize IEEE/ACM full names to abbreviations, then lookup
    3. Strip year suffix (e.g. "CVPR 2025" -> "CVPR")
    4. Substring match for keys >= 4 chars to handle partial venue names
    """
    import re
    for field in [venue, journal_title]:
        if not field:
            continue
        if field in CCF_MAP:
            return CCF_MAP[field]["tier"]
        norm = _normalize_venue(field)
        if norm != field and norm in CCF_MAP:
            return CCF_MAP[norm]["tier"]
        # Strip year suffix (e.g. "CVPR 2025" -> "CVPR")
        stripped = re.sub(r'\s+\d{4}$', '', field).strip()
        if stripped in CCF_MAP:
            return CCF_MAP[stripped]["tier"]
        # Keyword match: >= 4 chars substring or word-boundary for shorter keys
        upper = field.upper()
        for key, val in CCF_MAP.items():
            ku = key.upper()
            if len(ku) >= 4 and ku in upper:
                return val["tier"]
    return ""


def find_paper_by_id(paper_id: str) -> dict | None:
    """Look up a paper by id, including AI results if available.

    Returns a dict with paper fields plus an "AI" sub-dict if AI data
    exists, or None if the paper is not found.
    """
    conn = get_conn()

    paper_cols = ", ".join(f"p.{c}" for c in PAPER_COLS)
    ai_cols = ", ".join(f"a.{c}" for c in AI_COLS[1:])  # skip paper_id
    sql = (
        f"SELECT {paper_cols}, {ai_cols} "
        f"FROM papers p LEFT JOIN ai_results a ON p.id = a.paper_id "
        f"WHERE p.id = ?"
    )
    row = conn.execute(sql, (paper_id,)).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def load_all_papers() -> list[dict]:
    """Load all papers with their AI results, newest first.

    Returns a list of dicts with paper fields and optional "AI" sub-dict.
    """
    conn = get_conn()

    paper_cols = ", ".join(f"p.{c}" for c in PAPER_COLS)
    ai_cols = ", ".join(f"a.{c}" for c in AI_COLS[1:])
    sql = (
        f"SELECT {paper_cols}, {ai_cols} "
        f"FROM papers p LEFT JOIN ai_results a ON p.id = a.paper_id "
        f"ORDER BY p.created_at DESC"
    )
    rows = conn.execute(sql).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_written_count() -> int:
    """Return the total number of papers in the store."""
    conn = get_conn()
    return conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
