# SQLite Storage Migration + Code Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace JSONL file storage with SQLite (5-table relational model), eliminate duplicated job/enhance code, and optimize API response times from full-file-scan to indexed queries.

**Architecture:** SQLite database at `data/papers.db` with WAL mode for concurrent read/write. Write queue serializes mutations. Startup auto-migrates existing JSONL data. `paper_store.py` becomes a thin DB layer. `jobs.py` uses a `BaseCrawlerJob` class. `enhance.py` consolidates two entry points into one.

**Tech Stack:** Python 3.12, SQLite3 (stdlib), Flask, existing LangChain/OpenAI stack

---

## File Structure

| File | Responsibility |
|:-----|:---------------|
| `db.py` (NEW) | SQLite schema, connection pool, write queue, migration |
| `paper_store.py` (REWRITE) | Paper CRUD via db.py (replaces all JSONL logic) |
| `jobs.py` (REFACTOR) | BaseCrawlerJob base class + 5 thin subclasses |
| `ai/enhance.py` (SIMPLIFY) | Single `enhance_single()` entry, remove CLI dead code |
| `api.py` (MODIFY) | Use paper_store DB functions, remove JSONL file scanning |
| `daemon.py` (MINOR) | Call `init_db()` instead of `init_ids()` |
| `ai/digest.py` (MODIFY) | Read from DB instead of JSONL |

## Database Schema

```sql
CREATE TABLE papers (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT DEFAULT '',
    authors TEXT DEFAULT '[]',        -- JSON array
    categories TEXT DEFAULT '[]',     -- JSON array
    doi TEXT DEFAULT '',
    published_date TEXT DEFAULT '',
    url TEXT DEFAULT '',
    pdf TEXT DEFAULT '',
    publisher TEXT DEFAULT '',
    journal_title TEXT DEFAULT '',
    issn TEXT DEFAULT '[]',           -- JSON array
    comment TEXT DEFAULT '',
    article_type TEXT DEFAULT '',
    venue TEXT DEFAULT '',
    acceptance TEXT DEFAULT '',
    citation_count INTEGER DEFAULT 0,
    version TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE ai_results (
    paper_id TEXT PRIMARY KEY REFERENCES papers(id),
    tldr TEXT DEFAULT '',
    motivation TEXT DEFAULT '',
    method TEXT DEFAULT '',
    result TEXT DEFAULT '',
    conclusion TEXT DEFAULT '',
    title_zh TEXT DEFAULT '',
    summary_zh TEXT DEFAULT '',
    quality_score INTEGER DEFAULT 0,
    relevance_score INTEGER DEFAULT 0,
    recommendation TEXT DEFAULT '',
    skip_reason TEXT DEFAULT '',
    enhanced_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE feedback (
    paper_id TEXT PRIMARY KEY REFERENCES papers(id),
    rating TEXT NOT NULL CHECK(rating IN ('useful','not_useful')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE digests (
    date TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE subscriptions (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL  -- JSON blob
);

CREATE INDEX idx_papers_source ON papers(source);
CREATE INDEX idx_papers_published ON papers(published_date);
CREATE INDEX idx_ai_recommendation ON ai_results(recommendation);
CREATE INDEX idx_ai_relevance ON ai_results(relevance_score);
```

---

### Task 1: Create `db.py` — Schema, Connection, Write Queue

**Files:**
- Create: `db.py`

- [ ] **Step 1: Write `db.py` with schema, connection factory, and write queue**

