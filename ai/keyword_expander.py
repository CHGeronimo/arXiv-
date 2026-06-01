"""ai/keyword_expander.py — LLM-based keyword expansion for broader paper discovery."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    dotenv.load_dotenv(_env_path)

EXPAND_SYSTEM = """You are a research literature search expert. Given a researcher's direction and seed keywords, generate expanded search queries that will catch relevant papers missed by exact keyword matching.

Rules:
1. Include common abbreviations (e.g. "NeRF" → also "neural radiance fields")
2. Include emerging sub-topics within the research direction
3. Include related methodology terms (e.g. "diffusion models" → also "score-based generative models")
4. Each query should be a short phrase (1-4 words), not a sentence
5. Keep the original seed keywords in the output
6. Aim for 15-25 total queries
7. Remove duplicates and near-duplicates
8. Respond with valid JSON: {{"queries": ["query1", "query2", ...]}}"""

EXPAND_TEMPLATE = """Research Direction: {direction}
Seed Keywords: {keywords}
Quality Criteria: {quality_criteria}
Liked Papers: {liked}
Disliked Papers: {disliked}

Generate expanded search queries for Semantic Scholar paper search."""

_CACHE_PATH = Path("data/expanded_keywords.json")


def expand_keywords(
    direction: str,
    seed_keywords: list[str],
    quality_criteria: str = "",
    liked: list[str] | None = None,
    disliked: list[str] | None = None,
    force: bool = False,
) -> list[str]:
    """Expand seed keywords using LLM. Results are cached until seed keywords change."""
    cache_key = _cache_key(direction, seed_keywords)

    if not force:
        cached = _load_cache()
        if cached and cached.get("key") == cache_key:
            logger.info(f"Using cached expanded keywords ({len(cached['queries'])} queries)")
            return cached["queries"]

    model_name = os.environ.get("KEYWORD_MODEL", os.environ.get("MODEL_NAME", "deepseek-v4-flash"))
    llm = ChatOpenAI(model=model_name, temperature=0.3)
    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPAND_SYSTEM),
        ("human", EXPAND_TEMPLATE),
    ])
    chain = prompt | llm

    response = chain.invoke({
        "direction": direction,
        "keywords": ", ".join(seed_keywords),
        "quality_criteria": quality_criteria,
        "liked": "\n".join((liked or [])[-5:]),
        "disliked": "\n".join((disliked or [])[-5:]),
    })

    try:
        data = json.loads(response.content)
        queries = data.get("queries", seed_keywords)
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Failed to parse LLM keyword expansion, falling back to seeds")
        queries = seed_keywords

    # Deduplicate (case-insensitive)
    seen: set[str] = set()
    unique: list[str] = []
    for q in queries:
        ql = q.lower().strip()
        if ql and ql not in seen:
            seen.add(ql)
            unique.append(q)

    logger.info(f"Expanded {len(seed_keywords)} keywords → {len(unique)} queries")

    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(
        json.dumps({"key": cache_key, "queries": unique}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return unique


def _cache_key(direction: str, keywords: list[str]) -> str:
    """Simple hash of inputs to detect when cache is stale."""
    import hashlib
    blob = f"{direction}|{'|'.join(sorted(keywords))}"
    return hashlib.md5(blob.encode()).hexdigest()[:12]


def _load_cache() -> dict | None:
    if not _CACHE_PATH.exists():
        return None
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
