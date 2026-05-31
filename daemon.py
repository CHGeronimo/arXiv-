#!/usr/bin/env python3
"""arxivSCI-daily daemon: persistent service with multi-source subscription."""

import argparse
import logging
import signal
import sys
import threading
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("daemon")
logging.getLogger("arxiv").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(description="arxivSCI-daily daemon")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument("--config", default="subscriptions.json", help="Subscriptions file")
    args = parser.parse_args()

    # Late import to avoid circular dependencies at module level
    from api import app
    from jobs import Scheduler
    from crawler.subs_store import Subscriptions
    from db import init_db, stop_writer
    from migrate_jsonl import needs_migration, run_migration

    if not Path(args.config).exists():
        Subscriptions().save(args.config)
        logger.info(f"Created default {args.config}")

    init_db()
    if needs_migration():
        logger.info("Detected JSONL data, running migration...")
        count = run_migration()
        logger.info(f"Migrated {count} papers from JSONL to SQLite")

    sched = Scheduler()

    def _signal_handler(sig, frame):
        logger.info("Shutting down...")
        sched.stop()
        stop_writer()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    sched_thread = threading.Thread(target=sched.start, daemon=True)
    sched_thread.start()
    logger.info("Scheduler started: arXiv every 3h, Crossref/DBLP/S2/Author every 24h")

    logger.info(f"Starting server on port {args.port}")
    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
