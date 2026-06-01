"""Knowledge card extraction from AI-enhanced papers."""

import json
import logging
import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .structure import KnowledgeCard

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """You are a research knowledge extraction assistant.

Given a paper's title, abstract, and AI analysis, extract a structured knowledge card.

## Paper Title
{title}

## Abstract
{abstract}

## AI Analysis
- TL;DR: {tldr}
- Motivation: {motivation}
- Method: {method}
- Result: {result}
- Conclusion: {conclusion}

## User's Research Direction
{research_direction}

Extract:
1. **Problem**: What specific problem or research question does this paper address? One clear sentence.
2. **Method**: What is the core method, technique, or approach proposed? One sentence.
3. **Result**: What is the key result or finding? Include metrics if available. One sentence.
4. **Keywords**: 5-10 technical keywords characterizing this paper's contribution and domain.
5. **Relation to Profile**: How does this relate to the user's research direction?

Respond with valid JSON matching the KnowledgeCard schema."""

_CHAIN = None


def _get_chain():
    global _CHAIN
    if _CHAIN is None:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        llm = ChatOpenAI(model=model_name).with_structured_output(KnowledgeCard, method="json_mode")
        _CHAIN = ChatPromptTemplate.from_template(_EXTRACT_PROMPT) | llm
    return _CHAIN


def extract_knowledge_card(paper: dict, profile: dict | None = None) -> dict | None:
    """Extract a structured knowledge card from an AI-enhanced paper.

    Produces problem/method/result/keywords/relation fields used by the
    knowledge graph and clustering pipeline. Returns None if the paper
    lacks AI enhancement data.
    """
    ai = paper.get("AI") or {}
    if not ai.get("tldr") and not ai.get("method"):
        logger.debug(f"Skipping knowledge extraction for {paper.get('id')}: no AI data")
        return None

    if profile is None:
        from .enhance import load_research_profile
        profile = load_research_profile()

    chain = _get_chain()

    try:
        card: KnowledgeCard = chain.invoke({
            "title": paper.get("title", ""),
            "abstract": paper.get("summary", ""),
            "tldr": ai.get("tldr", ""),
            "motivation": ai.get("motivation", ""),
            "method": ai.get("method", ""),
            "result": ai.get("result", ""),
            "conclusion": ai.get("conclusion", ""),
            "research_direction": profile.get("direction", ""),
        })
    except Exception as e:
        logger.error(f"Knowledge extraction failed for {paper.get('id')}: {e}")
        return None

    return {
        "paper_id": paper["id"],
        "problem": card.problem,
        "method_extracted": card.method_extracted,
        "result_extracted": card.result_extracted,
        "keywords": json.dumps(card.keywords, ensure_ascii=False),
        "relation_to_profile": card.relation_to_profile,
        "extracted_at": None,
    }


def extract_knowledge_card_dict(paper: dict, profile: dict | None = None) -> dict:
    result = extract_knowledge_card(paper, profile)
    if result is None:
        return {}

    keywords = result.get("keywords", "[]")
    if isinstance(keywords, str):
        try:
            keywords = json.loads(keywords)
        except json.JSONDecodeError:
            keywords = []

    return {
        "paper_id": result["paper_id"],
        "problem": result["problem"],
        "method_extracted": result["method_extracted"],
        "result_extracted": result["result_extracted"],
        "keywords": keywords,
        "relation_to_profile": result["relation_to_profile"],
    }
