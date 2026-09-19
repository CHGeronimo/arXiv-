import json
import logging
import os
import re

from langchain_core.prompts import ChatPromptTemplate

from .llm import build_chat, task_model

logger = logging.getLogger(__name__)

QUICK_SYSTEM = """You are a paper relevance classifier for a CS PhD researcher.
Given the paper title and abstract, and the researcher's profile, classify if this paper is relevant enough for detailed analysis.

IMPORTANT: Be generous — classify as relevant if there is ANY chance the paper relates to the researcher's work.
Only mark as not-relevant if the paper is clearly in a completely different field.

Respond with valid JSON: {{"is_relevant": bool, "relevance_reason": "one sentence"}}"""

QUICK_TEMPLATE = """Research Direction: {research_direction}
Keywords: {keywords}
Preferred Topics: {liked_topics}
Disliked Topics: {disliked_topics}

Paper Title: {title}

Abstract:
{content}"""


def build_quick_filter(model_name: str | None = None):
    model = model_name or task_model("quick_filter")
    # 不用 with_structured_output：GLM 偶尔包 {"answer": "..."} 信封导致
    # pydantic 严格校验失败（实测 4% 论文因此跳过预筛直进昂贵增强）——
    # 自己解析 + 解包容错更稳
    llm = build_chat(model, thinking=False)
    prompt = ChatPromptTemplate.from_messages([
        ("system", QUICK_SYSTEM),
        ("human", QUICK_TEMPLATE),
    ])
    return prompt | llm


def quick_filter_paper(paper: dict, chain, profile: dict) -> tuple[bool, str]:
    """Classify a paper's relevance. Returns (is_relevant, relevance_reason).

    The reason is the LLM's one-sentence explanation — persisted by callers
    so rejected papers can be audited with human-readable justification.
    On failure, defaults to (True, "") (conservative: let full enhancement decide).
    """
    try:
        resp = chain.invoke({
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
            "liked_topics": ", ".join(profile.get("liked_topics", [])[-100:]),
            "disliked_topics": ", ".join(profile.get("disliked_topics", [])[-100:]),
            "title": paper.get("title", ""),
            "content": paper.get("summary", "")[:1000],
        })
        content = (resp.content or "").strip()
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if m:
            content = m.group()
        data = json.loads(content)
        # GLM 信封形态：{"answer": "{\"is_relevant\": ...}"} → 解包内层
        if isinstance(data.get("answer"), str):
            try:
                inner = json.loads(data["answer"])
                if isinstance(inner, dict):
                    data = inner
            except json.JSONDecodeError:
                pass
        if "is_relevant" not in data:
            logger.warning(f"快速过滤响应缺 is_relevant，默认保留: {content[:80]}")
            return True, ""
        return bool(data.get("is_relevant")), str(data.get("relevance_reason", "")).strip()
    except Exception as e:
        logger.warning(f"快速过滤失败 {paper.get('id','?')}: {e}，默认保留")
        return True, ""
