#!/usr/bin/env python3
"""主题分配防"其他"堆积：归一化+模糊救回近似主题名 / 解析失败走关键词救援 / 其他比例受控。"""
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ai.knowledge_clustering import _assign_papers_to_themes_llm  # noqa: E402

THEMES = ["multi-agent reinforcement learning", "mechanism design", "vital sign monitoring"]

PAPER_KW = {
    "p_case": ["multi-agent reinforcement learning", "credit assignment"],
    "p_rescue": ["collusion resistance", "mechanism design", "incentive compatibility"],
    "p_other": ["totally unrelated topic"],
    "p_missing": ["vital sign monitoring", "remote photoplethysmography"],
}
KW_COUNTER = Counter(t for kws in PAPER_KW.values() for t in kws)


class _Resp:
    def __init__(self, content):
        self.content = content


def _llm_with(content):
    class FakeChat:
        def invoke(self, _prompt):
            return _Resp(content)
    return FakeChat()


# [1] 归一化救回：LLM 返回大小写变体 → 命中规范主题名，不掉"其他"
content = '{"p_case": ["Multi-Agent Reinforcement Learning"], "p_rescue": ["mechanism designzzz"], "p_other": ["其他"]}'
# p_rescue 的主题名故意拼错（模糊不中）→ 走关键词救援；p_missing 未返回 → 同样救援
with patch("backend.ai.llm.build_chat", return_value=_llm_with(content)):
    r1 = _assign_papers_to_themes_llm(PAPER_KW, THEMES, KW_COUNTER)
assert r1["p_case"] == ["multi-agent reinforcement learning"], r1["p_case"]
assert "mechanism design" in r1["p_rescue"], f"应被关键词救援: {r1['p_rescue']}"
assert "vital sign monitoring" in r1["p_missing"], f"应被关键词救援: {r1['p_missing']}"
assert r1["p_other"] == ["其他"]
print("[1] 归一化+模糊救回 / 关键词救援 ✓")

# [2] 整批 JSON 解析失败 → 全部转关键词救援（不再整批判"其他"）
with patch("backend.ai.llm.build_chat", return_value=_llm_with("垃圾输出，不是 JSON {")):
    r2 = _assign_papers_to_themes_llm(PAPER_KW, THEMES, KW_COUNTER)
assert r2["p_case"] and r2["p_case"][0] in THEMES
assert r2["p_missing"] and "vital sign monitoring" in r2["p_missing"]
assert r2["p_other"] == ["其他"], "真不相关的论文才留在其他"
print("[2] 解析失败→关键词救援（不再整批其他）✓")

# [3] LLM 全挂 → 全量关键词回退（既有行为保持）
with patch("backend.ai.llm.build_chat", side_effect=RuntimeError("LLM down")):
    r3 = _assign_papers_to_themes_llm(PAPER_KW, THEMES, KW_COUNTER)
assert set(r3) == set(PAPER_KW) and r3["p_other"] == ["其他"]
print("[3] LLM 全挂全量回退保持 ✓")

# [4] 主题名解析单元：归一化精确 / difflib 模糊 / 真不匹配
from backend.ai.knowledge_clustering import _resolve_theme, _norm_theme  # noqa: E402
norm_map = {_norm_theme(t): t for t in THEMES}
assert _resolve_theme("Multi-Agent Reinforcement Learning", THEMES, norm_map) == THEMES[0]
assert _resolve_theme("mechanism design,", THEMES, norm_map) == THEMES[1]
assert _resolve_theme("quantum chemistry simulation", THEMES, norm_map) is None
assert _resolve_theme("其他", THEMES, norm_map) == "其他"
print("[4] 主题名归一化/模糊解析 ✓")

print("\n聚类防堆积测试通过 ✅")