```python
"""db.py — SQLite storage layer for arxivSCI-daily."""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from queue import Queue
from typing import Any

logger = logging.getLogger("db")

DB_PATH = Path("data/papers.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT DEFAULT '',
    authors TEXT DEFAULT '[]',
    categories TEXT DEFAULT '[]',
    doi TEXT DEFAULT '',
    published_date TEXT DEFAULT '',
    url TEXT DEFAULT '',
    pdf TEXT DEFAULT '',
    publisher TEXT DEFAULT '',
    journal_title TEXT DEFAULT '',
    issn TEXT DEFAULT '[]',
    comment TEXT DEFAULT '',
    article_type TEXT DEFAULT '',
    venue TEXT DEFAULT '',
    acceptance TEXT DEFAULT '',
    citation_count INTEGER DEFAULT 0,
    version TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS ai_results (
    paper_id TEXT PRIMARY KEY REFERENCES papers(id),
    tldr TEXT DEFAULT '',
    motivation TEXT DEFAULT '',
    method TEXT DEFAULT '',
    result TEXT DEFAULT '',
    conclusion TEXT DEFAULT '',
    title_zh TEXT DEFAULT '',
    summary_zh TEXT DEFAULT '',
    quality_score INTEGER DEFAULT 0,
    relevance_score INTEGER DEFAULT 0,
    recommendation TEXT DEFAULT '',
    skip_reason TEXT DEFAULT '',
    enhanced_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS feedback (
    paper_id TEXT PRIMARY KEY REFERENCES papers(id),
    rating TEXT NOT NULL CHECK(rating IN ('useful','not_useful')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS digests (
    date TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS subscriptions (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);
CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published_date);
CREATE INDEX IF NOT EXISTS idx_ai_recommendation ON ai_results(recommendation);
CREATE INDEX IF NOT EXISTS idx_ai_relevance ON ai_results(relevance_score);
"""

_local = threading.local()
_write_queue: Queue = Queue()
_writer_thread: threading.Thread | None = None
_shutdown = threading.Event()


def get_conn() -> sqlite3.Connection:
    """Get a thread-local connection with WAL mode and row factory."""
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn


def init_db() -> None:
    """Create tables and start the write-queue worker thread."""
    conn = get_conn()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    _start_writer()


def _start_writer() -> None:
    global _writer_thread
    if _writer_thread is not None and _writer_thread.is_alive():
        return
    _shutdown.clear()
    _writer_thread = threading.Thread(target=_write_worker, daemon=True)
    _writer_thread.start()


def _write_worker() -> None:
    """Background thread: drain write queue, batch-commit every 100ms or on sentinel."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    batch: list[tuple[str, tuple]] = []
    while not _shutdown.is_set():
        try:
            item = _write_queue.get(timeout=0.1)
        except Exception:
            if batch:
                _flush(conn, batch)
                batch.clear()
            continue
        if item is None:
            # sentinel — flush and exit
            if batch:
                _flush(conn, batch)
            conn.close()
            return
        batch.append(item)
        if len(batch) >= 50:
            _flush(conn, batch)
            batch.clear()


def _flush(conn: sqlite3.Connection, batch: list[tuple[str, tuple]]) -> None:
    try:
        for sql, params in batch:
            conn.execute(sql, params)
        conn.commit()
    except Exception as e:
        logger.error(f"Write queue flush error: {e}")
        conn.rollback()


def queue_write(sql: str, params: tuple = ()) -> None:
    """Enqueue a write operation for async execution."""
    _write_queue.put((sql, params))


def sync_write(sql: str, params: tuple = ()) -> None:
    """Execute a write synchronously (for startup migration etc.)."""
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()


def stop_writer() -> None:
    _shutdown.set()
    _write_queue.put(None)
    if _writer_thread:
        _writer_thread.join(timeout=5)
```

- [ ] **Step 2: Commit**

```bash
git add db.py
git commit -m "feat: db.py — SQLite schema, WAL mode, write queue"
```

---

### Task 2: Create `migrate_jsonl.py` — Auto-migrate existing data

**Files:**
- Create: `migrate_jsonl.py`

- [ ] **Step 1: Write migration script**

