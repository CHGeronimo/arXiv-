#!/usr/bin/env python3
"""P0-2: LLM failure must NOT permanently blacklist papers."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ai.enhance as enhance  # noqa: E402
import paper_store  # noqa: E402
from crawler.models import Paper  # noqa: E402

# 1) enhance_single 在 LLM 异常时打 _llm_failed 标记
paper = {"id": "test.1", "title": "t", "summary": "s"}
boom = type("BoomChain", (), {"invoke": lambda self, *a, **k: 1 / 0})()
result = enhance.enhance_single(paper, boom, {}, "Chinese")
assert result["AI"].get("_llm_failed") is True, "LLM 异常必须打失败标记"
assert result["AI"]["recommendation"] == "ignore", "默认值保持 ignore（但带标记）"

# 部分解析失败（有 partial）不打失败标记
import langchain_core.exceptions

class PartialBoom:
    def invoke(self, *a, **k):
        raise langchain_core.exceptions.OutputParserException(
            'Function Structure arguments: {"tldr": "x"} are not valid JSON'
        )
paper2 = {"id": "test.2", "title": "t", "summary": "s"}
result2 = enhance.enhance_single(paper2, PartialBoom(), {}, "Chinese")
assert "_llm_failed" not in result2["AI"] and result2["AI"]["tldr"] == "x"

# 2) append_paper：失败→"error"且不进 ignored；LLM判拒→照常 ignore
ignored_calls = []
p = Paper(id="test.local.1", source="arxiv", title="multi-agent reinforcement learning", summary="coordination")
with patch.object(paper_store, "_paper_exists", return_value=False), \
     patch.object(paper_store, "is_ignored", return_value=False), \
     patch.object(paper_store, "_ai_exists", return_value=False), \
     patch.object(paper_store, "ignore_paper", side_effect=lambda pid, r="": ignored_calls.append((pid, r))), \
     patch.object(paper_store, "get_quick_chain", return_value=None), \
     patch.object(paper_store, "get_ai_chain", return_value=(None, {})), \
     patch.object(paper_store, "quick_filter_paper", return_value=True), \
     patch.object(paper_store, "enhance_single", return_value={"AI": {**enhance.DEFAULT_AI, "_llm_failed": True}}), \
     patch.object(paper_store, "_local_filter_enabled", return_value=False):
    r = paper_store.append_paper(p, enhance=True)
assert r == "error", f"LLM 故障应返回 error, got {r}"
assert ignored_calls == [], f"故障时绝不能进 ignored: {ignored_calls}"

with patch.object(paper_store, "_paper_exists", return_value=False), \
     patch.object(paper_store, "is_ignored", return_value=False), \
     patch.object(paper_store, "_ai_exists", return_value=False), \
     patch.object(paper_store, "ignore_paper", side_effect=lambda pid, r="": ignored_calls.append((pid, r))), \
     patch.object(paper_store, "get_quick_chain", return_value=None), \
     patch.object(paper_store, "get_ai_chain", return_value=(None, {})), \
     patch.object(paper_store, "quick_filter_paper", return_value=True), \
     patch.object(paper_store, "enhance_single", return_value={"AI": {**enhance.DEFAULT_AI, "recommendation": "ignore", "skip_reason": "low_relevance"}}), \
     patch.object(paper_store, "_insert_paper_row"), \
     patch.object(paper_store, "_local_filter_enabled", return_value=False):
    r2 = paper_store.append_paper(p, enhance=True)
assert r2 == "ai_reject" and ignored_calls == [("test.local.1", "low_relevance")], (r2, ignored_calls)

print("LLM故障不误杀测试通过 ✅")
