#!/usr/bin/env python3
"""arxivSCI-daily daemon: persistent service with multi-source subscription.

监听地址优先级：命令行参数 > ai/.env（DAEMON_HOST/DAEMON_PORT，前端 ⚙️ 设置
面板可改）> 默认 127.0.0.1:8080。
"""

import argparse
import logging
import os
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

# 前端改的供应商/模型/监听地址都落在 ai/.env，启动时先载入
_AI_ENV = Path(__file__).resolve().parent / "ai" / ".env"
if _AI_ENV.exists():
    try:
        import dotenv
        dotenv.load_dotenv(_AI_ENV)
    except ImportError:
        pass


def resolve_bind(args_host: str | None, args_port: int | None) -> tuple[str, int]:
    """命令行 > 环境变量（前端写入）> 默认。独立成函数便于测试。"""
    host = args_host or os.environ.get("DAEMON_HOST", "").strip() or "127.0.0.1"
    if args_port is not None:
        port = args_port
    else:
        try:
            port = int(os.environ.get("DAEMON_PORT", "").strip() or 8080)
        except ValueError:
            logger.warning(f"DAEMON_PORT 配置非法，回退 8080")
            port = 8080
    return host, port


def main():
    parser = argparse.ArgumentParser(description="arXiv 每日电讯 daemon")
    parser.add_argument("--host", default=None, help="HTTP bind host（默认取 DAEMON_HOST 或 127.0.0.1）")
    parser.add_argument("--port", type=int, default=None, help="HTTP port（默认取 DAEMON_PORT 或 8080）")
    parser.add_argument("--config", default="subscriptions.json", help="Subscriptions file")
    args = parser.parse_args()

    # Late import to avoid circular dependencies at module level
    from backend.api import app
    from backend.jobs import Scheduler
    from backend.crawler.subs_store import Subscriptions
    from backend.db import init_db, stop_writer
    from scripts.migrate_jsonl import needs_migration, run_migration

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
        from backend.jobs import request_shutdown
        request_shutdown()
        sched.stop()
        stop_writer()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    sched_thread = threading.Thread(target=sched.start, daemon=True)
    sched_thread.start()
    night_start = os.environ.get("NIGHT_START", "2")
    stagger = os.environ.get("STAGGER_MINUTES", "30")
    from backend.db import get_runtime_settings
    if get_runtime_settings()["RUN_ON_START"]:
        logger.info(f"调度器已启动: 全部任务立即执行一次，此后每天凌晨 {night_start} 点起、每 {stagger} 分钟一个错峰运行")
    else:
        logger.info(f"调度器已启动: 自动任务每天凌晨 {night_start} 点起、每 {stagger} 分钟一个错峰运行（手动触发随时可用）")

    host, port = resolve_bind(args.host, args.port)
    # 实际绑定值暴露给 API（前端用来提示“改了但未重启”）
    os.environ["DAEMON_HOST_ACTUAL"] = host
    os.environ["DAEMON_PORT_ACTUAL"] = str(port)
    if host == "0.0.0.0":
        logger.warning("监听 0.0.0.0：服务对局域网开放（含 AI 配置接口），注意环境安全")
    logger.info(f"「arXiv 每日电讯」服务启动: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
