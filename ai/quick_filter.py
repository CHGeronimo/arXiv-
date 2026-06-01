import os
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .structure import QuickFilter

logger = logging.getLogger(__name__)

QUICK_SYSTEM = """You are a paper relevance classifier for a CS PhD researcher.
Given the paper title and abstract, and the researcher's profile, classify if this paper is relevant enough for detailed analysis.

IMPORTANT: Be generous — classify as relevant if there is ANY chance the paper relates to the researcher's work.
Only mark as not-relevant if the paper is clearly in a completely different field.

Respond with valid JSON: {{"is_relevant": bool, "relevance_reason": "one sentence"}}"""

QUICK_TEMPLATE = """Research Direction: {research_direction}
Keywords: {keywords}

Paper Title: {title}

Abstract:
{content}"""


def build_quick_filter(model_name: str | None = None):
    model = model_name or os.environ.get("QUICK_FILTER_MODEL", "deepseek-chat")
    llm = ChatOpenAI(model=model).with_structured_output(QuickFilter, method="json_mode")
    prompt = ChatPromptTemplate.from_messages([
        ("system", QUICK_SYSTEM),
        ("human", QUICK_TEMPLATE),
    ])
    return prompt | llm


def quick_filter_paper(paper: dict, chain, profile: dict) -> bool:
    """Return True if the paper passes the quick relevance filter.

    Rejects papers clearly outside the research direction to avoid
    the cost of full AI enhancement (~86% of arXiv papers are rejected).
    On failure, defaults to True (conservative: let full enhancement decide).
    """
    try:
        result: QuickFilter = chain.invoke({
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
            "title": paper.get("title", ""),
            "content": paper.get("summary", "")[:1000],
        })
        return result.is_relevant
    except Exception as e:
        logger.warning(f"Quick filter failed for {paper.get('id','?')}: {e}, defaulting to relevant")
        return True
