#!/usr/bin/env python3
"""正文分析预算放开 + 降级诚实标注。"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ai.fulltext_analyzer as fa  # noqa: E402
from ai.structure import FulltextAnalysis  # noqa: E402

captured = {}
class _FakeChain:
    def invoke(self, inputs):
        captured.update(inputs)
        return FulltextAnalysis(
            method_implementation="方法实现内容",
            experimental_design="实验设计",
            key_results_detail="关键结果",
            limitations="局限",
            reproducibility="可复现",
            relevance_to_profile="相关性",
        )

PAPER = {"id": "2609.00001", "source": "arxiv", "title": "T", "summary": "S"}

# [1] 预算放开：5万字符正文 → prompt 收到 30000（旧上限 8000）
big_sections = {"introduction": "i" * 10000, "method": "m" * 20000, "experiments": "e" * 20000}
with patch.object(fa, "fetch_and_extract", return_value=big_sections), \
     patch.object(fa, "_get_chain", return_value=_FakeChain()):
    r = fa.analyze_fulltext(PAPER, profile={})
assert len(captured["sections_text"]) == 30000, len(captured["sections_text"])
assert not r["method_implementation"].startswith("⚠️"), "完整正文不应降级标注"
print("[1] 总预算 30000（4倍于旧8000），完整正文无标注 ✓")

# [2] 降级标注：只抓到 introduction 且过短
with patch.object(fa, "fetch_and_extract", return_value={"introduction": "only abstract-ish text"}), \
     patch.object(fa, "_get_chain", return_value=_FakeChain()):
    r2 = fa.analyze_fulltext(PAPER, profile={})
assert r2["method_implementation"].startswith("⚠️ 正文获取不完整"), r2["method_implementation"][:40]
print("[2] 正文过短/缺方法实验节 → ⚠️ 降级标注 ✓")

# [3] 章节足够但无 experiments（如纯理论文有 method）→ 不标注
with patch.object(fa, "fetch_and_extract", return_value={"introduction": "i" * 3000, "method": "m" * 5000}), \
     patch.object(fa, "_get_chain", return_value=_FakeChain()):
    r3 = fa.analyze_fulltext(PAPER, profile={})
assert not r3["method_implementation"].startswith("⚠️")
print("[3] method 节充足 → 不误标 ✓")

# [4] fetcher 每节上限 8000（旧 4000）
from ai.fulltext_fetcher import extract_sections  # noqa: E402
long_p = "<p>" + "word " * 4000 + "</p>"  # ~20000 chars
html = f"<html><body><h2>3 Method</h2>{long_p}<h2>4 Experiments</h2><p>short</p></body></html>"
secs = extract_sections(html)
assert len(secs.get("method", "")) == 8000, len(secs.get("method", ""))
print("[4] fetcher 每节上限 4000→8000 ✓")

# [5] 非 arXiv 论文不分析（既有行为不回归）
assert fa.analyze_fulltext({"id": "10.x/y", "source": "crossref", "title": "t", "summary": "s"}, profile={}) is None
print("[5] 非 arXiv 返回 None ✓")

print("\n正文分析预算/标注测试通过 ✅")
