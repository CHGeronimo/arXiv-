#!/usr/bin/env python3
"""Generate a daily Markdown research digest from AI-enhanced papers."""

import json
import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

if os.path.exists(os.path.join(os.path.dirname(__file__), '.env')):
    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DIGEST_PROMPT = """You are a research assistant. Based on the following AI-analyzed papers from today, write a concise research digest in Markdown.

Group papers by topic/theme. For each group:
1. Summarize the key trend or insight (2-3 sentences)
2. List the most important papers with title + one-line note

At the end, highlight:
- Top 3 must-read papers (highest quality AND relevance)
- Any notable breakthroughs or surprising results

Write in {language}.

Papers data:
{papers_json}
"""


def generate_digest(date_str: str | None = None, language: str = "Chinese") -> str:
    date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data_dir = Path(__file__).parent.parent / "data"

    papers = []
    ai_file = data_dir / f"{date_str}_AI_enhanced_{language}.jsonl"
    if not ai_file.exists():
        logger.warning(f"No AI-enhanced file for {date_str}")
        return ""

    with open(ai_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                papers.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not papers:
        return ""

    papers.sort(
        key=lambda p: (
            (p.get("AI", {}).get("relevance_score", 0)),
            (p.get("AI", {}).get("quality_score", 0)),
        ),
        reverse=True,
    )

    summaries = []
    for p in papers[:80]:
        ai = p.get("AI", {})
        summaries.append({
            "title": p.get("title", ""),
            "source": p.get("source", ""),
            "journal": p.get("journal_title", ""),
            "categories": p.get("categories", []),
            "tldr": ai.get("tldr", ""),
            "recommendation": ai.get("recommendation", "skip"),
            "quality_score": ai.get("quality_score", 0),
            "relevance_score": ai.get("relevance_score", 0),
        })

    model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
    llm = ChatOpenAI(model=model_name, temperature=0.3)
    prompt = ChatPromptTemplate.from_template(DIGEST_PROMPT)
    chain = prompt | llm

    result = chain.invoke({
        "language": language,
        "papers_json": json.dumps(summaries, ensure_ascii=False, indent=2),
    })

    digest_dir = data_dir.parent / "digests"
    digest_dir.mkdir(exist_ok=True)
    digest_path = digest_dir / f"{date_str}.md"

    content = f"# Research Digest — {date_str}\n\n{result.content}\n"
    digest_path.write_text(content, encoding="utf-8")
    logger.info(f"Digest saved to {digest_path}")
    return str(digest_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    date = sys.argv[1] if len(sys.argv) > 1 else None
    path = generate_digest(date)
    if path:
        print(f"Digest: {path}")
    else:
        print("No papers to digest")
        sys.exit(1)
