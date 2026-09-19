"""Idea feasibility check — search existing papers and analyze differentiation."""

import json
import logging
import os

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from backend.db import get_conn
from .llm import build_chat, task_model

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
5. Risks — what could go wrong?

Respond with valid JSON matching the IdeaAnalysis schema."""

_CHAIN = None


def _get_chain():
    global _CHAIN
    if _CHAIN is None:
        model_name = task_model("idea")
        # 不用 with_structured_output：GLM 思考模式偶发输出信封/围栏/嵌套值，
        # pydantic 严格校验直接抛 OutputParserException（2026-09-19 自检实锤）——
        # 改为裸调用 + _parse_idea 容错解析，与全文分析同款策略
        llm = build_chat(model_name, thinking=True)
        _CHAIN = ChatPromptTemplate.from_template(_IDEA_PROMPT) | llm
    return _CHAIN


def _parse_idea(content) -> IdeaAnalysis:
    """容错解析：正则取 JSON + answer 信封解包 + 标量拍平，失败返回空字段对象。"""
    import json as _json
    import re as _re
    text = content if isinstance(content, str) else getattr(content, "content", str(content))
    data: dict = {}
    m = _re.search(r"\{.*\}", text, _re.DOTALL)
    if m:
        try:
            data = _json.loads(m.group())
        except _json.JSONDecodeError:
            data = {}
    if isinstance(data, dict) and isinstance(data.get("answer"), dict):
        data = data["answer"]
    if not isinstance(data, dict):
        data = {}

    def _s(key: str) -> str:
        v = data.get(key)
        if isinstance(v, (str, int, float)):
            return str(v)
        if isinstance(v, dict):
            return "；".join(f"{k}: {x}" for k, x in v.items())
        if isinstance(v, list):
            return "；".join(str(x) for x in v)
        return ""

    return IdeaAnalysis(
        feasibility=_s("feasibility"), novelty=_s("novelty"),
        related_work=_s("related_work"), differentiation=_s("differentiation"),
        risks=_s("risks"),
    )


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
        resp = _get_chain().invoke({
            "idea": idea,
            "research_direction": profile.get("direction", ""),
            "relevant_papers": relevant,
        })
        analysis = _parse_idea(resp)
    except Exception as e:
        logger.error(f"想法可行性检查失败: {e}")
        return None

    return analysis.model_dump()
