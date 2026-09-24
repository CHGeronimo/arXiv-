#!/usr/bin/env python3
"""Generate a daily Markdown research digest from AI-enhanced papers."""

import json
import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

import dotenv
from langchain_core.prompts import ChatPromptTemplate

from .llm import build_chat, task_model

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
    from backend.db import get_conn, queue_write

    conn = get_conn()
    # 按入库时间取论文：published_date 是投稿日（arXiv 早 1-2 天、会议论文是年初），
    # 按 published_date=今天 查永远查空；凌晨跑批时用当天 created_at 才能覆盖本轮新论文
    rows = conn.execute(
        """SELECT p.title, p.source, p.journal_title, p.categories,
                  ai.tldr, ai.recommendation, ai.quality_score, ai.relevance_score
           FROM papers p JOIN ai_results ai ON p.id = ai.paper_id
           WHERE p.created_at >= ? AND ai.recommendation != 'ignore'
           ORDER BY ai.relevance_score DESC, ai.quality_score DESC
           LIMIT 80""",
        (f"{date_str} 00:00:00",),
    ).fetchall()

    if not rows:
        logger.warning(f"{date_str} 无 AI 增强论文")
        return ""

    summaries = []
    for row in rows:
        summaries.append({
            "title": row[0],
            "source": row[1],
            "journal": row[2],
            "categories": json.loads(row[3]) if row[3] else [],
            "tldr": row[4],
            "recommendation": row[5],
            "quality_score": row[6],
            "relevance_score": row[7],
        })

    model_name = task_model("digest")
    llm = build_chat(model_name, thinking=True, temperature=0.3, timeout=300, priority=True)
    prompt = ChatPromptTemplate.from_template(DIGEST_PROMPT)
    chain = prompt | llm

    result = chain.invoke({
        "language": language,
        "papers_json": json.dumps(summaries, ensure_ascii=False, indent=2),
    })

    digest_dir = Path(__file__).parent.parent / "digests"
    digest_dir.mkdir(exist_ok=True)
    digest_path = digest_dir / f"{date_str}.md"
    content = f"# Research Digest — {date_str}\n\n{result.content}\n"
    digest_path.write_text(content, encoding="utf-8")

    queue_write(
        "INSERT OR REPLACE INTO digests (date, content) VALUES (?, ?)",
        (date_str, content),
    )

    logger.info(f"摘要已保存到 {digest_path}")
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
