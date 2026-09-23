"""AI enhancement for arxiv papers — unified entry point for daemon and CLI."""

import os
import json
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

import dotenv

import langchain_core.exceptions
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from .llm import build_chat, task_model
from .structure import Structure

logger = logging.getLogger(__name__)

# ── 分层流程版本戳（YYYY-MM-DD[.n]）──
# 各组件独立递增：改哪层只重跑哪层，不再全链重跑。
# 旧结果通过 ♻️「重跑旧流程」按对应层版本识别；中断续跑天然支持。
# ENHANCE_VER：影响 tldr/评分/推荐等级的提示词或解析变更
# CARD_VER：仅影响知识卡片提取的提示词/解析变更
# CLUSTER_VER：聚类算法/提示词变更（只重聚类，不动底层卡片）
ENHANCE_VER = "2026-09-19"   # 当前与旧全局戳同值（首次分层不触发重跑）
CARD_VER = "2026-09-19"
CLUSTER_VER = "2026-09-19"

# 兼容别名：增强打戳与重跑选择器用
PIPELINE_VERSION = ENHANCE_VER

_AI_DIR = os.path.dirname(os.path.abspath(__file__))

_env_path = os.path.join(_AI_DIR, '.env')
if os.path.exists(_env_path):
    dotenv.load_dotenv(_env_path)

template = open(os.path.join(_AI_DIR, "template.txt"), "r").read()
system = open(os.path.join(_AI_DIR, "system.txt"), "r").read()

DEFAULT_AI = {
    "tldr": "", "motivation": "", "method": "", "result": "", "conclusion": "",
    "title_zh": "", "summary_zh": "",
    "quality_score": 0, "relevance_score": 0, "recommendation": "ignore",
    "skip_reason": "",
}


def load_research_profile() -> dict:
    profile_path = os.path.join(os.path.dirname(__file__), '..', 'research_profile.json')
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            return json.load(f)
    return {"direction": "", "keywords": [], "quality_criteria": ""}


def build_chain(model_name: str):
    """Build the AI enhancement pipeline (raw LLM + tolerant parse).

    不用 with_structured_output：GLM 思考模式偶发返回 {"answer": "..."} 信封
    或对话式文本而非结构化 JSON——pydantic 严格校验直接丢整篇高质量分析。
    改为裸链 + _parse_structure 容错解析（与 quick_filter/idea_checker 同款）。
    """
    llm = build_chat(model_name, thinking=True)
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])
    return prompt_template | llm


def _parse_structure(content) -> Structure | None:
    """容错解析：正则取 JSON + answer 信封解包 + 部分字段缺省填充。"""
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
    # answer 信封解包
    if isinstance(data, dict) and isinstance(data.get("answer"), dict):
        data = data["answer"]
    if not isinstance(data, dict):
        return None

    # 字段别名与缺省
    aliases = {
        "tldr": ["tldr", "TLDR", "tl_dr"],
        "title_zh": ["title_zh", "titleZh", "title_chinese"],
        "summary_zh": ["summary_zh", "summaryZh", "abstract_zh"],
    }
    for canon, alts in aliases.items():
        if canon not in data:
            for alt in alts:
                if alt in data:
                    data[canon] = data.pop(alt)
                    break

    # 评分和推荐给安全默认值（防止 LLM 忘了填）
    try:
        data.setdefault("quality_score", max(1, min(10, int(data.get("quality_score", 3)))))
        data.setdefault("relevance_score", max(1, min(10, int(data.get("relevance_score", 3)))))
    except (ValueError, TypeError):
        data["quality_score"] = 3
        data["relevance_score"] = 3
    rec = str(data.get("recommendation", "reference")).lower().strip()
    if rec not in ("must-read", "recommended", "reference", "ignore"):
        data["recommendation"] = "reference"
    data.setdefault("skip_reason", "")

    # 必填字符串字段给空串默认
    for f in ("tldr", "motivation", "method", "result", "conclusion",
              "title_zh", "summary_zh"):
        data.setdefault(f, "")

    try:
        return Structure(**data)
    except Exception:
        return None


def _extract_partial(error_msg: str) -> dict:
    """Try to extract partial JSON from an OutputParserException message."""
    try:
        if "Function Structure arguments:" in error_msg:
            json_str = error_msg.split("Function Structure arguments:", 1)[1] \
                .strip().split("are not valid JSON")[0].strip()
        else:
            start = error_msg.find('{')
            end = error_msg.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = error_msg[start:end + 1]
            else:
                json_str = ""
        if json_str:
            return json.loads(json_str)
    except Exception:
        pass
    return {}


