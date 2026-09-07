"""SQLite storage layer for arxivSCI-daily.

Provides:
- Schema initialization with 5 tables
- Thread-local connection management
- Background write queue for batched writes
- WAL mode for concurrent reads
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from pathlib import Path
from queue import Queue
from typing import Any

logger = logging.getLogger("db")

# Database path
DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "papers.db"

# Thread-local storage for connections
_local = threading.local()

# Write queue and worker thread
_write_queue: Queue[tuple[str, tuple[Any, ...]] | None] = Queue()
_writer_thread: threading.Thread | None = None
_shutdown_event = threading.Event()

# Batch configuration
BATCH_SIZE = 50
DRAIN_INTERVAL = 0.1  # 100ms


def get_conn() -> sqlite3.Connection:
    """Get a thread-local SQLite connection.

    Each thread gets its own connection to avoid cross-thread issues.
    Connections are cached in thread-local storage.

    Returns:
        sqlite3.Connection: Thread-local database connection
    """
    if not hasattr(_local, "conn") or _local.conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(DB_PATH),
            check_same_thread=False,
            isolation_level=None,  # Autocommit for reads
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
        logger.debug(f"Created new connection for thread {threading.current_thread().name}")
    return _local.conn


def init_db() -> None:
    """Initialize database schema and start the writer thread.

    Creates all tables if they don't exist and starts the background
    write queue worker thread.
    """
    conn = get_conn()

    # Create tables
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            authors JSON,
            categories JSON,
            doi TEXT,
            published_date TEXT,
            url TEXT,
            pdf TEXT,
            publisher TEXT,
            journal_title TEXT,
            issn JSON,
            comment TEXT,
            article_type TEXT,
            venue TEXT,
            acceptance TEXT,
            citation_count INTEGER DEFAULT 0,
            ccf_tier TEXT,
            version TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ai_results (
            paper_id TEXT PRIMARY KEY,
            tldr TEXT,
            motivation TEXT,
            method TEXT,
            result TEXT,
            conclusion TEXT,
            title_zh TEXT,
            summary_zh TEXT,
            quality_score INTEGER,
            relevance_score INTEGER,
            recommendation TEXT,
            skip_reason TEXT,
            enhanced_at TEXT,
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS feedback (
            paper_id TEXT PRIMARY KEY,
            rating TEXT CHECK (rating IN ('like', 'dislike', '')),
            relevance INTEGER CHECK (relevance BETWEEN 1 AND 5),
            novelty INTEGER CHECK (novelty BETWEEN 1 AND 5),
            note TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
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

        CREATE TABLE IF NOT EXISTS knowledge_cards (
            paper_id TEXT PRIMARY KEY,
            problem TEXT,
            method_extracted TEXT,
            result_extracted TEXT,
            keywords JSON,
            relation_to_profile TEXT,
            extracted_at TEXT,
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS knowledge_clusters (
            cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_name TEXT NOT NULL,
            method_keywords JSON NOT NULL,
            paper_ids JSON NOT NULL,
            problem_domains JSON,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS fulltext_analysis (
            paper_id TEXT PRIMARY KEY,
            method_implementation TEXT,
            experimental_design TEXT,
            key_results_detail TEXT,
            limitations TEXT,
            reproducibility TEXT,
            relevance_to_profile TEXT,
            analyzed_at TEXT,
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS trend_reports (
            week_start TEXT PRIMARY KEY,
            new_methods TEXT,
            solved_problems TEXT,
            controversies TEXT,
            opportunities TEXT,
            paper_count INTEGER,
            generated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS ignored_papers (
            paper_id TEXT PRIMARY KEY,
            reason TEXT,
            ignored_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);
        CREATE INDEX IF NOT EXISTS idx_papers_published_date ON papers(published_date);
        CREATE INDEX IF NOT EXISTS idx_ai_results_recommendation ON ai_results(recommendation);
        CREATE INDEX IF NOT EXISTS idx_ai_results_relevance_score ON ai_results(relevance_score);
        CREATE INDEX IF NOT EXISTS idx_knowledge_cards_keywords ON knowledge_cards(keywords);
        CREATE INDEX IF NOT EXISTS idx_papers_ccf_tier ON papers(ccf_tier);
        CREATE INDEX IF NOT EXISTS idx_papers_created_at ON papers(created_at);
    """)

    # Schema migrations for databases created before bookmarks were server-side
    feedback_cols = {r[1] for r in conn.execute("PRAGMA table_info(feedback)")}
    if "bookmarked" not in feedback_cols:
        conn.execute("ALTER TABLE feedback ADD COLUMN bookmarked INTEGER DEFAULT 0")
    if "is_read" not in feedback_cols:
        conn.execute("ALTER TABLE feedback ADD COLUMN is_read INTEGER DEFAULT 0")
    papers_cols = {r[1] for r in conn.execute("PRAGMA table_info(papers)")}
    if "code_url" not in papers_cols:
        conn.execute("ALTER TABLE papers ADD COLUMN code_url TEXT")
    ignored_cols = {r[1] for r in conn.execute("PRAGMA table_info(ignored_papers)")}
    if "reason_detail" not in ignored_cols:
        conn.execute("ALTER TABLE ignored_papers ADD COLUMN reason_detail TEXT")
    trend_cols = {r[1] for r in conn.execute("PRAGMA table_info(trend_reports)")}
    if "period_type" not in trend_cols:
        conn.execute("ALTER TABLE trend_reports ADD COLUMN period_type TEXT DEFAULT 'weekly'")

    logger.info("数据库架构已初始化")

    # Start writer thread
    _start_writer()


