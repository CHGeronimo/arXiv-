from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from ai.enhance import enhance_single, build_chain, load_research_profile
from ai.quick_filter import build_quick_filter, quick_filter_paper
from crawler.models import Paper

logger = logging.getLogger("paper_store")

DATA_DIR = Path("data")
AI_LANGUAGE = "Chinese"

_written_ids: set[str] = set()
_enhanced_ids: set[str] = set()
_ids_lock = threading.Lock()

_ai_chain = None
_ai_profile = None
_quick_chain = None


def get_ai_chain():
    global _ai_chain, _ai_profile
    if _ai_chain is None:
        import os
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        _ai_chain = build_chain(model_name)
        _ai_profile = load_research_profile()
        logger.info(f"AI chain initialized: {model_name}")
    return _ai_chain, _ai_profile


def reset_ai_chain():
    global _ai_chain, _ai_profile
    _ai_chain = None
    _ai_profile = None


def get_quick_chain():
    global _quick_chain
    if _quick_chain is None:
        _quick_chain = build_quick_filter()
        logger.info("Quick filter chain initialized")
    return _quick_chain


def load_existing_ids() -> set[str]:
    existing: set[str] = set()
    if not DATA_DIR.exists():
        return existing
    for f in DATA_DIR.glob("*.jsonl"):
        if "_AI_" in f.name:
            continue
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    pid = data.get("id") or data.get("doi", "")
                    if pid:
                        existing.add(pid)
                except json.JSONDecodeError:
                    pass
    return existing


def load_enhanced_ids() -> set[str]:
    enhanced: set[str] = set()
    if not DATA_DIR.exists():
        return enhanced
    for f in DATA_DIR.glob("*_AI_enhanced_*.jsonl"):
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    data = json.loads(line.strip())
                    pid = data.get("id") or data.get("doi", "")
                    if pid:
                        enhanced.add(pid)
                except (json.JSONDecodeError, KeyError):
                    pass
    return enhanced


def init_ids():
    global _written_ids, _enhanced_ids
    _written_ids = load_existing_ids()
    _enhanced_ids = load_enhanced_ids()
    logger.info(f"Loaded {len(_written_ids)} existing, {len(_enhanced_ids)} enhanced")


def append_paper(paper: Paper, date_str: str | None = None, enhance: bool = False) -> bool:
    with _ids_lock:
        if paper.id in _written_ids:
            return False

    date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    DATA_DIR.mkdir(exist_ok=True)

    if enhance:
        if paper.id in _enhanced_ids:
            with _ids_lock:
                _written_ids.add(paper.id)
            return False

        paper_dict = json.loads(paper.to_jsonl())

        quick_chain = get_quick_chain()
        chain, profile = get_ai_chain()
        if not quick_filter_paper(paper_dict, quick_chain, profile):
            paper_dict["AI"] = {
                "tldr": "", "motivation": "", "method": "", "result": "", "conclusion": "",
                "title_zh": "", "summary_zh": "",
                "quality_score": 0, "relevance_score": 0, "recommendation": "skip",
                "skip_reason": "Filtered by quick relevance check",
            }
            ai_path = DATA_DIR / f"{date_str}_AI_enhanced_{AI_LANGUAGE}.jsonl"
            with open(ai_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(paper_dict, ensure_ascii=False) + "\n")
            with _ids_lock:
                _written_ids.add(paper.id)
            _enhanced_ids.add(paper.id)
            return True

        try:
            enhanced = enhance_single(paper_dict, chain, profile, AI_LANGUAGE)
            if enhanced:
                ai_path = DATA_DIR / f"{date_str}_AI_enhanced_{AI_LANGUAGE}.jsonl"
                with open(ai_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(enhanced, ensure_ascii=False) + "\n")
                with _ids_lock:
                    _written_ids.add(paper.id)
                _enhanced_ids.add(paper.id)
                return True
        except Exception as e:
            logger.warning(f"AI enhance failed for {paper.id}: {e}")

    filepath = DATA_DIR / f"{date_str}.jsonl"
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(paper.to_jsonl() + "\n")
    with _ids_lock:
        _written_ids.add(paper.id)
    return True


def find_paper_by_id(paper_id: str) -> dict | None:
    if not DATA_DIR.exists():
        return None
    for f in DATA_DIR.glob("*_AI_enhanced_*.jsonl"):
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    p = json.loads(line.strip())
                    if p.get("id") == paper_id:
                        return p
                except json.JSONDecodeError:
                    pass
    return None


def load_all_papers() -> list[dict]:
    papers = []
    if not DATA_DIR.exists():
        return papers
    seen_ids: set[str] = set()
    seen_dois: set[str] = set()
    for f in sorted(DATA_DIR.glob("*.jsonl"), reverse=True):
        if "_AI_" in f.name:
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        p = json.loads(line.strip())
                        pid = p.get("id", "")
                        doi = p.get("doi", "")
                        if pid in seen_ids:
                            continue
                        if doi and doi in seen_dois:
                            continue
                        seen_ids.add(pid)
                        if doi:
                            seen_dois.add(doi)
                        papers.append(p)
                    except json.JSONDecodeError:
                        pass
    for f in sorted(DATA_DIR.glob("*.jsonl"), reverse=True):
        if "_AI_" not in f.name:
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        p = json.loads(line.strip())
                        pid = p.get("id", "")
                        doi = p.get("doi", "")
                        if pid in seen_ids:
                            continue
                        if doi and doi in seen_dois:
                            continue
                        seen_ids.add(pid)
                        if doi:
                            seen_dois.add(doi)
                        papers.append(p)
                    except json.JSONDecodeError:
                        pass
    return papers
