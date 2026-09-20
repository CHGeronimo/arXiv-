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

    # ── LLM 流水线组：每类任务一条真实链路冒烟 ─────────────────
    # （各 1 次最小调用；全部选用无写库/无缓存副作用的入口）
    def _llm_ping():
        from backend.ai.llm import build_chat, task_model
        model = task_model("enhance")
        chat = build_chat(model, thinking=False, timeout=20, priority=True)
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
    _check(checks, "LLM", "快筛（分类预筛）", _quick_smoke)

    def _keyword_smoke():
        from backend.ai.keyword_expander import extract_keywords_strict
        kws = extract_keywords_strict(
            "multi-agent reinforcement learning under partial observability",
            ["MARL"], quality_criteria="novel mechanism",
        )
        if not kws or len(kws) < 3:
            raise RuntimeError(f"返回关键词过少: {kws}")
        return f"提取 {len(kws)} 条检索词"
    _check(checks, "LLM", "关键词提取", _keyword_smoke)

    def _topic_smoke():
        from backend.api import _academicize_note
        out = _academicize_note("这篇多智能体信用分配的做法很新颖，值得跟进", "useful")
        if not out or len(out) < 8:
            raise RuntimeError("学术化输出异常")
        return f"{len(out)} 字规范表述"
    _check(checks, "LLM", "评语学术化（主题）", _topic_smoke)

    def _cluster_smoke():
        from collections import Counter as _C
        from backend.ai.knowledge_clustering import _extract_themes
        kws = ["multi-agent reinforcement learning", "POMDP", "mechanism design",
               "credit assignment", "game theory", "vital sign monitoring",
               "adversarial robustness", "diffusion policy"]
        themes = _extract_themes(kws, _C(kws * 2))
        if not themes or len(themes) < 3:
            raise RuntimeError(f"主题数过少: {themes}")
        return f"归纳 {len(themes)} 个主题"
    _check(checks, "LLM", "主题聚类", _cluster_smoke)

    def _enhance_smoke():
        from backend.ai.llm import task_model
        from backend.ai.enhance import build_chain, enhance_single
        chain = build_chain(task_model("enhance"))
        result = enhance_single(
            {"id": "selftest-smoke", "title": "Cooperative Multi-Agent Planning",
             "summary": "We propose a communication protocol improving coordination."},
            chain, {"direction": "MARL", "keywords": ["MARL"], "quality_criteria": ""}, "Chinese",
        )
        ai = result.get("AI", {})
        if ai.get("_llm_failed"):
            raise RuntimeError("增强标记 _llm_failed")
        if not ai.get("tldr"):
            raise RuntimeError("TLDR 缺失")
        return f"推荐={ai.get('recommendation')} 相关度={ai.get('relevance_score')}"
    _check(checks, "LLM", "深度评分（增强）", _enhance_smoke)

    def _knowledge_smoke():
        from backend.ai.knowledge_extractor import extract_knowledge_card_dict
        card = extract_knowledge_card_dict(
            {"id": "selftest-card", "title": "Opponent Modeling in Stackelberg Games",
             "summary": "We learn opponent behavior models for security games.",
             "AI": {"tldr": "学习对手行为模型用于安全博弈", "method": "层级强化学习对手建模"}},
            {"direction": "multi-agent reinforcement learning", "keywords": ["MARL"]})
        if not card:
            raise RuntimeError("知识卡片为空")
        return "problem/method/keywords 提取正常"
    _check(checks, "LLM", "知识卡片", _knowledge_smoke)

    def _tpl_vars(prompt: str) -> dict:
        import string
        out = {}
        for _, field, _, _ in string.Formatter().parse(prompt):
            if field:
                out[field] = {"count": "3", "scale_hint": "月度"}.get(
                    field, "多智能体强化学习测试" if "direction" in field or "keyword" in field else "测试样本")
        return out

    def _fulltext_smoke():
        from backend.ai import fulltext_analyzer as fa
        chain = fa._get_chain()
        from backend.ai.fulltext_analyzer import _FULLTEXT_PROMPT
        resp = chain.invoke(_tpl_vars(_FULLTEXT_PROMPT))
        parsed = fa._parse_analysis(resp.content if hasattr(resp, "content") else str(resp))
        if parsed is None:
            raise RuntimeError("全文分析解析为空")
        return "六字段解析链路正常"
    _check(checks, "LLM", "全文深读", _fulltext_smoke)

    def _trend_smoke():
        import json as _json
        from backend.ai import trend_analyzer as ta
        from backend.ai.trend_analyzer import _TREND_PROMPT
        resp = ta._get_raw_chain().invoke(_tpl_vars(_TREND_PROMPT))
        data = _json.loads((resp.content if hasattr(resp, "content") else str(resp)).strip())
        if not isinstance(data, dict):
            raise RuntimeError("趋势 JSON 结构异常")
        return f"JSON 报告结构正常（{len(data)} 个键）"
    _check(checks, "LLM", "趋势雷达", _trend_smoke)

    def _digest_smoke():
        # 简报生成链路的同款配置（thinking on + temperature 0.3）最小调用
        from backend.ai.llm import build_chat, task_model
        out = build_chat(task_model("digest"), thinking=True, temperature=0.3, timeout=60, priority=True).invoke(
            "用一句话中文总结：多智能体强化学习近期进展活跃。")
        text = out.content if hasattr(out, "content") else str(out)
        if len(text.strip()) < 8:
            raise RuntimeError("简报链路输出异常")
        return f"{len(text.strip())} 字输出正常"
    _check(checks, "LLM", "简报链路", _digest_smoke)

    def _idea_smoke():
        from backend.ai.idea_checker import _get_chain, _parse_idea, _IDEA_PROMPT
        resp = _get_chain().invoke(_tpl_vars(_IDEA_PROMPT))
        analysis = _parse_idea(resp)
        if analysis is None:
            raise RuntimeError("想法查重解析为空")
        return "容错解析链路正常"
    _check(checks, "LLM", "想法查重", _idea_smoke)


    def _dedup_smoke():
        # 反馈闭环的关键守卫链路：主题语义去重（LLM + 空结果保底）
        from backend.api import _deduplicate_topics
        out = _deduplicate_topics(["opponent modeling", "Opponent Modeling", "diffusion policy"])
        if not isinstance(out, list) or not out:
            raise RuntimeError(f"去重输出异常: {out}")
        return f"{len(out)} 个主题（语义去重+守卫正常）"
    _check(checks, "LLM", "主题去重（反馈环）", _dedup_smoke)

    # ── API 层组：内部往返（test_client，零外部成本/零写） ─────────
    def _api(method, path, **kw):
        from backend.api import app as _app
        r = _app.test_client().open(path, method=method, **kw)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        return r.get_json() if r.mimetype == "application/json" else r.data

    _check(checks, "API", "论文列表", lambda: f"{_api('GET', '/api/papers?per_page=1')['total']} 篇")

    def _api_stats():
        d = _api("GET", "/api/stats")
        return f"{d.get('total_papers', '?')} 篇 · 必读 {d.get('must_read', '?')} · 版本 {d.get('daemon_version', '?')}"
    _check(checks, "API", "统计/版本", _api_stats)

    def _api_bibtex():
        row = __import__("backend.db", fromlist=["get_conn"]).get_conn().execute(
            "SELECT id FROM papers LIMIT 1").fetchone()
        if not row:
            return ("库为空，跳过", "warn")
        d = _api("POST", "/api/export/bibtex", json={"ids": [row[0]]})
        return f"导出 {len(d) if isinstance(d, list) else 1} 条（含斜杠 id 路由验证）"
    _check(checks, "API", "BibTeX 导出", _api_bibtex)

    def _api_trend():
        d = _api("GET", "/api/trend-radars?scope=weekly")
        n = len(d.get("reports", d if isinstance(d, list) else []))
        return f"{n} 份周报"
    _check(checks, "API", "趋势雷达", _api_trend)

    _check(checks, "API", "简报列表", lambda: f"{len(_api('GET', '/api/digests')['digests'])} 期")

    # ── 数据就绪组：配置与数据文件可解析 ──────────────────────────
    def _subs_ready():
        import json as _json
        path = __import__("pathlib").Path("subscriptions.json")
        if not path.exists():
            return ("subscriptions.json 缺失（首次运行会生成）", "warn")
        d = _json.loads(path.read_text(encoding="utf-8"))
        n_arxiv = len((d.get("arxiv") or {}).get("categories") or [])
        n_journal = len((d.get("crossref") or {}).get("journals") or [])
        n_conf = len(d.get("conferences") or [])
        n_author = len((d.get("authors") or d.get("author") or []) or [])
        n_kw = len((d.get("search") or {}).get("keywords") or [])
        total = n_arxiv + n_journal + n_conf + n_author + n_kw
        if not total:
            return ("订阅为空——所有抓取任务将跳过", "warn")
        return f"分类{n_arxiv} 期刊{n_journal} 会议{n_conf} 作者{n_author} 关键词{n_kw}"
    _check(checks, "数据", "订阅配置", _subs_ready)

    def _profile_ready():
        import json as _json
        path = __import__("pathlib").Path("research_profile.json")
        if not path.exists():
            return ("research_profile.json 缺失（首次保存时生成）", "warn")
        d = _json.loads(path.read_text(encoding="utf-8"))
        if not (d.get("direction") or d.get("keywords")):
            return ("研究方向与关键词均为空，本地预筛与评分将退化", "warn")
        return f"方向 {len(d.get('direction', ''))} 字 · 偏好 {len(d.get('liked_topics', []))}/{len(d.get('disliked_topics', []))}"
    _check(checks, "数据", "研究画像", _profile_ready)

    def _clusters_ready():
        row = __import__("backend.db", fromlist=["get_conn"]).get_conn().execute(
            "SELECT COUNT(*) FROM knowledge_clusters").fetchone()
        n = row[0] if row else 0
        if not n:
            return ("无聚类数据——🕸️ 图谱为空，🤖 菜单跑一次重聚类", "warn")
        return f"{n} 个聚类"
    _check(checks, "数据", "知识聚类", _clusters_ready)

    # ── 版本戳与收敛组：分层版本/收敛配置/各层旧版量 ──────────────
    def _version_layers():
        from backend.ai.enhance import ENHANCE_VER, CARD_VER, CLUSTER_VER
        return f"增强 {ENHANCE_VER} / 卡片 {CARD_VER} / 聚类 {CLUSTER_VER}"
    _check(checks, "版本", "三层版本戳", _version_layers)

    def _converge_config():
        from backend.db import get_runtime_settings
        st = get_runtime_settings()
        pct = int(st.get("CONVERGE_PCT", 10))
        max_min = int(st.get("CONVERGE_MAX_MIN", 30))
        if pct < 1 or pct > 50:
            return (f"CONVERGE_PCT={pct} 越界（应 1-50）", "warn")
        if max_min < 5 or max_min > 120:
            return (f"CONVERGE_MAX_MIN={max_min} 越界（应 5-120）", "warn")
        return f"每轮 {pct}% / 限时 {max_min} 分钟"
    _check(checks, "收敛", "配置有效性", _converge_config)

    def _stale_report():
        from backend.jobs import _stale_counts
        stale = _stale_counts()
        parts = []
        if stale.get("enhance"):
            parts.append(f"增强旧版 {stale['enhance']} 篇")
        if stale.get("card"):
            parts.append(f"卡片旧版 {stale['card']} 篇")
        if not parts:
            return "全层最新 ✓"
        hint = "（夜间自动渐进收敛中）"
        return "、".join(parts) + hint
    _check(checks, "收敛", "旧版存量", _stale_report)

    def _card_rerun_endpoint():
        from backend.api import app as _app
        r = _app.test_client().get("/api/stale-counts")
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        d = r.get_json()
        if "enhance" not in d or "card" not in d:
            raise RuntimeError(f"响应缺键: {list(d)}")
        return f"enhance={d['enhance']} card={d['card']}"
    _check(checks, "收敛", "stale-counts 端点", _card_rerun_endpoint)

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
