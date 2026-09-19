"""Weekly trend radar generation."""

import json
import logging
import os
from datetime import datetime, timedelta

from langchain_core.prompts import ChatPromptTemplate

from backend.db import get_conn
from .llm import build_chat, task_model
from .structure import TrendReport

logger = logging.getLogger(__name__)

_TREND_PROMPT = """Analyze {period_label} AI research papers and identify trends.

## Papers from {period_label} ({count} papers, {scale_hint}):
{paper_summaries}

## User's Research Direction: {research_direction}

Identify:
1. New methods or techniques that emerged
2. Problems that appear solved or significantly advanced
3. Controversies or conflicting findings
4. Research opportunities visible from these papers

Respond with valid JSON with EXACTLY these four keys:
"new_methods", "solved_problems", "controversies", "opportunities".
Each key MUST be a non-empty array of 2-5 items; each item is a short string
or {{"name": "...", "description": "..."}}. Do not return empty arrays.
用简体中文撰写所有内容（方法名/博弈术语等标准术语保留英文）。"""

_CHAIN = None
_RAW_CHAIN = None


def _get_raw_chain():
    global _RAW_CHAIN
    if _RAW_CHAIN is None:
        model_name = task_model("trend")
        # 思考模式 + 50篇论文长prompt：默认120s超时不够（实测 Request timed out）
        llm = build_chat(model_name, thinking=True, timeout=300, priority=True,
                         model_kwargs={"response_format": {"type": "json_object"}})
        _RAW_CHAIN = ChatPromptTemplate.from_template(_TREND_PROMPT) | llm
    return _RAW_CHAIN


def generate_trend_report(week_start: str | None = None) -> dict | None:
    """Back-compat wrapper: weekly report."""
    return generate_trend_report_period("weekly", week_start)


def generate_trend_report_period(period_type: str = "weekly", period_key: str | None = None,
                                  window_end: str | None = None) -> dict | None:
    """Generate a weekly or monthly trend report.

    weekly:  period_key = 周一日期 'YYYY-MM-DD'（默认本周），窗口=该日起入库
    monthly: period_key = 'YYYY-MM'（默认本月），窗口=该月1日起入库
    window_end: 可选上界（'YYYY-MM-DD'），存档场景防止跨期污染。
    结果存 trend_reports（week_start=period_key, period_type 标记），历史自动沉淀。
    """
    if period_type not in ("weekly", "monthly"):
        return None
    today = datetime.now()
    if period_type == "weekly":
        if period_key is None:
            period_key = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        window_start = period_key
        period_label = f"本周（{period_key} 起）"
        scale_hint = "these papers from the current week"
        prompt_limit = 20
    else:
        if period_key is None:
            period_key = today.strftime("%Y-%m")
        window_start = period_key + "-01"
        period_label = f"本月（{period_key}）"
        scale_hint = ("these papers from the whole month — identify month-scale "
                      "patterns, dominant research shifts and emerging directions, "
                      "not weekly noise")
        prompt_limit = 40

    conn = get_conn()
    # 按入库时间取窗口内论文（published_date 是投稿日：会议/引文论文都是老日期）
    logger.info(f"[trend] ▶ 生成{'周' if period_type == 'weekly' else '月'}报 {period_key}")
    where = "WHERE p.created_at >= ?"
    params: list = [f"{window_start} 00:00:00"]
    if window_end:
        where += " AND p.created_at < ?"
        params.append(f"{window_end} 00:00:00")
    rows = conn.execute(f"""
        SELECT p.title, a.tldr, a.method, a.result
        FROM papers p JOIN ai_results a ON p.id = a.paper_id
        {where}
        AND a.recommendation != 'ignore'
        ORDER BY a.relevance_score DESC LIMIT 100
    """, params).fetchall()

    if not rows:
        logger.info(f"[trend] ⊘ {period_key} 无论文入库")
        return None

    summaries = "\n".join(
        f"- {r['title']}: {(r['tldr'] or '')[:120]}" for r in rows[:prompt_limit]
    )

    from .enhance import load_research_profile
    profile = load_research_profile()

    try:
        raw_resp = _get_raw_chain().invoke({
            "count": len(rows), "paper_summaries": summaries,
            "research_direction": profile.get("direction", ""),
            "period_label": period_label, "scale_hint": scale_hint,
        })
        raw_text = raw_resp.content if hasattr(raw_resp, 'content') else str(raw_resp)
        logger.info(f"[trend] LLM 原始响应 {len(raw_text)} 字符: {raw_text[:200]}")
        data = json.loads(raw_text)
    except Exception as e:
        logger.error(f"趋势报告 LLM 调用失败: {e}")
        return None

    # Normalize LLM field name variations
    if "research_opportunities" in data and "opportunities" not in data:
        data["opportunities"] = data.pop("research_opportunities")
    if "advanced_problems" in data and "solved_problems" not in data:
        data["solved_problems"] = data.pop("advanced_problems")
    if "problems_advanced" in data and "solved_problems" not in data:
        data["solved_problems"] = data.pop("problems_advanced")
    if "controversies_or_conflicts" in data and "controversies" not in data:
        data["controversies"] = data.pop("controversies_or_conflicts")

    report = TrendReport.from_lists(data)

    result = {
        "week_start": period_key,
        "new_methods": report.new_methods,
        "solved_problems": report.solved_problems,
        "controversies": report.controversies,
        "opportunities": report.opportunities,
        "paper_count": len(rows),
        "period_type": period_type,
    }
    conn.execute(
        "INSERT OR REPLACE INTO trend_reports (week_start, new_methods, solved_problems, controversies, opportunities, paper_count, period_type, generated_at) VALUES (?,?,?,?,?,?,?,datetime('now'))",
        (result["week_start"], result["new_methods"], result["solved_problems"],
         result["controversies"], result["opportunities"], result["paper_count"], period_type),
    )
    conn.commit()
    logger.info(f"[trend] ✔ {'周' if period_type == 'weekly' else '月'}报完成: {result['week_start']} ({result['paper_count']} 篇)")
    return result