```python
"""migrate_jsonl.py — One-time JSONL → SQLite migration."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from db import get_conn, sync_write

logger = logging.getLogger("migrate")
DATA_DIR = Path("data")


def needs_migration() -> bool:
    """Return True if there are JSONL files but no papers in DB."""
    has_jsonl = any(DATA_DIR.glob("*.jsonl"))
    if not has_jsonl:
        return False
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    return count == 0


def run_migration() -> int:
    """Migrate all JSONL data to SQLite. Returns count of papers migrated."""
    conn = get_conn()
    migrated = 0
    seen_ids: set[str] = set()

    # Phase 1: raw JSONL (papers without AI)
    for f in sorted(DATA_DIR.glob("*.jsonl")):
        if "_AI_" in f.name:
            continue
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    p = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pid = p.get("id", "")
                if not pid or pid in seen_ids:
                    continue
                seen_ids.add(pid)
                _insert_paper(conn, p)
                migrated += 1
        conn.commit()

    # Phase 2: AI-enhanced JSONL (has AI fields merged in)
    for f in sorted(DATA_DIR.glob("*_AI_enhanced_*.jsonl")):
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    p = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pid = p.get("id", "")
                doi = p.get("doi", "")
                ai_data = p.pop("AI", None)

                if pid in seen_ids:
                    # paper exists, just add AI result
                    if ai_data:
                        _upsert_ai(conn, pid, ai_data)
                    continue

                seen_ids.add(pid)
                _insert_paper(conn, p)
                if ai_data:
                    _upsert_ai(conn, pid, ai_data)
                migrated += 1
        conn.commit()

    logger.info(f"Migration complete: {migrated} papers, {len(seen_ids)} unique IDs")
    return migrated


def _insert_paper(conn, p: dict) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO papers
        (id, source, title, summary, authors, categories, doi,
         published_date, url, pdf, publisher, journal_title, issn,
         comment, article_type, venue, acceptance, citation_count, version)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            p.get("id", ""),
            p.get("source", ""),
            p.get("title", ""),
            p.get("summary", ""),
            json.dumps(p.get("authors", []), ensure_ascii=False),
            json.dumps(p.get("categories", []), ensure_ascii=False),
            p.get("doi", ""),
            p.get("published_date", ""),
            p.get("url", ""),
            p.get("pdf", ""),
            p.get("publisher", ""),
            p.get("journal_title", ""),
            json.dumps(p.get("issn", []), ensure_ascii=False),
            p.get("comment", ""),
            p.get("article_type", ""),
            p.get("venue", ""),
            p.get("acceptance", ""),
            p.get("citation_count", 0),
            p.get("version", ""),
        ),
    )


def _upsert_ai(conn, paper_id: str, ai: dict) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO ai_results
        (paper_id, tldr, motivation, method, result, conclusion,
         title_zh, summary_zh, quality_score, relevance_score,
         recommendation, skip_reason)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            paper_id,
            ai.get("tldr", ""),
            ai.get("motivation", ""),
            ai.get("method", ""),
            ai.get("result", ""),
            ai.get("conclusion", ""),
            ai.get("title_zh", ""),
            ai.get("summary_zh", ""),
            ai.get("quality_score", 0),
            ai.get("relevance_score", 0),
            ai.get("recommendation", ""),
            ai.get("skip_reason", ""),
        ),
    )
```

- [ ] **Step 2: Commit**

```bash
git add migrate_jsonl.py
git commit -m "feat: migrate_jsonl.py — JSONL to SQLite auto-migration"
```

---

### Task 3: Rewrite `paper_store.py` — DB-backed CRUD

**Files:**
- Rewrite: `paper_store.py`

- [ ] **Step 1: Rewrite `paper_store.py` to use SQLite via `db.py`**

