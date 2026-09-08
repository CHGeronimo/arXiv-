#!/usr/bin/env python3
"""正文分析：预算/降级标注/嵌套解析拍平/占位页跳过。"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ai.fulltext_analyzer as fa  # noqa: E402

PAPER = {"id": "2609.00001", "source": "arxiv", "title": "T", "summary": "S"}

class _FakeChain:
    def __init__(self, payload):
        self.content = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    def invoke(self, inputs):
        captured.update(inputs)
        return type("R", (), {"content": self.content})()

captured = {}
GOOD = {
    "method_implementation": "方法实现", "experimental_design": "实验设计",
    "key_results_detail": "关键结果", "limitations": "局限",
    "reproducibility": "可复现", "relevance_to_profile": "相关性",
}

# [1] 预算放开：5万字符正文 → prompt 收到 30000
big_sections = {"introduction": "i" * 10000, "method": "m" * 20000, "experiments": "e" * 20000}
with patch.object(fa, "fetch_and_extract", return_value=big_sections), \
     patch.object(fa, "_get_chain", return_value=_FakeChain(GOOD)):
    r = fa.analyze_fulltext(PAPER, profile={})
assert len(captured["sections_text"]) == 30000
assert r["method_implementation"] == "方法实现"
print("[1] 总预算 30000 ✓")

# [2] 嵌套 dict 响应拍平（昨夜实锤形态：六字段全是对象，pydantic 全炸）
nested = {
    "analysis_note": "占位页说明，应被忽略",
    "method_implementation": {"core_problem": "评分机制漂移", "architecture_design": {"setup": "两阶段校准", "attack": "一致错误同伴"}},
    "experimental_design": {"datasets": "多项选择QA", "metrics": ["覆盖率", "子群体覆盖率"]},
    "key_results_detail": {"headline": "90%→74%", "subgroup": "87%→47%"},
    "limitations": ["仅多项选择QA", "仅开放权重模型"],
    "reproducibility": {"code": "未提及"},
    "relevance_to_profile": {"overall": "高度相关"},
}
with patch.object(fa, "fetch_and_extract", return_value=big_sections), \
     patch.object(fa, "_get_chain", return_value=_FakeChain(nested)):
    r2 = fa.analyze_fulltext(PAPER, profile={})
assert isinstance(r2["method_implementation"], str)
assert "评分机制漂移" in r2["method_implementation"] and "两阶段校准" in r2["method_implementation"]
assert "- 覆盖率" in r2["experimental_design"] and "多项选择QA" in r2["experimental_design"]
assert "90%→74%" in r2["key_results_detail"] and "87%→47%" in r2["key_results_detail"]
assert "仅多项选择QA" in r2["limitations"]
assert "占位页说明" not in json.dumps(r2, ensure_ascii=False), "analysis_note 等额外键不应混入"
print("[2] 嵌套对象/数组递归拍平为可读文本，额外键忽略 ✓")

# [3] markdown 围栏 + answer 信封
wrapped = '```json\n{"answer": ' + json.dumps(json.dumps(GOOD, ensure_ascii=False), ensure_ascii=False) + '}\n```'
with patch.object(fa, "fetch_and_extract", return_value=big_sections), \
     patch.object(fa, "_get_chain", return_value=_FakeChain(wrapped)):
    r3 = fa.analyze_fulltext(PAPER, profile={})
assert r3["method_implementation"] == "方法实现"
print("[3] 围栏+answer信封 解包 ✓")

# [4] 降级标注仍工作（正文过短但非占位页——直接给 analyze 短 sections）
with patch.object(fa, "fetch_and_extract", return_value={"introduction": "short only"}), \
     patch.object(fa, "_get_chain", return_value=_FakeChain(GOOD)):
    r4 = fa.analyze_fulltext(PAPER, profile={})
assert r4["method_implementation"].startswith("⚠️ 正文获取不完整")
print("[4] 降级诚实标注 ✓")

# [5] fetcher 占位页检测：总字数 <2000 → None（下轮重试而非垃圾分析）
from ai import fulltext_fetcher as ff  # noqa: E402
placeholder_html = "<html><body><h2>2 Experiments</h2><p>arXivLabs platform template text " + "x" * 300 + "</p></body></html>"
with patch.object(ff, "fetch_arxiv_html", return_value=placeholder_html):
    assert ff.fetch_and_extract("2609.04445") is None
real_html = "<html><body><h2>3 Method</h2><p>" + "real method content. " * 300 + "</p><h2>4 Experiments</h2><p>" + "results. " * 200 + "</p></body></html>"
with patch.object(ff, "fetch_arxiv_html", return_value=real_html):
    secs = ff.fetch_and_extract("2609.04445")
    assert secs and "method" in secs
print("[5] ar5iv 占位页(<2000字符)跳过，真实正文通过 ✓")

# [6] 非 arXiv 不分析
assert fa.analyze_fulltext({"id": "10.x/y", "source": "crossref", "title": "t", "summary": "s"}, profile={}) is None
print("[6] 非 arXiv 返回 None ✓")

print("\n正文分析解析/占位页测试通过 ✅")
