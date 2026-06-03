"""Deep full-text analysis for high-quality papers."""
from __future__ import annotations

import logging
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .structure import FulltextAnalysis
from .fulltext_fetcher import fetch_and_extract
from .enhance import load_research_profile

logger = logging.getLogger(__name__)

_FULLTEXT_PROMPT = """You are a research paper analyst performing deep analysis of a paper's full text.

## Researcher Profile
Direction: {research_direction}
Keywords: {keywords}

## Paper Title
{title}

## Abstract
{abstract}

## Full Text Sections
{sections_text}

Analyze this paper's full text in detail. Focus on:
1. **Method Implementation**: How exactly does the method work? Architecture, algorithms, training procedure.
2. **Experimental Design**: Datasets, baselines, metrics, ablation studies, evaluation protocol.
3. **Key Results**: Specific quantitative results, comparisons with baselines, state-of-the-art achievements.
4. **Limitations**: Stated or inferred limitations, assumptions, scalability issues, negative results.
5. **Reproducibility**: Is code available? Are hyperparameters specified? Are datasets accessible?
6. **Relevance to Profile**: Which techniques could transfer to the user's research? What gaps does this fill?

Respond with valid JSON using these exact keys: "method_implementation", "experimental_design", "key_results_detail", "limitations", "reproducibility", "relevance_to_profile"."""

_CHAIN = None


def _get_chain():
    global _CHAIN
    if _CHAIN is None:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        llm = ChatOpenAI(model=model_name).with_structured_output(FulltextAnalysis, method="json_mode")
        _CHAIN = ChatPromptTemplate.from_template(_FULLTEXT_PROMPT) | llm
    return _CHAIN


def analyze_fulltext(paper: dict, profile: dict | None = None) -> Optional[dict]:
    """Fetch full text and run deep analysis for a paper.

    Only works for arXiv papers (ar5iv HTML available).
    Returns analysis dict or None if fetch/analysis fails.
    """
    source = paper.get("source", "")
    arxiv_id = paper.get("id", "")

    if source != "arxiv":
        logger.debug(f"Skipping fulltext for non-arXiv paper {arxiv_id} (source={source})")
        return None

    sections = fetch_and_extract(arxiv_id)
    if not sections:
        logger.warning(f"未能从 {arxiv_id} 提取任何章节")
        return None

    # Format sections for prompt
    sections_text = ""
    for name, text in sections.items():
        sections_text += f"### {name.title()}\n{text}\n\n"

    # Truncate to ~8000 chars to control token cost
    if len(sections_text) > 8000:
        sections_text = sections_text[:8000]

    if profile is None:
        profile = load_research_profile()

    chain = _get_chain()

    try:
        result: FulltextAnalysis = chain.invoke({
            "title": paper.get("title", ""),
            "abstract": paper.get("summary", ""),
            "sections_text": sections_text,
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
        })
    except Exception as e:
        logger.error(f"正文分析失败 {arxiv_id}: {e}")
        return None

    return {
        "paper_id": arxiv_id,
        "method_implementation": result.method_implementation,
        "experimental_design": result.experimental_design,
        "key_results_detail": result.key_results_detail,
        "limitations": result.limitations,
        "reproducibility": result.reproducibility,
        "relevance_to_profile": result.relevance_to_profile,
    }
