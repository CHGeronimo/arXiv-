"""Weekly trend radar generation."""

import json
import logging
import os
from datetime import datetime, timedelta

from langchain_core.prompts import ChatPromptTemplate

from db import get_conn
from .llm import build_chat
from .structure import TrendReport

logger = logging.getLogger(__name__)

_TREND_PROMPT = """Analyze this week's AI research papers and identify trends.

## Papers from the past 7 days ({count} papers):
{paper_summaries}

## User's Research Direction: {research_direction}

Identify:
1. New methods or techniques that emerged
2. Problems that appear solved or significantly advanced
3. Controversies or conflicting findings
4. Research opportunities visible from these papers

Respond with valid JSON matching the TrendReport schema."""

_CHAIN = None
_RAW_CHAIN = None


def _get_raw_chain():
    global _RAW_CHAIN
    if _RAW_CHAIN is None:
        model_name = os.environ.get("MODEL_NAME", "glm-5.3-flash")
        # 思考模式 + 50篇论文长prompt：默认120s超时不够（实测 Request timed out）
        llm = build_chat(model_name, thinking=True, timeout=300,
                         model_kwargs={"response_format": {"type": "json_object"}})
        _RAW_CHAIN = ChatPromptTemplate.from_template(_TREND_PROMPT) | llm
    return _RAW_CHAIN


def generate_trend_report(week_start: str | None = None) -> dict | None:
    if week_start is None:
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

    conn = get_conn()
    # 按入库时间取本周论文（published_date 是投稿日：会议/引文论文都是老日期，
    # 按它筛会把本周新发现的大量论文漏掉——与 digest 的修复同类）
    today_str = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"[trend] ▶ 生成周报 {week_start}")
    rows = conn.execute("""
        SELECT p.title, a.tldr, a.method, a.result
        FROM papers p JOIN ai_results a ON p.id = a.paper_id
        WHERE p.created_at >= ?
        AND a.recommendation != 'ignore'
        ORDER BY a.relevance_score DESC LIMIT 50
    """, (f"{week_start} 00:00:00",)).fetchall()

    if not rows:
        logger.info(f"[trend] ⊘ 周起始 {week_start} 无论文入库")
        return None

    # 20 篇足够覆盖一周动态；过长 prompt 会把思考模式的响应时间拖过超时
    summaries = "\n".join(
        f"- {r['title']}: {(r['tldr'] or '')[:120]}" for r in rows[:20]
    )

    from .enhance import load_research_profile
    profile = load_research_profile()

    try:
        raw_resp = _get_raw_chain().invoke({
            "count": len(rows), "paper_summaries": summaries,
            "research_direction": profile.get("direction", ""),
        })
        raw_text = raw_resp.content if hasattr(raw_resp, 'content') else str(raw_resp)
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
        "week_start": week_start,
        "new_methods": report.new_methods,
        "solved_problems": report.solved_problems,
        "controversies": report.controversies,
        "opportunities": report.opportunities,
        "paper_count": len(rows),
    }
    conn.execute(
        "INSERT OR REPLACE INTO trend_reports (week_start, new_methods, solved_problems, controversies, opportunities, paper_count, generated_at) VALUES (?,?,?,?,?,?,datetime('now'))",
        (result["week_start"], result["new_methods"], result["solved_problems"],
         result["controversies"], result["opportunities"], result["paper_count"]),
    )
    conn.commit()
    logger.info(f"[trend] ✔ 周报完成: {result['week_start']} ({result['paper_count']} 篇)")
    return result
