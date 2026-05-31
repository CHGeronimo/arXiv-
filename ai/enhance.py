"""AI enhancement for arxiv papers — unified entry point for daemon and CLI."""

import os
import json
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

import dotenv

import langchain_core.exceptions
from langchain_openai import ChatOpenAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from .structure import Structure

logger = logging.getLogger(__name__)

_AI_DIR = os.path.dirname(os.path.abspath(__file__))

_env_path = os.path.join(_AI_DIR, '.env')
if os.path.exists(_env_path):
    dotenv.load_dotenv(_env_path)

template = open(os.path.join(_AI_DIR, "template.txt"), "r").read()
system = open(os.path.join(_AI_DIR, "system.txt"), "r").read()

DEFAULT_AI = {
    "tldr": "", "motivation": "", "method": "", "result": "", "conclusion": "",
    "title_zh": "", "summary_zh": "",
    "quality_score": 0, "relevance_score": 0, "recommendation": "skip",
    "skip_reason": "",
}


def load_research_profile() -> dict:
    profile_path = os.path.join(os.path.dirname(__file__), '..', 'research_profile.json')
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            return json.load(f)
    return {"direction": "", "keywords": [], "quality_criteria": ""}


def build_chain(model_name: str):
    llm = ChatOpenAI(model=model_name).with_structured_output(Structure, method="json_mode")
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])
    return prompt_template | llm


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
    On full failure, sets paper['AI'] to DEFAULT_AI.
    """
    try:
        response: Structure = chain.invoke({
            "language": language,
            "content": paper.get("summary", ""),
            "title": paper.get("title", ""),
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
            "quality_criteria": profile.get("quality_criteria", ""),
            "liked_topics": "\n".join(profile.get("liked_topics", [])[-5:]),
            "disliked_topics": "\n".join(profile.get("disliked_topics", [])[-5:]),
        })
        paper["AI"] = response.model_dump()
    except langchain_core.exceptions.OutputParserException as e:
        partial = _extract_partial(str(e))
        paper["AI"] = {**DEFAULT_AI, **partial}
        if partial:
            logger.warning(f"Partial AI data for {paper.get('id', '?')}: {list(partial.keys())}")
    except Exception as e:
        logger.error(f"Enhance error for {paper.get('id', '?')}: {e}")
        paper["AI"] = dict(DEFAULT_AI)

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

    model_name = os.environ.get("MODEL_NAME", 'deepseek-v4-flash')
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
        logger.info(f"Incremental: {len(existing_ids)} papers already processed")

    new_data = [item for item in unique_data if item['id'] not in existing_ids]
    logger.info(f"To process: {len(new_data)} (skipping {len(unique_data) - len(new_data)} existing)")

    if not new_data:
        logger.info("No new papers to process")
        return

    # Write existing data back (overwrite file)
    with open(target_file, "w") as f:
        for item in existing_data:
            f.write(json.dumps(item) + "\n")

    # Build chain and process
    chain = build_chain(model_name)
    logger.info(f"Model: {model_name}")

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
                        logger.error(f"Item {item.get('id', '?')} exception: {e}")
                        item["AI"] = dict(DEFAULT_AI)
                        result = item
                    f.write(json.dumps(result) + "\n")
                    f.flush()

    logger.info(f"Done: {target_file}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