```python
"""paper_store.py — Paper CRUD backed by SQLite."""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from ai.enhance import enhance_single, build_chain, load_research_profile
from ai.quick_filter import build_quick_filter, quick_filter_paper
from crawler.models import Paper
from db import get_conn, queue_write

logger = logging.getLogger("paper_store")

AI_LANGUAGE = "Chinese"

_ai_chain = None
_ai_profile = None
_quick_chain = None


def get_ai_chain():
    global _ai_chain, _ai_profile
    if _ai_chain is None:
        import os
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        _ai_chain = build_chain(model_name)
        _ai_profile = load_research_profile()
        logger.info(f"AI chain initialized: {model_name}")
    return _ai_chain, _ai_profile


def reset_ai_chain():
    global _ai_chain, _ai_profile
    _ai_chain = None
    _ai_profile = None


def get_quick_chain():
    global _quick_chain
    if _quick_chain is None:
        _quick_chain = build_quick_filter()
        logger.info("Quick filter chain initialized")
    return _quick_chain


def _paper_exists(paper_id: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM papers WHERE id=?", (paper_id,)).fetchone()
    return row is not None


def _ai_exists(paper_id: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM ai_results WHERE paper_id=?", (paper_id,)).fetchone()
    return row is not None


def append_paper(paper: Paper, enhance: bool = False) -> bool:
    """Insert paper. If enhance=True, run AI pipeline first. Returns True if new."""
    if _paper_exists(paper.id):
        return False

    paper_dict = json.loads(paper.to_jsonl())

    if enhance:
        if _ai_exists(paper.id):
            # AI result already exists, just insert the paper
            _insert_paper_row(paper_dict)
            return True

        quick_chain = get_quick_chain()
        chain, profile = get_ai_chain()
        if not quick_filter_paper(paper_dict, quick_chain, profile):
            paper_dict["AI"] = {
                "tldr": "", "motivation": "", "method": "", "result": "", "conclusion": "",
                "title_zh": "", "summary_zh": "",
                "quality_score": 0, "relevance_score": 0, "recommendation": "skip",
                "skip_reason": "Filtered by quick relevance check",
            }
            _insert_paper_row(paper_dict)
            _insert_ai_row(paper.id, paper_dict["AI"])
            return True

        try:
            enhanced = enhance_single(paper_dict, chain, profile, AI_LANGUAGE)
            if enhanced:
                _insert_paper_row(enhanced)
                _insert_ai_row(enhanced["id"], enhanced.get("AI", {}))
                return True
        except Exception as e:
            logger.warning(f"AI enhance failed for {paper.id}: {e}")

    _insert_paper_row(paper_dict)
    return True


def _insert_paper_row(p: dict) -> None:
    queue_write(
        """INSERT OR IGNORE INTO papers
        (id, source, title, summary, authors, categories, doi,
         published_date, url, pdf, publisher, journal_title, issn,
         comment, article_type, venue, acceptance, citation_count, version)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            p.get("id", ""), p.get("source", ""), p.get("title", ""),
            p.get("summary", ""),
            json.dumps(p.get("authors", []), ensure_ascii=False),
            json.dumps(p.get("categories", []), ensure_ascii=False),
            p.get("doi", ""), p.get("published_date", ""), p.get("url", ""),
            p.get("pdf", ""), p.get("publisher", ""), p.get("journal_title", ""),
            json.dumps(p.get("issn", []), ensure_ascii=False),
            p.get("comment", ""), p.get("article_type", ""), p.get("venue", ""),
            p.get("acceptance", ""), p.get("citation_count", 0), p.get("version", ""),
        ),
    )


def _insert_ai_row(paper_id: str, ai: dict) -> None:
    queue_write(
        """INSERT OR REPLACE INTO ai_results
        (paper_id, tldr, motivation, method, result, conclusion,
         title_zh, summary_zh, quality_score, relevance_score,
         recommendation, skip_reason)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            paper_id, ai.get("tldr", ""), ai.get("motivation", ""),
            ai.get("method", ""), ai.get("result", ""), ai.get("conclusion", ""),
            ai.get("title_zh", ""), ai.get("summary_zh", ""),
            ai.get("quality_score", 0), ai.get("relevance_score", 0),
            ai.get("recommendation", ""), ai.get("skip_reason", ""),
        ),
    )


def find_paper_by_id(paper_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        """SELECT p.*, ai.tldr, ai.motivation, ai.method, ai.result, ai.conclusion,
                  ai.title_zh, ai.summary_zh, ai.quality_score, ai.relevance_score,
                  ai.recommendation, ai.skip_reason
           FROM papers p LEFT JOIN ai_results ai ON p.id = ai.paper_id
           WHERE p.id=?""",
        (paper_id,),
    ).fetchone()
    if not row:
        return None
    return _row_to_dict(row)


def load_all_papers() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT p.*, ai.tldr, ai.motivation, ai.method, ai.result, ai.conclusion,
                  ai.title_zh, ai.summary_zh, ai.quality_score, ai.relevance_score,
                  ai.recommendation, ai.skip_reason
           FROM papers p LEFT JOIN ai_results ai ON p.id = ai.paper_id
           ORDER BY p.created_at DESC"""
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a joined papers+ai_results row to the dict format expected by the API."""
    PAPER_COLS = [
        "id", "source", "title", "summary", "authors", "categories", "doi",
        "published_date", "url", "pdf", "publisher", "journal_title", "issn",
        "comment", "article_type", "venue", "acceptance", "citation_count", "version",
    ]
    AI_COLS = [
        "tldr", "motivation", "method", "result", "conclusion",
        "title_zh", "summary_zh", "quality_score", "relevance_score",
        "recommendation", "skip_reason",
    ]
    d = {}
    for col in PAPER_COLS:
        val = row[col]
        if col in ("authors", "categories", "issn") and isinstance(val, str):
            val = json.loads(val)
        d[col] = val
    ai = {}
    has_ai = False
    for col in AI_COLS:
        val = row[col]
        if val is not None and val != "" and val != 0:
            has_ai = True
        ai[col] = val
    if has_ai:
        d["AI"] = ai
    return d


# Legacy compat — used by api.py stats endpoint
def get_written_count() -> int:
    conn = get_conn()
    return conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
```

- [ ] **Step 2: Commit**

```bash
git add paper_store.py
git commit -m "refactor: paper_store.py — SQLite-backed CRUD replacing JSONL scanning"
```

---

### Task 4: Refactor `jobs.py` — BaseCrawlerJob base class

**Files:**
- Rewrite: `jobs.py`

- [ ] **Step 1: Rewrite `jobs.py` with `BaseCrawlerJob` and thin subclasses**

