"""ai/keyword_expander.py — LLM-based keyword expansion for broader paper discovery.

Two-stage pipeline:
1. Direction mining: exhaustively extract every distinct research concept
   from the (possibly Chinese) direction description as canonical English
   terms, honoring liked/disliked feedback topics.
2. Query expansion: for seeds + mined concepts, generate search variants
   (abbreviations, full forms, sub-topic names, related methodology terms),
   targeting 40-90 total queries.

Successful results are cached until direction/keywords/feedback change.
Failed runs fall back to seed keywords WITHOUT caching, so a later run
(e.g. after topping up API credit) retries the LLM instead of reusing
the fallback.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

import dotenv
from langchain_core.prompts import ChatPromptTemplate

from .llm import build_chat, task_model

logger = logging.getLogger(__name__)

_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    dotenv.load_dotenv(_env_path)

MINE_SYSTEM = """You are a research literature search expert. A researcher describes their research direction (possibly in Chinese). Extract EVERY distinct searchable research concept from it.

Sweep the ENTIRE description and collect concepts from ALL of these angles whenever present:
- problem settings / environment assumptions (e.g. partially observable, non-stationary, dynamic uncertainty)
- methodologies (e.g. deep reinforcement learning, continual learning)
- theoretical tools (e.g. game theory, mechanism design)
- studied mechanisms and abilities (e.g. credit assignment, belief updating, collusion resistance, distributed coordination)
- model / problem classes (e.g. POMDP, Dec-POMDP, Markov game)
- evaluation properties (e.g. sample efficiency, generalization, robustness, interpretability)
- application domains (e.g. vital-sign monitoring, network security)

Rules:
1. Output canonical ENGLISH research terminology — translate Chinese concepts into the standard English terms used in paper titles/abstracts; keep English terms already in the text.
2. Each concept is a short phrase (1-5 words), never a sentence.
3. Be EXHAUSTIVE — do NOT drop minor sub-topics. A rich description should yield 20-40+ concepts.
4. Merge overlapping concepts into the most standard phrasing; no duplicates or near-duplicates.
5. "Liked topics" reveal extra themes the researcher cares about — include their distinct concepts too. "Disliked topics" must be excluded.
6. Respond with valid JSON: {{"concepts": ["concept1", "concept2", ...]}}"""

MINE_TEMPLATE = """Research Direction (may be Chinese):
{direction}

Quality Criteria: {quality_criteria}

Liked topics (extra signal of interest, include their distinct concepts):
{liked}

Disliked topics (EXCLUDE these themes):
{disliked}"""

EXPAND_SYSTEM = """You are a research literature search expert. Given seed keywords and mined research concepts, produce an exhaustive set of search queries that will catch all relevant papers missed by exact keyword matching.

Rules:
1. Keep ALL original seed keywords in the output.
2. Cover EVERY mined concept — generate 1-3 query variants for each.
3. Variants include: abbreviation AND full form (e.g. "NeRF" and "neural radiance fields"), established sub-topic names (e.g. "diffusion models" -> "score-based generative models"), closely related methodology terms, and how LLM-era papers phrase the topic (e.g. "multi-agent reinforcement learning" -> "LLM-based multi-agent coordination").
4. Each query is a short phrase (1-4 words), never a sentence.
5. All queries in canonical English research terminology.
6. Aim for {min_q}-{max_q} total queries, scaling with the number of concepts — more coverage is better than less.
7. Remove duplicates and near-duplicates.
8. Exclude anything similar to the disliked topics.
9. Respond with valid JSON: {{"queries": ["query1", "query2", ...]}}"""

EXPAND_TEMPLATE = """Research Direction: {direction}

Seed Keywords (must keep ALL of them):
{keywords}

Mined Concepts (cover EVERY one with 1-3 variants):
{concepts}

Quality Criteria: {quality_criteria}

