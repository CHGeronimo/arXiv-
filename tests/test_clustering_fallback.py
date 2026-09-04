#!/usr/bin/env python3
"""P0-3: clustering LLM failure must fall back to keyword matching, not crash."""
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.knowledge_clustering import _assign_papers_to_themes_llm  # noqa: E402

paper_kw = {
    "p1": ["multi-agent reinforcement learning", "credit assignment"],
    "p2": ["collusion resistance", "mechanism design"],
    "p3": ["totally unrelated topic"],
}
themes = ["multi-agent reinforcement learning", "mechanism design"]
kw_counter = Counter(t for kws in paper_kw.values() for t in kws)

# LLM 挂掉 → 回退关键词匹配（修复前此处 TypeError）
with patch("ai.llm.build_chat", side_effect=RuntimeError("LLM down")):
    result = _assign_papers_to_themes_llm(paper_kw, themes, kw_counter)
assert isinstance(result, dict) and set(result) == {"p1", "p2", "p3"}
assert "multi-agent reinforcement learning" in result["p1"] + result["p1"]
assert result["p2"] and result["p2"][0] in themes + ["其他"]
assert result["p3"] == ["其他"]

print("聚类回退测试通过 ✅")