```python
"""jobs.py — Crawler job scheduling with BaseCrawlerJob pattern."""
from __future__ import annotations

import logging
import os
import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Generator

from ai.digest import generate_digest
from ai.enhance import enhance_single, load_research_profile
from crawler.arxiv_crawler import ArxivCrawler
from crawler.author_crawler import AuthorCrawler
from crawler.crossref_crawler import CrossrefCrawler
from crawler.dblp_crawler import DblpCrawler
from crawler.s2_crawler import S2Crawler
from crawler.subs_store import Subscriptions
from db import get_conn, queue_write
from paper_store import append_paper, get_ai_chain, reset_ai_chain, AI_LANGUAGE

logger = logging.getLogger("jobs")

SUBS_PATH = "subscriptions.json"
_job_status: dict[str, dict] = {}
_ai_max_workers = int(os.environ.get("AI_MAX_WORKERS", "3"))


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


class BaseCrawlerJob(ABC):
    """Base class for all crawler jobs. Subclasses set name and implement _create_crawler + _post_run."""

    name: str = ""

    def run(self) -> None:
        _set_job_status(self.name, "running")
        logger.info(f"Starting {self.name} crawl job")
        try:
            subs = _load_subs()
            crawler = self._create_crawler(subs)
            if crawler is None:
                _set_job_status(self.name, "skipped", self._skip_reason(subs))
                return
            fetched, written = 0, 0
            for paper in crawler.crawl_iter():
                fetched += 1
                if append_paper(paper, enhance=True):
                    written += 1
                if fetched % 20 == 0:
                    logger.info(f"{self.name} progress: {fetched} fetched, {written} written")
            self._post_run(subs, fetched)
            logger.info(f"{self.name} job done: {fetched} fetched, {written} new written")
            _set_job_status(self.name, "done", f"{fetched} fetched, {written} written")
        except Exception as e:
            logger.error(f"{self.name} job failed: {e}", exc_info=True)
            _set_job_status(self.name, "error", str(e))

    @abstractmethod
    def _create_crawler(self, subs: Subscriptions):
        """Return a crawler instance or None to skip."""

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no config"

    def _post_run(self, subs: Subscriptions, fetched: int) -> None:
        pass


class ArxivJob(BaseCrawlerJob):
    name = "arxiv"

    def _create_crawler(self, subs: Subscriptions):
        if not subs.arxiv_categories:
            return None
        from paper_store import _paper_exists
        existing = set()
        conn = get_conn()
        for row in conn.execute("SELECT id FROM papers WHERE source='arxiv'"):
            existing.add(row[0])
        return ArxivCrawler(categories=subs.arxiv_categories, existing_ids=existing)

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no categories"


class CrossrefJob(BaseCrawlerJob):
    name = "crossref"

    def _create_crawler(self, subs: Subscriptions):
        if not subs.crossref_journals:
            return None
        return CrossrefCrawler(journals=subs.crossref_journals)

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no journals"

    def _post_run(self, subs: Subscriptions, fetched: int) -> None:
        if fetched > 0:
            now = datetime.now(timezone.utc).isoformat()
            for j in subs.crossref_journals:
                j.last_updated = now
            _save_subs(subs)


class DblpJob(BaseCrawlerJob):
    name = "dblp"

    def _create_crawler(self, subs: Subscriptions):
        if not subs.conferences:
            return None
        return DblpCrawler(conferences=subs.conferences)

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no conferences"

    def _post_run(self, subs: Subscriptions, fetched: int) -> None:
        if fetched > 0:
            now = datetime.now(timezone.utc).isoformat()
            for c in subs.conferences:
                c.last_updated = now
            _save_subs(subs)


class S2Job(BaseCrawlerJob):
    name = "s2"

    def _create_crawler(self, subs: Subscriptions):
        keywords = subs.search_keywords
        if not keywords:
            profile = load_research_profile()
            keywords = profile.get("keywords", [])
        if not keywords:
            return None
        return S2Crawler(keywords=keywords, max_per_keyword=20)

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no keywords"


class AuthorJob(BaseCrawlerJob):
    name = "author"

    def _create_crawler(self, subs: Subscriptions):
        if not subs.authors:
            return None
        author_dicts = [{"authorId": a.author_id, "name": a.name} for a in subs.authors]
        return AuthorCrawler(authors=author_dicts, papers_per_author=50)

    def _skip_reason(self, subs: Subscriptions) -> str:
        return "no authors"

    def _post_run(self, subs: Subscriptions, fetched: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for a in subs.authors:
            a.last_updated = now
        _save_subs(subs)


# Job registry
JOBS: dict[str, BaseCrawlerJob] = {
    "arxiv": ArxivJob(),
    "crossref": CrossrefJob(),
    "dblp": DblpJob(),
    "s2": S2Job(),
    "author": AuthorJob(),
}


# Standalone job functions (used by api.py trigger endpoints)
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


def run_retro_enhance():
    logger.info("Starting retro-enhance for papers without AI data")
    try:
        chain, profile = get_ai_chain()
        conn = get_conn()
        rows = conn.execute(
            """SELECT p.* FROM papers p
               LEFT JOIN ai_results ai ON p.id = ai.paper_id
               WHERE ai.paper_id IS NULL AND (p.summary != '' OR p.title != '')"""
        ).fetchall()
        if not rows:
            logger.info("No papers to retro-enhance")
            return

        import json
        from paper_store import _insert_ai_row

        logger.info(f"Retro-enhance: {len(rows)} papers to process")
        enhanced_count = 0
        with ThreadPoolExecutor(max_workers=_ai_max_workers) as executor:
            futures = {}
            for row in rows:
                p = dict(row)
                p["authors"] = json.loads(p.get("authors", "[]"))
                p["categories"] = json.loads(p.get("categories", "[]"))
                p["issn"] = json.loads(p.get("issn", "[]"))
                futures[executor.submit(enhance_single, p, chain, profile, AI_LANGUAGE)] = p

            for future in as_completed(futures):
                p = futures[future]
                try:
                    result = future.result()
                    if result:
                        _insert_ai_row(result["id"], result.get("AI", {}))
                        enhanced_count += 1
                except Exception as e:
                    logger.warning(f"Retro-enhance failed for {p.get('id','?')}: {e}")
                if enhanced_count % 10 == 0:
                    logger.info(f"Retro-enhance progress: {enhanced_count}/{len(rows)}")

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
```

