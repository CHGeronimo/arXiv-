#!/usr/bin/env python3
"""Smoke test for the two-stage keyword expander with mocked LLM calls."""
import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO)

import backend.ai.keyword_expander as ke

DIR = "动态不确定环境下的智能感知与协同决策：以深度学习、强化学习为基础，融合博弈论与多智能体建模，研究部分可观测条件下的策略演化、信用分配、防合谋机制、信念更新与分布式协同；面向体征感知、智能决策、网络安全落地。"
SEEDS = ["multi-agent reinforcement learning", "POMDP", "remote vital sign monitoring"]
LIKED = ["信用分配问题", "混合动机MARL基准"]
DISLIKED = ["two-player matrix games"]

FAKE_CONCEPTS = [
    "policy evolution under partial observability",
    "collusion-resistant mechanism design",
    "belief updating",
    "distributed coordination",
    "continual reinforcement learning",
    "generalization in reinforcement learning",
    "network security applications",
    "vital sign sensing",
]
FAKE_QUERIES = SEEDS + [
    "MARL", "Dec-POMDP", "anti-collusion mechanism design", "belief update",
    "learning dynamics in games", "LLM-based multi-agent coordination",
    "credit assignment", "Markov game", "multi-agent coordination",
]

def fake_llm_json(llm, system, template, inputs, list_field, retries=2):
    if list_field == "concepts":
        assert inputs["liked"] != "(none)", "liked topics must reach mining prompt"
        return FAKE_CONCEPTS, None
    assert inputs["keywords"].startswith("multi-agent"), "seeds must reach expand prompt"
    assert "collusion-resistant mechanism design" in inputs["concepts"], "concepts must reach expand prompt"
    assert isinstance(inputs["min_q"], int) and inputs["min_q"] >= 40, "query budget must scale up"
    return FAKE_QUERIES, None

if ke._CACHE_PATH.exists():
    os.remove(ke._CACHE_PATH)

with patch.object(ke, "_get_llm", return_value=object()), \
     patch.object(ke, "_llm_json", side_effect=fake_llm_json):
    out = ke.expand_keywords(direction=DIR, seed_keywords=SEEDS, liked=LIKED, disliked=DISLIKED, force=True)

print(f"\n[1] 扩展输出 {len(out)} 条")
assert out[:3] == SEEDS, "seeds must be kept and come first"
for c in FAKE_CONCEPTS:
    assert c in out, f"mined concept missing: {c}"
assert len(out) > len(SEEDS) * 2, "output must be substantially larger than seeds"

cached = json.loads(ke._CACHE_PATH.read_text(encoding="utf-8"))
assert cached["version"] == 2 and cached["queries"] == out
print("[2] 成功结果已缓存 (version=2) ✓")

# [3] LLM 全挂（先清缓存确保真调 LLM）：lenient 回种子、不写缓存、strict 抛真实错误
os.remove(ke._CACHE_PATH)
err = RuntimeError("Error code: 429 - {'error': {'code': '1113', 'message': '余额不足或无可用资源包'}}")
with patch.object(ke, "_get_llm", return_value=object()), \
     patch.object(ke, "_llm_json", return_value=([], err)):
    out3 = ke.expand_keywords(direction=DIR, seed_keywords=SEEDS, liked=LIKED, disliked=DISLIKED, force=True)
    try:
        ke.extract_keywords_strict(direction=DIR, seed_keywords=SEEDS, liked=LIKED, disliked=DISLIKED)
        raise AssertionError("strict must raise on failure")
    except RuntimeError as e:
        assert "1113" in str(e), f"error must carry underlying cause, got: {e}"
assert out3 == SEEDS, "lenient fallback must return seeds unchanged"
assert not ke._CACHE_PATH.exists(), "失败结果绝不能写缓存"
print("[3] 失败回退种子、不写缓存、strict 抛真实错误 ✓")

# [4] 失败不留缓存 → 下一次调用重新调 LLM
called = []
def counting_fake(llm, system, template, inputs, list_field, retries=2):
    called.append(list_field)
    return (FAKE_CONCEPTS if list_field == "concepts" else FAKE_QUERIES), None
with patch.object(ke, "_get_llm", return_value=object()), \
     patch.object(ke, "_llm_json", side_effect=counting_fake):
    out4 = ke.expand_keywords(direction=DIR, seed_keywords=SEEDS, liked=LIKED, disliked=DISLIKED)
assert called == ["concepts", "queries"], "无缓存时必须重新调 LLM"
assert out4 == out
print("[4] 失败不留缓存 → 下次自动重试 LLM ✓")

# [5] 缓存命中路径不调 LLM
with patch.object(ke, "_get_llm", side_effect=AssertionError("must not build LLM")), \
     patch.object(ke, "_llm_json", side_effect=AssertionError("must not call LLM")):
    out2 = ke.expand_keywords(direction=DIR, seed_keywords=SEEDS, liked=LIKED, disliked=DISLIKED)
    out5 = ke.extract_keywords_strict(direction=DIR, seed_keywords=SEEDS, liked=LIKED, disliked=DISLIKED)
assert out2 == out and out5 == out
os.remove(ke._CACHE_PATH)
print("[5] 缓存命中不调 LLM（strict 同样享受缓存）✓")

print("\n全部通过 ✅")
