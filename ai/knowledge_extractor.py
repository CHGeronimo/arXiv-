"""Knowledge card extraction from AI-enhanced papers."""

import json
import logging
import os

from langchain_core.prompts import ChatPromptTemplate

from .llm import build_chat
from .structure import KnowledgeCard

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """你是一位学术知识抽取助手。请用中文回答。

根据论文的标题、摘要和 AI 分析结果，抽取结构化知识卡片。

## 论文标题
{title}

## 摘要
{abstract}

## AI 分析
- TL;DR: {tldr}
- 动机: {motivation}
- 方法: {method}
- 结果: {result}
- 结论: {conclusion}

## 用户研究方向
{research_direction}

请抽取以下信息：
1. **问题**: 这篇论文解决的具体问题或研究问题是什么？一句话概括。
2. **方法**: 提出的核心方法、技术或方案是什么？一句话概括。
3. **结果**: 关键结果或发现是什么？如有指标请包含。一句话概括。
4. **关键词**: 5-10 个表征该论文贡献和领域的技术关键词。
5. **与研究方向的关系**: 这篇论文与用户的研究方向有什么关联？

请用中文输出，使用以下 JSON 键名: "problem", "method_extracted", "result_extracted", "keywords", "relation_to_profile"。"""

_CHAIN = None


def _get_chain():
    global _CHAIN
    if _CHAIN is None:
        model_name = os.environ.get("MODEL_NAME", "glm-5.3-flash")
        llm = build_chat(model_name, thinking=False).with_structured_output(KnowledgeCard, method="json_mode")
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
        logger.error(f"知识卡片抽取失败 {paper.get('id')}: {e}")
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