def _start_writer() -> None:
    """Start the background write queue worker thread."""
    global _writer_thread

    if _writer_thread is not None and _writer_thread.is_alive():
        logger.warning("写入线程已在运行")
        return

    _shutdown_event.clear()
    _writer_thread = threading.Thread(
        target=_write_worker,
        name="db-writer",
        daemon=True,
    )
    _writer_thread.start()
    logger.info("写入线程已启动")


def _write_worker() -> None:
    """Background worker that processes the write queue.

    Uses a separate connection (not thread-local) to avoid cross-thread issues.
    Batches up to BATCH_SIZE writes and drains every DRAIN_INTERVAL.
    """
    # Separate connection for the writer thread
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False,
        isolation_level="IMMEDIATE",
    )
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    logger.debug("Writer thread connection established")

    while not _shutdown_event.is_set():
        batch: list[tuple[str, tuple[Any, ...]]] = []
        deadline = time.time() + DRAIN_INTERVAL

        # Collect batch
        while len(batch) < BATCH_SIZE:
            remaining = deadline - time.time()
            if remaining <= 0:
                break

            try:
                item = _write_queue.get(timeout=remaining)
                if item is None:  # Sentinel
                    _flush(conn, batch)
                    conn.close()
                    logger.debug("Writer thread received shutdown signal")
                    return
                batch.append(item)
            except Exception:
                break  # Timeout, flush current batch

        if batch:
            _flush(conn, batch)

    conn.close()
    logger.debug("Writer thread exiting")


def _flush(conn: sqlite3.Connection, batch: list[tuple[str, tuple[Any, ...]]]) -> None:
    """Flush a batch of writes to the database.

    Args:
        conn: Database connection
        batch: List of (sql, params) tuples

    Wraps the batch in a transaction with rollback on error.
    """
    if not batch:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        for sql, params in batch:
            cursor.execute(sql, params)
        conn.commit()
        logger.debug(f"Flushed {len(batch)} writes")
    except Exception as e:
        conn.rollback()
        logger.error(f"批量写入失败，已回滚 {len(batch)} 项: {e}")


def queue_write(sql: str, params: tuple[Any, ...] = ()) -> None:
    """Queue a write operation for async processing.

    Args:
        sql: SQL statement
        params: Parameters tuple

    The write will be processed by the background worker thread
    in the next batch.
    """
    if _shutdown_event.is_set():
        logger.warning("写入队列正在关闭，写入被拒绝")
        return
    _write_queue.put((sql, params))


def sync_write(sql: str, params: tuple[Any, ...] = ()) -> None:
    """Execute a write operation synchronously.

    Args:
        sql: SQL statement
        params: Parameters tuple

    Bypasses the write queue for immediate execution.
    Use sparingly for critical writes that must complete before proceeding.
    """
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(sql, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"同步写入失败: {e}")
        raise


def ignore_paper(paper_id: str, reason: str = "", detail: str = "") -> None:
    """Record a paper as ignored so it won't be re-fetched.

    detail carries the human explanation (e.g. quick_filter's
    relevance_reason) for later audit. Uses the async write queue.
    """
    queue_write(
        "INSERT OR REPLACE INTO ignored_papers (paper_id, reason, reason_detail, ignored_at) VALUES (?, ?, ?, datetime('now'))",
        (paper_id, reason, detail or None),
    )


def is_ignored(paper_id: str) -> bool:
    """Check if a paper was previously ignored."""
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM ignored_papers WHERE paper_id = ?", (paper_id,)).fetchone()
    return row is not None


def stop_writer() -> None:
    """Stop the background writer thread.

    Sets shutdown event, puts sentinel in queue, and joins thread
    with 5 second timeout.
    """
    global _writer_thread

    if _writer_thread is None or not _writer_thread.is_alive():
        logger.debug("Writer thread not running")
        return

    _shutdown_event.set()
    _write_queue.put(None)  # Sentinel

    _writer_thread.join(timeout=5.0)

    if _writer_thread.is_alive():
        logger.warning("写入线程未能优雅停止")
    else:
        logger.info("写入线程已停止")

    _writer_thread = None
