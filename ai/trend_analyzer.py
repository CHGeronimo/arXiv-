"""Weekly trend radar generation."""

import json
import logging
import os
from datetime import datetime, timedelta

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from db import get_conn, queue_write
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


def _get_chain():
    global _CHAIN
    if _CHAIN is None:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        llm = ChatOpenAI(model=model_name).with_structured_output(TrendReport, method="json_mode")
        _CHAIN = ChatPromptTemplate.from_template(_TREND_PROMPT) | llm
    return _CHAIN


def generate_trend_report(week_start: str | None = None) -> dict | None:
    if week_start is None:
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

    conn = get_conn()
    week_ago = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")

    rows = conn.execute("""
        SELECT p.title, a.tldr, a.method, a.result
        FROM papers p JOIN ai_results a ON p.id = a.paper_id
        WHERE p.published_date >= ? AND p.published_date < ?
        ORDER BY a.relevance_score DESC LIMIT 50
    """, (week_ago, week_start)).fetchall()

    if not rows:
        logger.info(f"趋势报告周 {week_start} 无论文")
        return None

    summaries = "\n".join(f"- {r['title']}: {r['tldr']}" for r in rows[:30])

    from .enhance import load_research_profile
    profile = load_research_profile()

    try:
        report: TrendReport = _get_chain().invoke({
            "count": len(rows), "paper_summaries": summaries,
            "research_direction": profile.get("direction", ""),
        })
    except Exception as e:
        logger.error(f"趋势报告生成失败: {e}")
        return None

    result = {
        "week_start": week_start,
        "new_methods": report.new_methods,
        "solved_problems": report.solved_problems,
        "controversies": report.controversies,
        "opportunities": report.opportunities,
        "paper_count": len(rows),
    }
    queue_write(
        "INSERT OR REPLACE INTO trend_reports (week_start, new_methods, solved_problems, controversies, opportunities, paper_count) VALUES (?,?,?,?,?,?)",
        tuple(result.values()),
    )
    return result
