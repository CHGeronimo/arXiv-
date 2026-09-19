"""🧪 系统自检——轻量连通性冒烟测试。

对每个子系统用最小代价（每个网络源 1 条请求、LLM 一次 ping + 一次快筛冒烟）
验证全链路可用，绝不触发全量爬取/增强。报告由 /api/selftest 读出，
🔄 菜单「🧪 系统自检」触发，前端弹窗展示分组结果。
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_last_report: dict | None = None


def get_last_report() -> dict | None:
    return _last_report


def _check(checks: list, group: str, name: str, fn, warn_on: tuple = ()):
    """执行单项检查；异常→fail，命中 warn_on 类型→warn，其余→ok。"""
    t0 = time.monotonic()
    try:
        detail = fn()
        status = "ok"
    except Exception as e:  # noqa: BLE001 — 自检的职责就是把异常变成报告行
        detail, status = f"{type(e).__name__}: {str(e)[:160]}", "fail"
    if status == "ok" and isinstance(detail, tuple):
        detail, status = detail[0], detail[1]  # 检查函数可返回 (detail, "warn")
    checks.append({"group": group, "name": name, "status": status,
                   "ms": int((time.monotonic() - t0) * 1000), "detail": str(detail)[:200]})


def _http_ok(url: str, params: dict | None = None, timeout: float = 10) -> str:
    resp = httpx.get(url, params=params, timeout=timeout,
                     headers={"User-Agent": "arxivSCI-daily-selftest"})
    if resp.status_code == 200:
        return f"HTTP 200 · {len(resp.content)//1024}KB"
    if resp.status_code == 429:
        return (f"HTTP 429 限流（可稍后自检）", "warn")
    raise RuntimeError(f"HTTP {resp.status_code}")


def run_selftest() -> dict:
    global _last_report
    checks: list[dict] = []

    # ── 网络组：每源 1 条最小请求 ──────────────────────────────
    _check(checks, "网络", "arXiv 列表页", lambda: _http_ok("https://arxiv.org/list/cs.MA/new"))
    _check(checks, "网络", "Crossref API", lambda: _http_ok(
        "https://api.crossref.org/works", {"rows": 1}))

    def _openalex():
        from backend.crawler.openalex_client import openalex_get
        data = openalex_get("https://api.openalex.org/works",
                            {"search": "reinforcement learning", "per-page": 1})
        if data is None:
            return ("接口熔断/无响应", "warn")
        n = data.get("meta", {}).get("count", "?")
        return f"搜索正常 · 全库命中 {n}"
    _check(checks, "网络", "OpenAlex 搜索", _openalex)

    def _openalex_quota():
        from backend.crawler.openalex_client import quota_paused
        if quota_paused():
            return ("计费配额熔断中（UTC 午夜重置，期间仅免费接口可用）", "warn")
        return "配额正常"
    _check(checks, "网络", "OpenAlex 配额", _openalex_quota)

    def _s2():
        resp = httpx.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": "multi-agent", "limit": 1, "fields": "title"}, timeout=10)
        if resp.status_code == 429:
            return ("无 key 限流（仅影响作者订阅频率，重试兜底）", "warn")
        resp.raise_for_status()
        return "HTTP 200"
    _check(checks, "网络", "Semantic Scholar", _s2)

    def _ar5iv():
        resp = httpx.get("https://ar5iv.labs.arxiv.org/html/1705.05870",
                         timeout=8, follow_redirects=True)
        # ar5iv 对部分论文返回 404 属正常（可选全文源）
        if resp.status_code in (200, 404):
            return f"HTTP {resp.status_code}" + ("（该样本无预渲染，全文源整体可用性以实际抓取为准）" if resp.status_code == 404 else "")
        raise RuntimeError(f"HTTP {resp.status_code}")
    _check(checks, "网络", "ar5iv 全文镜像", _ar5iv)

    # ── LLM 组：ping + 快筛冒烟（各 1 次最小调用）──────────────
    def _llm_ping():
        from backend.ai.llm import build_chat, task_model
        model = task_model("enhance")
        chat = build_chat(model, thinking=False, timeout=20)
        chat.invoke("ping")
        base = __import__("os").environ.get("OPENAI_BASE_URL", "")
        return f"{model} @ {base.split('//')[-1].split('/')[0]}"
    _check(checks, "LLM", "供应商连通", _llm_ping)

    def _quick_smoke():
        from backend.ai.quick_filter import build_quick_filter, quick_filter_paper
        chain = build_quick_filter()
        keep, reason = quick_filter_paper(
            {"title": "Multi-Agent Reinforcement Learning with Partial Observability",
             "summary": "We study decentralized coordination of agents under partial observability."},
            chain,
            {"direction": "multi-agent reinforcement learning", "keywords": ["MARL", "POMDP"]},
        )
        return f"判定={'相关' if keep else '不相关'} · 解析链路正常"
    _check(checks, "LLM", "快筛冒烟", _quick_smoke)

    # ── 存储与调度组：只读不写 ─────────────────────────────────
    def _db():
        from backend.db import get_conn
        conn = get_conn()
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("papers", "ai_results", "feedback")}
        return f"papers={counts['papers']} ai={counts['ai_results']} feedback={counts['feedback']}"
    _check(checks, "存储", "SQLite 读写", _db)

    def _schedule():
        from backend.jobs import get_scheduled_at
        planned = get_scheduled_at() or {}
        if not planned:
            return ("调度器未启动（无夜间任务计划）", "warn")
        first = sorted(planned.values())[0]
        return f"下次任务 {first}（共 {len(planned)} 项）"
    _check(checks, "调度", "时间表", _schedule)

    # ── 版本与前端资源组 ───────────────────────────────────────
    def _version():
        import subprocess
        from backend.api import _DAEMON_VERSION
        disk = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip()
        if disk and disk != _DAEMON_VERSION:
            return (f"daemon={_DAEMON_VERSION} 磁盘={disk}，重启后生效新代码", "warn")
        return f"一致（{disk or _DAEMON_VERSION}）"
    _check(checks, "版本", "代码一致性", _version)

    def _web_assets():
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        missing = [str(p) for p in ("web/index.html", "web/js/app.js", "web/css/tokens.css")
                   if not (root / p).exists()]
        if missing:
            raise RuntimeError(f"缺失: {missing}")
        return "index/js/css 齐全"
    _check(checks, "前端", "静态资源", _web_assets)

    report = {
        "started": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "ok": sum(1 for c in checks if c["status"] == "ok"),
        "warn": sum(1 for c in checks if c["status"] == "warn"),
        "fail": sum(1 for c in checks if c["status"] == "fail"),
        "total": len(checks),
    }
    _last_report = report
    logger.info(f"[selftest] 完成: {report['ok']}✓ {report['warn']}⚠ {report['fail']}✗ / {report['total']}")
    return report


def run_selftest_job():
    """后台任务入口：更新 /api/jobs 状态，失败不让线程崩。"""
    from backend.jobs import _set_job_status
    _set_job_status("selftest", "running")
    try:
        r = run_selftest()
        msg = f"{r['ok']}✓ {r['warn']}⚠ {r['fail']}✗ / {r['total']}"
        _set_job_status("selftest", "done", msg)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[selftest] 失败: {e}", exc_info=True)
        _set_job_status("selftest", "error", str(e)[:160])