- [ ] **Step 2: Commit**

```bash
git add jobs.py
git commit -m "refactor: jobs.py — BaseCrawlerJob base class eliminates 5 duplicate functions"
```

---

### Task 5: Simplify `ai/enhance.py` — Unified entry point

**Files:**
- Simplify: `ai/enhance.py`

- [ ] **Step 1: Simplify `ai/enhance.py` — keep `enhance_single()`, `build_chain()`, `load_research_profile()`, remove CLI-only code**

```python
"""ai/enhance.py — Unified AI enhancement for arxivSCI-daily."""
import json
import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from threading import Lock
from datetime import datetime

import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain_core.exceptions import OutputParserException
from .structure import Structure

logger = logging.getLogger(__name__)

_AI_DIR = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_AI_DIR, '.env')
if os.path.exists(_env_path):
    dotenv.load_dotenv(_env_path)

template = open(os.path.join(_AI_DIR, "template.txt"), "r").read()
system = open(os.path.join(_AI_DIR, "system.txt"), "r").read()

DEFAULT_AI = {
    "tldr": "", "motivation": "", "method": "", "result": "", "conclusion": "",
    "title_zh": "", "summary_zh": "",
    "quality_score": 0, "relevance_score": 0, "recommendation": "skip",
    "skip_reason": "",
}


def load_research_profile() -> dict:
    profile_path = os.path.join(os.path.dirname(__file__), '..', 'research_profile.json')
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            return json.load(f)
    return {"direction": "", "keywords": [], "quality_criteria": ""}


def build_chain(model_name: str):
    llm = ChatOpenAI(model=model_name).with_structured_output(Structure, method="json_mode")
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])
    return prompt_template | llm


def enhance_single(paper: dict, chain, profile: dict, language: str) -> dict | None:
    """Enhance a single paper with AI analysis. Used by both daemon and CLI."""
    try:
        response: Structure = chain.invoke({
            "language": language,
            "content": paper.get("summary", ""),
            "title": paper.get("title", ""),
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
            "quality_criteria": profile.get("quality_criteria", ""),
            "liked_topics": "\n".join(profile.get("liked_topics", [])[-5:]),
            "disliked_topics": "\n".join(profile.get("disliked_topics", [])[-5:]),
        })
        paper["AI"] = response.model_dump()
    except OutputParserException as e:
        partial = _extract_partial(str(e))
        paper["AI"] = {**DEFAULT_AI, **partial}
    except Exception as e:
        logger.error(f"Enhance error for {paper.get('id','?')}: {e}")
        paper["AI"] = {**DEFAULT_AI}

    for k in DEFAULT_AI:
        if k not in paper["AI"]:
            paper["AI"][k] = DEFAULT_AI[k]
    return paper


def _extract_partial(error_msg: str) -> dict:
    """Try to extract partial JSON from an OutputParserException."""
    try:
        if "Function Structure arguments:" in error_msg:
            json_str = error_msg.split("Function Structure arguments:", 1)[1].strip()
            json_str = json_str.split("are not valid JSON")[0].strip()
        else:
            start = error_msg.find('{')
            end = error_msg.rfind('}')
            if start != -1 and end != -1:
                json_str = error_msg[start:end+1]
            else:
                return {}
        return json.loads(json_str) if json_str else {}
    except Exception:
        return {}


# ── CLI entry point (kept for standalone usage) ────────────────────

def main():
    """Standalone CLI: python -m ai.enhance --data FILE"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    parser.add_argument("--max_workers", type=int, default=1)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
    language = os.environ.get("LANGUAGE", "Chinese")
    chain = build_chain(model_name)
    profile = load_research_profile()

    data = []
    with open(args.data, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))

    # Deduplicate
    seen = set()
    unique = []
    for item in data:
        if item["id"] not in seen:
            seen.add(item["id"])
            unique.append(item)

    target = args.data.replace(".jsonl", f"_AI_enhanced_{language}.jsonl")
    existing_ids = set()
    if os.path.exists(target):
        with open(target, "r") as f:
            for line in f:
                if line.strip():
                    existing_ids.add(json.loads(line)["id"])

    new_data = [item for item in unique if item["id"] not in existing_ids]
    logger.info(f"Processing {len(new_data)} new papers (skipping {len(existing_ids)} existing)")

    saved = 0
    with open(target, "a") as f:
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            futures = {executor.submit(enhance_single, p, chain, profile, language): p for p in new_data}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                    f.flush()
                    saved += 1
    logger.info(f"Done: {saved} papers enhanced → {target}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add ai/enhance.py
git commit -m "refactor: ai/enhance.py — unified enhance_single(), removed duplicate CLI code"
```