Liked topics: {liked}
Disliked topics (exclude): {disliked}"""

_CACHE_PATH = Path("data/expanded_keywords.json")
_CACHE_VERSION = 2

MIN_QUERIES = 40
MAX_QUERIES = 90


def _get_llm():
    model_name = task_model("keyword")
    return build_chat(model_name, thinking=False, temperature=0.3)


def _llm_json(llm, system: str, template: str, inputs: dict, list_field: str, retries: int = 2):
    """Build a prompt|llm chain, invoke it, and parse a JSON object with a
    string-list field. Tolerates markdown fences around the JSON.

    Retries transient failures with backoff; deterministic errors like
    insufficient balance are not retried. Returns (items, last_error) —
    items is [] on failure.
    """
    chain = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", template),
    ]) | llm
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = chain.invoke(inputs)
            content = resp.content.strip()
            m = re.search(r'\{.*\}', content, re.DOTALL)
            if m:
                content = m.group()
            data = json.loads(content)
            items = data.get(list_field, [])
            if isinstance(items, list):
                return [str(q).strip() for q in items if isinstance(q, str) and q.strip()], None
            return [], ValueError(f"{list_field} 字段不是列表")
        except Exception as e:
            last_err = e
            msg = str(e)
            if "余额不足" in msg or "insufficient" in msg.lower():
                break  # 确定性错误，重试无意义
            if attempt < retries:
                wait = 5 * (attempt + 1)
                logger.warning(f"LLM 调用失败 ({list_field}) 第 {attempt + 1}/{retries + 1} 次: {e}，{wait}s 后重试")
                time.sleep(wait)
    logger.warning(f"LLM 调用/解析失败 ({list_field}): {last_err}")
    return [], last_err


def _dedup(items: list[str]) -> list[str]:
    """Case-insensitive dedup, preserving first occurrence order."""
    seen: set[str] = set()
    out: list[str] = []
    for q in items:
        ql = q.lower().strip()
        if ql and ql not in seen:
            seen.add(ql)
            out.append(q)
    return out


def _run_pipeline(
    direction: str,
    seed_keywords: list[str],
    quality_criteria: str,
    liked: list[str] | None,
    disliked: list[str] | None,
) -> tuple[list[str], int, list[Exception]]:
    """Run both LLM stages. Returns (merged_queries, n_concepts, errors)."""
    llm = _get_llm()
    liked_s = "\n".join((liked or [])[-100:])
    disliked_s = "\n".join((disliked or [])[-100:])

    # Stage 1: mine concepts from the direction description
    concepts, err1 = _llm_json(llm, MINE_SYSTEM, MINE_TEMPLATE, {
        "direction": direction,
        "quality_criteria": quality_criteria,
        "liked": liked_s or "(none)",
        "disliked": disliked_s or "(none)",
    }, "concepts")
    logger.info(f"方向概念挖掘: {len(concepts)} 个概念")

    # Stage 2: expand seeds + concepts into search queries
    n_concepts = len(concepts) or len(seed_keywords)
    min_q = max(MIN_QUERIES, n_concepts)
    max_q = max(MAX_QUERIES, n_concepts * 2)
    queries, err2 = _llm_json(llm, EXPAND_SYSTEM, EXPAND_TEMPLATE, {
        "min_q": min_q,
        "max_q": max_q,
        "direction": direction,
        "keywords": ", ".join(seed_keywords),
        "concepts": "\n".join(f"- {c}" for c in concepts) or "(none)",
        "quality_criteria": quality_criteria,
        "liked": liked_s or "(none)",
        "disliked": disliked_s or "(none)",
    }, "queries")

    # Seeds first (user priority), then mined concepts, then LLM queries;
    # dedup keeps the earliest occurrence of each phrase.
    merged = _dedup(list(seed_keywords) + concepts + queries)
    return merged, len(concepts), [e for e in (err1, err2) if e]


def _expand(
    direction: str,
    seed_keywords: list[str],
    quality_criteria: str,
    liked: list[str] | None,
    disliked: list[str] | None,
    force: bool,
) -> tuple[list[str], str | None]:
    """Shared implementation. Returns (queries, error).

    On success writes the cache. On failure returns seeds and the error
    message WITHOUT caching, so the next call retries the LLM.
    """
    cache_key = _cache_key(direction, seed_keywords, liked, disliked)

    if not force:
        cached = _load_cache()
        if (
            cached
            and cached.get("key") == cache_key
            and cached.get("version") == _CACHE_VERSION
        ):
            logger.info(f"使用缓存的扩展关键词（{len(cached['queries'])} 条查询）")
            return cached["queries"], None

    try:
        merged, n_concepts, errors = _run_pipeline(
            direction, seed_keywords, quality_criteria, liked, disliked
        )
    except Exception as e:  # chain construction etc.
        merged, n_concepts, errors = [], 0, [e]

    n_seed_unique = len(_dedup(list(seed_keywords)))
    expanded_ok = n_concepts > 0 or len(merged) > n_seed_unique

    if not expanded_ok:
        err_msg = "; ".join(str(e) for e in errors) or "LLM 未返回结果"
        logger.warning(
            f"关键词扩展失败: {err_msg}（本次使用 {n_seed_unique} 个种子关键词，不缓存，下次自动重试）"
        )
        return list(seed_keywords), f"关键词提取失败: {err_msg}"

    logger.info(
        f"关键词扩展: {len(seed_keywords)} 种子 + {n_concepts} 概念 → {len(merged)} 条查询"
    )
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(
        json.dumps(
            {"version": _CACHE_VERSION, "key": cache_key, "queries": merged},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    return merged, None


def expand_keywords(
    direction: str,
    seed_keywords: list[str],
    quality_criteria: str = "",
    liked: list[str] | None = None,
    disliked: list[str] | None = None,
    force: bool = False,
) -> list[str]:
    """Expand seed keywords via two-stage LLM pipeline (lenient).

    Used by the crawl scheduler: on LLM failure falls back to seed keywords
    so crawling still runs. Failures are never cached.
    """
    if not seed_keywords and not direction:
        return []
    return _expand(direction, seed_keywords, quality_criteria, liked, disliked, force)[0]


def extract_keywords_strict(
    direction: str,
    seed_keywords: list[str],
    quality_criteria: str = "",
    liked: list[str] | None = None,
    disliked: list[str] | None = None,
) -> list[str]:
    """Two-stage extraction for interactive use (raises on LLM failure).

    Used by the /api/extract-keywords endpoint so the UI surfaces the real
    error (e.g. insufficient balance) instead of silently returning seeds.
    """
    if not direction and not seed_keywords:
        raise RuntimeError("研究方向和种子关键词均为空")
    queries, err = _expand(direction, seed_keywords, quality_criteria, liked, disliked, force=False)
    if err:
        raise RuntimeError(err)
    return queries


def _cache_key(direction: str, keywords: list[str], liked: list[str] | None = None, disliked: list[str] | None = None) -> str:
    """Simple hash of inputs to detect when cache is stale."""
    import hashlib
    liked_str = "|".join(sorted(liked or []))
    disliked_str = "|".join(sorted(disliked or []))
    blob = f"{direction}|{'|'.join(sorted(keywords))}|{liked_str}|{disliked_str}"
    return hashlib.md5(blob.encode()).hexdigest()[:12]


def _load_cache() -> dict | None:
    if not _CACHE_PATH.exists():
        return None
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
