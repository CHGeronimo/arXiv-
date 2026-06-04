"""Weekly trend radar generation."""

import json
import logging
import os
from datetime import datetime, timedelta

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from db import get_conn
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
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        llm = ChatOpenAI(model=model_name, model_kwargs={"response_format": {"type": "json_object"}})
        _RAW_CHAIN = ChatPromptTemplate.from_template(_TREND_PROMPT) | llm
    return _RAW_CHAIN


def generate_trend_report(week_start: str | None = None) -> dict | None:
    if week_start is None:
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

    conn = get_conn()
    # Cover from week_start to today (not just the previous week)
    today_str = datetime.now().strftime("%Y-%m-%d")

    rows = conn.execute("""
        SELECT p.title, a.tldr, a.method, a.result
        FROM papers p JOIN ai_results a ON p.id = a.paper_id
        WHERE p.published_date >= ? AND p.published_date <= ?
        AND a.recommendation != 'ignore'
        ORDER BY a.relevance_score DESC LIMIT 50
    """, (week_start, today_str)).fetchall()

    if not rows:
        logger.info(f"趋势报告周 {week_start} 无论文")
        return None

    summaries = "\n".join(f"- {r['title']}: {r['tldr']}" for r in rows[:30])

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
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO trend_reports (week_start, new_methods, solved_problems, controversies, opportunities, paper_count) VALUES (?,?,?,?,?,?)",
        tuple(result.values()),
    )
    conn.commit()
    return result