def enhance_single(paper: dict, chain, profile: dict, language: str) -> dict:
    """Enhance a single paper with AI analysis.

    Always returns the paper dict with an 'AI' key populated.
    On partial parse failure, fills missing fields from DEFAULT_AI.
    On full failure, sets paper['AI'] to DEFAULT_AI plus '_llm_failed': True
    so callers can distinguish "LLM said ignore" from "LLM was unreachable"
    and avoid permanently blacklisting the paper.
    """
    try:
        resp = chain.invoke({
            "language": language,
            "content": paper.get("summary", ""),
            "title": paper.get("title", ""),
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
            "quality_criteria": profile.get("quality_criteria", ""),
            "liked_topics": "\n".join(profile.get("liked_topics", [])[-100:]),
            "disliked_topics": "\n".join(profile.get("disliked_topics", [])[-100:]),
            "recent_notes": "\n".join(profile.get("feedback_notes", [])[-20:]) or "(none)",
        })
        parsed = _parse_structure(resp)
        if parsed is None:
            paper["AI"] = {**DEFAULT_AI, "_llm_failed": True}
            return paper
        paper["AI"] = parsed.model_dump()
    except langchain_core.exceptions.OutputParserException as e:
        partial = _extract_partial(str(e))
        if partial:
            paper["AI"] = {**DEFAULT_AI, **partial}
            logger.warning(f"论文 {paper.get('id', '?')} AI 数据不完整: {list(partial.keys())}")
        else:
            paper["AI"] = {**DEFAULT_AI, "_llm_failed": True}
            logger.error(f"论文 {paper.get('id', '?')} 增强失败: {e}")
    except Exception as e:
        paper["AI"] = {**DEFAULT_AI, "_llm_failed": True}
        logger.error(f"论文 {paper.get('id', '?')} 增强失败: {e}")

    # Sanitize recommendation to exact allowed values
    rec = paper["AI"].get("recommendation", "ignore")
    if rec not in ("must-read", "recommended", "reference", "ignore"):
        logger.warning(f"非标准推荐 '{rec}' 论文 {paper.get('id', '?')}，映射为 'reference'")
        paper["AI"]["recommendation"] = "reference"
        rec = "reference"

    # Auto-downgrade low-relevance reference to ignore
    if rec == "reference":
        rel = paper["AI"].get("relevance_score", 0) or 0
        if rel <= 5:
            logger.info(f"低相关性 reference 降级 (rel={rel}) 论文 {paper.get('id', '?')}")
            paper["AI"]["recommendation"] = "ignore"
            paper["AI"]["skip_reason"] = "low_relevance"

    # Ensure every key from DEFAULT_AI exists
    for k, v in DEFAULT_AI.items():
        paper["AI"].setdefault(k, v)

    return paper


def main():
    """CLI entry point for batch AI enhancement."""
    parser = argparse.ArgumentParser(description="AI-enhance arxiv papers")
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    parser.add_argument("--max_workers", type=int, default=1, help="parallel workers")
    args = parser.parse_args()

    model_name = task_model("enhance")
    language = os.environ.get("LANGUAGE", 'Chinese')
    target_file = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')

    # Load and deduplicate input data
    data: List[Dict] = []
    with open(args.data, "r") as f:
        for line in f:
            data.append(json.loads(line))

    seen_ids = set()
    unique_data = []
    for item in data:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)

    # Incremental mode: skip already-processed IDs
    existing_data = []
    existing_ids = set()
    if os.path.exists(target_file):
        with open(target_file, "r") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    existing_data.append(item)
                    existing_ids.add(item['id'])
        logger.info(f"增量处理: 已有 {len(existing_ids)} 篇论文")

    new_data = [item for item in unique_data if item['id'] not in existing_ids]
    logger.info(f"待处理: {len(new_data)} 篇（跳过 {len(unique_data) - len(new_data)} 篇已有）")

    if not new_data:
        logger.info("没有新论文需要处理")
        return

    # Write existing data back (overwrite file)
    with open(target_file, "w") as f:
        for item in existing_data:
            f.write(json.dumps(item) + "\n")

    # Build chain and process
    chain = build_chain(model_name)
    logger.info(f"模型: {model_name}")

    def _process(paper: dict) -> dict:
        profile = load_research_profile()
        return enhance_single(paper, chain, profile, language)

    with open(target_file, "a") as f:
        if args.max_workers <= 1:
            for item in new_data:
                result = _process(item)
                f.write(json.dumps(result) + "\n")
                f.flush()
        else:
            with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
                futures = {executor.submit(_process, item): item for item in new_data}
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        logger.error(f"论文 {item.get('id', '?')} 异常: {e}")
                        item["AI"] = dict(DEFAULT_AI)
                        result = item
                    f.write(json.dumps(result) + "\n")
                    f.flush()

    logger.info(f"完成: {target_file}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
