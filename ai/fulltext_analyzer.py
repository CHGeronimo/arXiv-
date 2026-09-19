"""Deep full-text analysis for high-quality papers."""
from __future__ import annotations

import logging
import os
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate

from .llm import build_chat, task_model
from .structure import FulltextAnalysis
from .fulltext_fetcher import fetch_and_extract
from .enhance import load_research_profile

logger = logging.getLogger(__name__)

_FULLTEXT_PROMPT = """你是一位专业的学术论文分析助手，正在对论文全文进行深度分析。请用中文回答。

## 研究者画像
研究方向: {research_direction}
关键词: {keywords}

## 论文标题
{title}

## 摘要
{abstract}

## 正文章节
{sections_text}

请对这篇论文的全文进行深度分析，重点关注：
1. **方法实现**: 方法的具体工作原理，包括架构设计、核心算法、训练流程、关键设计选择
2. **实验设计**: 使用的数据集、基线方法、评价指标、消融实验、评估协议
3. **关键结果**: 具体的定量结果、与基线的对比、是否达到 SOTA
4. **局限性**: 论文声明或可推断的局限性、假设条件、可扩展性问题、负面结果
5. **可复现性**: 代码是否开源、超参数是否详尽、数据集是否可获取
6. **与研究方向的关系**: 哪些技术可以迁移到用户的研究中？填补了什么空白？

请用中文输出，使用以下 JSON 键名: "method_implementation", "experimental_design", "key_results_detail", "limitations", "reproducibility", "relevance_to_profile"。"""

_CHAIN = None

# 字段别名（LLM 偶尔用驼峰或简写键名）
_FIELD_ALIASES = {
    "method_implementation": ["method_implementation", "MethodImplementation", "method"],
    "experimental_design": ["experimental_design", "ExperimentalDesign", "experiments"],
    "key_results_detail": ["key_results_detail", "KeyResults", "key_results"],
    "limitations": ["limitations", "Limitations"],
    "reproducibility": ["reproducibility", "Reproducibility"],
    "relevance_to_profile": ["relevance_to_profile", "RelevanceToProfile", "relevance"],
}


def _flatten_value(v) -> str:
    """LLM 常返回嵌套 dict/list（实测内容质量很高但结构不符 schema）——
    递归拍平成 '键: 值' 行式文本而不是丢弃整个分析。"""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        parts = [_flatten_value(x) for x in v]
        return "\n".join(f"- {p}" for p in parts if p)
    if isinstance(v, dict):
        parts = [(k, _flatten_value(x)) for k, x in v.items()]
        return "\n".join(f"{k}: {val}" for k, val in parts if val)
    return str(v)


def _parse_analysis(raw_text: str) -> FulltextAnalysis:
    import json as _json
    import re as _re
    m = _re.search(r'\{.*\}', raw_text, _re.DOTALL)
    if m:
        raw_text = m.group()
    data = _json.loads(raw_text)
    # GLM 信封：{"analysis_note": "...", ...} 之外的包裹层不常见，但 answer 信封同款处理
    if isinstance(data.get("answer"), str):
        try:
            inner = _json.loads(data["answer"])
            if isinstance(inner, dict):
                data = inner
        except _json.JSONDecodeError:
            pass
    fields = {}
    for canon, aliases in _FIELD_ALIASES.items():
        val = next((data[a] for a in aliases if a in data), "")
        fields[canon] = _flatten_value(val)
    return FulltextAnalysis(**fields)


def _get_chain():
    global _CHAIN
    if _CHAIN is None:
        model_name = task_model("fulltext")
        # 不用 with_structured_output：GLM 思考模式常返回嵌套 dict 值
        # （实测六字段全是对象，pydantic 严格校验丢弃整个高质量分析）——自行解析拍平
        llm = build_chat(model_name, thinking=True)
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

    # 预算放开：正文覆盖 ~15% → 大部分正文（flash 上下文充裕，成本几乎无感）
    if len(sections_text) > 30000:
        sections_text = sections_text[:30000]

    # 诚实标注：抓取不完整（过短或缺方法/实验节）时明示降级，不冒充全文分析
    low_confidence = len(sections_text) < 2000 or not (
        "method" in sections or "experiments" in sections
    )
    if low_confidence:
        logger.warning(
            f"正文获取不完整（节={list(sections.keys())}, {len(sections_text)}字符），降级为摘要级分析: {arxiv_id}"
        )

    if profile is None:
        profile = load_research_profile()

    chain = _get_chain()

    try:
        resp = chain.invoke({
            "title": paper.get("title", ""),
            "abstract": paper.get("summary", ""),
            "sections_text": sections_text,
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
        })
        result = _parse_analysis(resp.content if hasattr(resp, "content") else str(resp))
    except Exception as e:
        logger.error(f"正文分析失败 {arxiv_id}: {e}")
        return None

    return {
        "paper_id": arxiv_id,
        # 降级时在首字段明示，避免摘要级分析冒充全文分析
        "method_implementation": (
            ("⚠️ 正文获取不完整，以下为基于摘要的降级分析\n\n" + result.method_implementation)
            if low_confidence else result.method_implementation
        ),
        "experimental_design": result.experimental_design,
        "key_results_detail": result.key_results_detail,
        "limitations": result.limitations,
        "reproducibility": result.reproducibility,
        "relevance_to_profile": result.relevance_to_profile,
    }
