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
    from api import app, SUBS_PATH
    from jobs import Scheduler, _save_subs, SUBS_PATH as JOBS_SUBS_PATH
    from crawler.subs_store import Subscriptions
    from paper_store import init_ids

    # Sync subs path
    import api as _api
    import jobs as _jobs
    _api.SUBS_PATH = args.config
    _jobs.SUBS_PATH = args.config

    if not Path(args.config).exists():
        Subscriptions().save(args.config)
        logger.info(f"Created default {args.config}")

    init_ids()

    sched = Scheduler()

    def _signal_handler(sig, frame):
        logger.info("Shutting down...")
        sched.stop()
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
