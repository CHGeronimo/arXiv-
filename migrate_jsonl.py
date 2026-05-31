"""One-time JSONL to SQLite auto-migration.

Migrates raw and AI-enhanced JSONL files from data/ into the papers
and ai_results tables.  Idempotent: re-running on an already-migrated
database is a no-op (needs_migration returns False).

Usage:
    from db import init_db
    init_db()
    from migrate_jsonl import run_migration
    count = run_migration()
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from db import get_conn

logger = logging.getLogger("migrate_jsonl")

DATA_DIR = Path("data")

# Columns in the papers table (excluding created_at which has a default)
PAPER_COLUMNS = [
    "id", "source", "title", "summary",
    "authors", "categories",
    "doi", "published_date", "url", "pdf",
    "publisher", "journal_title", "issn",
    "comment", "article_type",
    "venue", "acceptance", "citation_count", "version",
]

# Fields stored as JSON strings
_JSON_FIELDS = {"authors", "categories", "issn"}

# Columns in the ai_results table (excluding enhanced_at which has a default)
AI_COLUMNS = [
    "paper_id",
    "tldr", "motivation", "method", "result", "conclusion",
    "title_zh", "summary_zh",
    "quality_score", "relevance_score",
    "recommendation", "skip_reason",
]


def needs_migration() -> bool:
    """Return True if JSONL files exist but the papers table is empty."""
    jsonl_files = list(DATA_DIR.glob("*.jsonl"))
    if not jsonl_files:
        return False

    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    return count == 0


def _insert_paper(conn, p: dict) -> None:
    """INSERT OR IGNORE a paper dict into the papers table.

    JSON-encodes authors, categories, and issn fields.
    Missing keys default to None.
    """
    row = {}
    for col in PAPER_COLUMNS:
        val = p.get(col)
        if col in _JSON_FIELDS and val is not None:
            val = json.dumps(val, ensure_ascii=False)
        row[col] = val

    placeholders = ", ".join(f":{c}" for c in PAPER_COLUMNS)
    cols = ", ".join(PAPER_COLUMNS)
    sql = f"INSERT OR IGNORE INTO papers ({cols}) VALUES ({placeholders})"
    conn.execute(sql, row)


def _upsert_ai(conn, paper_id: str, ai: dict) -> None:
    """INSERT OR REPLACE an AI result row for the given paper_id."""
    row = {"paper_id": paper_id}
    for col in AI_COLUMNS[1:]:  # skip paper_id, already set
        row[col] = ai.get(col)

    placeholders = ", ".join(f":{c}" for c in AI_COLUMNS)
    cols = ", ".join(AI_COLUMNS)
    sql = f"INSERT OR REPLACE INTO ai_results ({cols}) VALUES ({placeholders})"
    conn.execute(sql, row)


def _load_jsonl(path: Path) -> list[dict]:
    """Load all lines from a JSONL file, skipping blank/malformed lines."""
    papers: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                papers.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"Skipping malformed line {line_no} in {path.name}")
    return papers


def run_migration() -> int:
    """Migrate all JSONL data into SQLite. Returns count of papers migrated.

    Phase 1: Process raw JSONL files (no _AI_ in filename).
    Phase 2: Process AI-enhanced JSONL files — extract AI sub-dict,
              insert paper row + AI row (or upsert AI if paper already seen).
    Commits after each file for bulk speed.
    """
    conn = get_conn()
    seen_ids: set[str] = set()
    total_inserted = 0

    # Collect and sort JSONL files
    all_jsonl = sorted(DATA_DIR.glob("*.jsonl"))
    raw_files = [f for f in all_jsonl if "_AI_" not in f.name]
    ai_files = [f for f in all_jsonl if "_AI_" in f.name]

    # Phase 1: Raw JSONL files
    for path in raw_files:
        logger.info(f"Phase 1: processing {path.name}")
        papers = _load_jsonl(path)
        file_count = 0
        conn.execute("BEGIN IMMEDIATE")
        for p in papers:
            pid = p.get("id")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            _insert_paper(conn, p)
            file_count += 1
        conn.commit()
        total_inserted += file_count
        logger.info(f"  Inserted {file_count} papers from {path.name}")

    # Phase 2: AI-enhanced JSONL files
    for path in ai_files:
        logger.info(f"Phase 2: processing {path.name}")
        papers = _load_jsonl(path)
        file_papers = 0
        file_ai = 0
        conn.execute("BEGIN IMMEDIATE")
        for p in papers:
            pid = p.get("id")
            if not pid:
                continue

            ai = p.pop("AI", None)

            if pid not in seen_ids:
                seen_ids.add(pid)
                _insert_paper(conn, p)
                file_papers += 1
            # else: paper already inserted, only handle AI

            if ai:
                _upsert_ai(conn, pid, ai)
                file_ai += 1

        conn.commit()
        total_inserted += file_papers
        logger.info(
            f"  Inserted {file_papers} papers + {file_ai} AI results from {path.name}"
        )

    logger.info(f"Migration complete: {total_inserted} papers, {len(seen_ids)} unique IDs")
    return total_inserted