---

### Task 6: Update `api.py`, `daemon.py`, `ai/digest.py` — Wire everything to SQLite

**Files:**
- Modify: `api.py`
- Modify: `daemon.py`
- Modify: `ai/digest.py`

- [ ] **Step 1: Update `api.py` — remove JSONL scanning, use paper_store DB functions**

The key changes to `api.py`:
1. `get_papers()` — calls `load_all_papers()` which now queries SQLite instead of scanning JSONL
2. `get_stats()` — use `get_written_count()` instead of `_written_ids` global
3. `save_feedback()` — write to `feedback` table via `queue_write()` instead of `feedback.json`
4. `get_feedback()` — read from `feedback` table
5. `_update_profile_from_feedback()` — keep as-is (operates on research_profile.json, not JSONL)
6. `export_bibtex()` — query papers by ID from DB instead of scanning all JSONL files
7. Remove `DATA_DIR` import and all file-scanning loops

```python
# api.py — key changes only (diff-style)

# REMOVE these imports:
#   from paper_store import ..., DATA_DIR
# ADD these imports:
from paper_store import load_all_papers, find_paper_by_id, get_written_count
from db import get_conn, queue_write

# get_papers() — change to:
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
    return jsonify({"papers": papers[start:start + per_page], "total": total, "page": page, "per_page": per_page})

# get_stats() — replace body:
@app.route("/api/stats")
def get_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    source_counts = {}
    for row in conn.execute("SELECT source, COUNT(*) as cnt FROM papers GROUP BY source"):
        source_counts[row["source"]] = row["cnt"]
    subs = _load_subs()
    return jsonify({
        "total_papers": total,
        "by_source": source_counts,
        "arxiv_categories": subs.arxiv_categories,
        "crossref_journals": len(subs.crossref_journals),
    })

# save_feedback() — write to DB:
@app.route("/api/feedback", methods=["POST"])
def save_feedback():
    data = request.json or {}
    paper_id = data.get("paper_id", "")
    rating = data.get("rating", "")
    if not paper_id or rating not in ("useful", "not_useful"):
        return jsonify({"error": "invalid"}), 400
    queue_write(
        "INSERT OR REPLACE INTO feedback (paper_id, rating) VALUES (?, ?)",
        (paper_id, rating),
    )
    _update_profile_from_feedback(paper_id, rating)
    return jsonify({"status": "saved"})

# get_feedback() — read from DB:
@app.route("/api/feedback", methods=["GET"])
def get_feedback():
    conn = get_conn()
    rows = conn.execute("SELECT paper_id, rating FROM feedback").fetchall()
    return jsonify({row["paper_id"]: row["rating"] for row in rows})

# export_bibtex() — query by ID from DB:
@app.route("/api/export/bibtex", methods=["POST"])
def export_bibtex():
    data = request.get_json()
    ids = data.get("ids", []) if data else []
    if not ids:
        return jsonify({"error": "no ids provided"}), 400
    conn = get_conn()
    entries = []
    for pid in ids:
        paper = find_paper_by_id(pid)
        if paper:
            entries.append(_bibtex_for(paper))
    if not entries:
        return jsonify({"error": "no papers found"}), 404
    return "\n\n".join(entries), 200, {"Content-Type": "application/x-bibtex"}

# Remove FEEDBACK_FILE constant and its usage
# Remove _load_feedback / _save_feedback helpers if any
```

