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
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
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
        logger.info(f"已创建默认配置 {args.config}")

    init_db()
    if needs_migration():
        logger.info("检测到 JSONL 数据，正在迁移...")
        count = run_migration()
        logger.info(f"已迁移 {count} 篇论文从 JSONL 到 SQLite")

    sched = Scheduler()

    def _signal_handler(sig, frame):
        logger.info("正在关闭...")
        sched.stop()
        stop_writer()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    sched_thread = threading.Thread(target=sched.start, daemon=True)
    sched_thread.start()
    import os
    night_start = os.environ.get("NIGHT_START", "2")
    stagger = os.environ.get("STAGGER_MINUTES", "30")
    if os.environ.get("RUN_ON_START", "") in ("1", "true", "yes"):
        logger.info(f"调度器已启动: 全部任务立即执行一次，此后每天凌晨 {night_start} 点起、每 {stagger} 分钟一个错峰运行")
    else:
        logger.info(f"调度器已启动: 自动任务每天凌晨 {night_start} 点起、每 {stagger} 分钟一个错峰运行（手动触发随时可用）")

    logger.info(f"服务启动，端口 {args.port}")
    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
