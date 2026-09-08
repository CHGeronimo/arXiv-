#!/usr/bin/env python3
"""QuickFilter 解析容错：普通/信封/异常三种形态。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.quick_filter import quick_filter_paper  # noqa: E402

PROFILE = {"direction": "MARL", "keywords": [], "liked_topics": [], "disliked_topics": []}
PAPER = {"id": "x", "title": "t", "summary": "s"}

class _Chain:
    def __init__(self, content): self.content = content
    def invoke(self, inputs): return type("R", (), {"content": self.content})()

# [1] 普通 JSON
r = quick_filter_paper(PAPER, _Chain('{"is_relevant": false, "relevance_reason": "unrelated topic"}'), PROFILE)
assert r == (False, "unrelated topic"), r
# [2] GLM 信封：{"answer": "{...}"} —— 昨夜日志实锤形态
envelope = '{"answer": "{\\"is_relevant\\": false, \\"relevance_reason\\": \\"sociolinguistics, unrelated\\"}"}'
r2 = quick_filter_paper(PAPER, _Chain(envelope), PROFILE)
assert r2 == (False, "sociolinguistics, unrelated"), r2
# [3] markdown 围栏
r3 = quick_filter_paper(PAPER, _Chain('```json\n{"is_relevant": true, "relevance_reason": "MARL paper"}\n```'), PROFILE)
assert r3 == (True, "MARL paper"), r3
# [4] 缺字段 → 默认保留
r4 = quick_filter_paper(PAPER, _Chain('{"something": 1}'), PROFILE)
assert r4[0] is True
# [5] 完全异常 → 默认保留
r5 = quick_filter_paper(PAPER, _Chain('not json at all'), PROFILE)
assert r5 == (True, "")
# [6] reason 缺失 → 空串
r6 = quick_filter_paper(PAPER, _Chain('{"is_relevant": true}'), PROFILE)
assert r6 == (True, "")
print("✓ QuickFilter 解析容错（普通/信封/围栏/缺字段/异常）全部通过")
