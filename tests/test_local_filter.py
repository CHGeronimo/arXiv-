#!/usr/bin/env python3
"""P1-5: local zero-cost pre-filter."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paper_store  # noqa: E402

# 词表构建：profile 关键词 + 扩展缓存 → len>=4 token
with patch.object(paper_store, "load_research_profile",
                  return_value={"keywords": ["multi-agent reinforcement learning", "POMDP"]}), \
     patch("pathlib.Path.read_text",
           return_value='{"version":2,"key":"k","queries":["collusion-resistant mechanism design"]}'):
    paper_store._local_terms = None
    terms = paper_store.get_local_terms()
assert {"multi", "agent", "reinforcement", "learning", "collusion", "resistant", "mechanism", "design"} <= terms
assert "pomdp" in terms  # 5 字母 token，len>=4 应入选

# 0 命中 → 拒；1 命中 → 放行（保守）——用词表内 token 构造正例
assert paper_store.local_reject({"title": "NeRF for novel view synthesis",
                                 "summary": "3D gaussian splatting rendering"}, terms) is True
assert paper_store.local_reject({"title": "Agricultural disease classification",
                                 "summary": "crop image classification"}, terms) is True
assert paper_store.local_reject({"title": "Reinforcement learning for MARL",
                                 "summary": "anything"}, terms) is False
assert paper_store.local_reject({"title": "x", "summary": "mechanism design approach"}, terms) is False

# append_paper 集成：0 命中 → filter_reject + local_filter_reject
from crawler.models import Paper
calls = []
p = Paper(id="test.lf.1", source="arxiv", title="Thermal-NeRF from infrared camera", summary="radiance field")
with patch.object(paper_store, "_paper_exists", return_value=False), \
     patch.object(paper_store, "is_ignored", return_value=False), \
     patch.object(paper_store, "_ai_exists", return_value=False), \
     patch.object(paper_store, "ignore_paper", side_effect=lambda pid, r="": calls.append((pid, r))), \
     patch.object(paper_store, "get_local_terms", return_value=terms):
    r = paper_store.append_paper(p, enhance=True)
assert r == "filter_reject" and calls == [("test.lf.1", "local_filter_reject")], (r, calls)

print("本地预筛测试通过 ✅")