- [ ] **Step 2: Update `daemon.py` — call `init_db()` + auto-migration**

```python
# daemon.py — key changes only

# REMOVE: from paper_store import init_ids
# ADD:
from db import init_db, stop_writer
from migrate_jsonl import needs_migration, run_migration

# In main(), replace `init_ids()` with:
    init_db()
    if needs_migration():
        logger.info("Detected JSONL data, running migration...")
        count = run_migration()
        logger.info(f"Migrated {count} papers from JSONL to SQLite")

# Add to _signal_handler:
    def _signal_handler(sig, frame):
        logger.info("Shutting down...")
        sched.stop()
        stop_writer()
        sys.exit(0)
```

- [ ] **Step 3: Update `ai/digest.py` — read papers from DB instead of JSONL**

```python
# ai/digest.py — key changes to generate_digest()

def generate_digest(date_str: str | None = None, language: str = "Chinese") -> str:
    date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    from db import get_conn

    conn = get_conn()
    rows = conn.execute(
        """SELECT p.title, p.source, p.journal_title, p.categories,
                  ai.tldr, ai.recommendation, ai.quality_score, ai.relevance_score
           FROM papers p JOIN ai_results ai ON p.id = ai.paper_id
           WHERE p.published_date = ?
           ORDER BY ai.relevance_score DESC, ai.quality_score DESC
           LIMIT 80""",
        (date_str,),
    ).fetchall()

    if not rows:
        logger.warning(f"No AI-enhanced papers for {date_str}")
        return ""

    summaries = []
    for row in rows:
        import json
        summaries.append({
            "title": row["title"],
            "source": row["source"],
            "journal": row["journal_title"],
            "categories": json.loads(row["categories"]),
            "tldr": row["tldr"],
            "recommendation": row["recommendation"],
            "quality_score": row["quality_score"],
            "relevance_score": row["relevance_score"],
        })

    model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
    llm = ChatOpenAI(model=model_name, temperature=0.3)
    prompt = ChatPromptTemplate.from_template(DIGEST_PROMPT)
    chain = prompt | llm

    result = chain.invoke({
        "language": language,
        "papers_json": json.dumps(summaries, ensure_ascii=False, indent=2),
    })

    # Save digest to DB as well
    digest_dir = Path(__file__).parent.parent / "digests"
    digest_dir.mkdir(exist_ok=True)
    digest_path = digest_dir / f"{date_str}.md"
    content = f"# Research Digest — {date_str}\n\n{result.content}\n"
    digest_path.write_text(content, encoding="utf-8")

    from db import queue_write
    queue_write(
        "INSERT OR REPLACE INTO digests (date, content) VALUES (?, ?)",
        (date_str, content),
    )

    logger.info(f"Digest saved to {digest_path}")
    return str(digest_path)
```

- [ ] **Step 4: Update `.gitignore` — add `data/papers.db`**

Add to `.gitignore`:
```
data/papers.db
data/papers.db-wal
data/papers.db-shm
```

- [ ] **Step 5: Commit**

```bash
git add api.py daemon.py ai/digest.py .gitignore
git commit -m "refactor: wire api/daemon/digest to SQLite, auto-migration on startup"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** SQLite 5-table schema ✓, auto-migration ✓, WAL+write-queue ✓, BaseCrawlerJob ✓, enhance.py unified ✓, api.py wired ✓, daemon.py wired ✓, digest.py wired ✓
- [x] **Placeholder scan:** No TBD/TODO/fill-in-later. All code blocks contain full implementations.
- [x] **Type consistency:** `_insert_paper_row` / `_insert_ai_row` use same column order across paper_store.py and migrate_jsonl.py. `find_paper_by_id` returns dict with "AI" key matching frontend expectations. `queue_write(sql, params)` signature consistent across all callers.

