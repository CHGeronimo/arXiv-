"""Idea feasibility check — search existing papers and analyze differentiation."""

import json
import logging
import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from db import get_conn

logger = logging.getLogger(__name__)


class IdeaAnalysis(BaseModel):
    feasibility: str = Field(description="high/medium/low — how feasible is this idea given existing work")
    novelty: str = Field(description="high/medium/low — how novel compared to existing papers")
    related_work: str = Field(description="2-4 sentence summary of closest existing work found")
    differentiation: str = Field(description="how to differentiate from existing work, specific suggestions")
    risks: str = Field(description="main risks or challenges, 1-3 items")


_IDEA_PROMPT = """Analyze this research idea against existing papers.

## Research Idea
{idea}

## User's Research Direction
{research_direction}

## Most Relevant Existing Papers
{relevant_papers}

Assess:
1. Feasibility (high/medium/low) — is this achievable?
2. Novelty (high/medium/low) — is this already done?
3. Related work summary — what's closest?
4. Differentiation — how to make this novel?
5. Risks — what could go wrong?"""

_CHAIN = None


def _get_chain():
    global _CHAIN
    if _CHAIN is None:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        llm = ChatOpenAI(model=model_name).with_structured_output(IdeaAnalysis, method="json_mode")
        _CHAIN = ChatPromptTemplate.from_template(_IDEA_PROMPT) | llm
    return _CHAIN


def check_idea(idea: str) -> dict | None:
    """Check idea feasibility against existing papers in DB."""
    conn = get_conn()
    words = idea.split()[:5]
    conditions = " OR ".join(["(p.title LIKE ? OR a.tldr LIKE ? OR a.method LIKE ?)"] * len(words))
    params: list[str] = []
    for w in words:
        params.extend([f"%{w}%"] * 3)

    rows = conn.execute(f"""
        SELECT p.title, a.tldr, a.method, a.result, a.recommendation
        FROM papers p JOIN ai_results a ON p.id = a.paper_id
        WHERE {conditions}
        ORDER BY a.relevance_score DESC LIMIT 10
    """, params).fetchall()

    if not rows:
        relevant = "No directly relevant papers found in the database."
    else:
        relevant = "\n".join(f"- {r['title']}: {r['tldr']}" for r in rows)

    from .enhance import load_research_profile
    profile = load_research_profile()

    try:
        analysis: IdeaAnalysis = _get_chain().invoke({
            "idea": idea,
            "research_direction": profile.get("direction", ""),
            "relevant_papers": relevant,
        })
    except Exception as e:
        logger.error(f"Idea check failed: {e}")
        return None

    return analysis.model_dump()
