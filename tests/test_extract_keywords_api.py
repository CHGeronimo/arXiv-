#!/usr/bin/env python3
"""Test /api/extract-keywords endpoint with mocked LLM expansion."""
import sys
from pathlib import Path
import json
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api  # noqa: E402

FAKE_KWS = ["multi-agent reinforcement learning", "MARL", "collusion-resistant mechanism design",
            "belief updating", "learning dynamics in games", "vital sign sensing"] * 8  # 48 条

captured = {}

def fake_strict(direction, seed_keywords, quality_criteria="", liked=None, disliked=None):
    captured.update(direction=direction, seeds=seed_keywords, liked=liked, disliked=disliked)
    return FAKE_KWS

client = api.app.test_client()

# 1) 正常提取：direction 来自请求，liked/disliked 自动从 profile 磁盘文件读取
with patch("ai.keyword_expander.extract_keywords_strict", side_effect=fake_strict):
    r = client.post("/api/extract-keywords",
                    json={"direction": "动态不确定环境下的智能感知与协同决策", "seed_keywords": ["MARL"]})
assert r.status_code == 200, r.get_data(as_text=True)
data = r.get_json()
assert data["count"] == len(FAKE_KWS) == 48 and data["keywords"] == FAKE_KWS
assert captured["liked"] and captured["disliked"], "profile liked/disliked 必须传给扩展器"
assert captured["seeds"] == ["MARL"]
print(f"[1] 提取成功: {data['count']} 条, liked={len(captured['liked'])} disliked={len(captured['disliked'])} ✓")

# 2) 缺 direction → 400
r2 = client.post("/api/extract-keywords", json={"direction": "  "})
assert r2.status_code == 400
print("[2] 空 direction 返回 400 ✓")

# 3) 未传 seeds → 回退到 profile.keywords (14 个)
with patch("ai.keyword_expander.extract_keywords_strict", side_effect=fake_strict):
    r3 = client.post("/api/extract-keywords", json={"direction": "test direction"})
    assert r3.status_code == 200
assert len(captured["seeds"]) == 14, f"应回退到 profile 关键词, got {len(captured['seeds'])}"
print(f"[3] 无 seeds 时回退 profile.keywords ({len(captured['seeds'])} 个) ✓")

# 4) LLM 异常（如余额不足）→ 502 且 error 透传真实原因
with patch("ai.keyword_expander.extract_keywords_strict",
           side_effect=RuntimeError("关键词提取失败: Error code: 429 - {'code': '1113', 'message': '余额不足或无可用资源包'}")):
    r4 = client.post("/api/extract-keywords", json={"direction": "x"})
body4 = r4.get_json()
assert r4.status_code == 502 and "1113" in body4["error"], (r4.status_code, body4)
print("[4] LLM 异常返回 502，错误原因透传 ✓")

print("\n端点测试全部通过 ✅")
