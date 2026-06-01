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
from db import get_conn, queue_write

logger = logging.getLogger("paper_store")

AI_LANGUAGE = "Chinese"

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
    "venue", "acceptance", "citation_count", "version",
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

def append_paper(paper: Paper, enhance: bool = False) -> bool:
    """Insert a paper into the store, optionally running AI enhancement.

    Args:
        paper: Paper dataclass instance.
        enhance: If True, run quick filter and AI enhancement.

    Returns:
        True if the paper was newly inserted, False if it already existed.
    """
    if _paper_exists(paper.id):
        return False

    paper_dict = json.loads(paper.to_jsonl())

    if enhance:
        # If AI result already exists, just insert the paper row
        if _ai_exists(paper.id):
            _insert_paper_row(paper_dict)
            return True

        # Quick relevance filter
        quick_chain = get_quick_chain()
        chain, profile = get_ai_chain()
        if not quick_filter_paper(paper_dict, quick_chain, profile):
            ai_default = {
                "tldr": "", "motivation": "", "method": "", "result": "",
                "conclusion": "",
                "title_zh": "", "summary_zh": "",
                "quality_score": 0, "relevance_score": 0,
                "recommendation": "skip",
                "skip_reason": "Filtered by quick relevance check",
            }
            _insert_paper_row(paper_dict)
            _insert_ai_row(paper.id, ai_default)
            return True

        # Full enhancement
        try:
            enhanced = enhance_single(paper_dict, chain, profile, AI_LANGUAGE)
            if enhanced:
                ai_data = enhanced.get("AI", enhanced)
                _insert_paper_row(paper_dict)
                _insert_ai_row(paper.id, ai_data)
                try:
                    _insert_knowledge_card(paper.id, enhanced)
                except Exception as e:
                    logger.warning(f"Knowledge card extraction failed for {paper.id}: {e}")
                return True
        except Exception as e:
            logger.warning(f"AI enhance failed for {paper.id}: {e}")

    # No enhance, or enhance failed — insert paper row only
    _insert_paper_row(paper_dict)
    return True


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

    return d


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
