#!/usr/bin/env python3
"""评分归因主题匹配 + 图谱聚类下钻端点。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from backend.db import init_db  # noqa: E402
init_db()

import backend.api as api  # noqa: E402

# [1] 主题匹配：整串子串 / 词项几乎全中 / 不中
f = api._match_preference_topics
text = "Multi-Agent Credit Assignment via Opponent Modeling in POMDPs"
assert f(["opponent modeling"], text) == ["opponent modeling"]          # 整串子串
assert f(["credit assignment"], text) == ["credit assignment"]
assert f(["multi-agent reinforcement learning"], "Multi-Agent Learning Coordination") == ["multi-agent reinforcement learning"]  # 词项 3/4 ≥ max(1,3)
assert f(["multi-agent reinforcement learning"], text) == []  # 词项 2/4，不足
assert f(["quantum chemistry"], text) == []                             # 词项 0/2
assert f(["opponent modeling theory"], text) == ["opponent modeling theory"]  # 2/3 词项（≥max(1,2)）
assert f([], text) == [] and f(["x"], "") == []
print("[1] 偏好主题匹配规则 ✓")

# [2] GET /api/paper/<id> 带 preference 字段（真实库任取一篇）
c = api.app.test_client()
row = api.get_conn().execute("SELECT id FROM papers LIMIT 1").fetchone()
if row:
    r = c.get(f"/api/paper/{row[0]}")
    assert r.status_code == 200
    data = r.get_json()
    assert "preference" in data and set(data["preference"]) == {"liked", "disliked"}
    print(f"[2] 论文详情含 preference ✓（{row[0][:24]}…）")
else:
    print("[2] 跳过（空库）")

# [3] 聚类下钻端点：真实聚类 → 论文列表
crow = api.get_conn().execute(
    "SELECT cluster_name FROM knowledge_clusters ORDER BY LENGTH(paper_ids) DESC LIMIT 1").fetchone()
if crow:
    name = crow[0]
    r = c.get(f"/api/cluster/{name}/papers")
    assert r.status_code == 200
    data = r.get_json()
    assert data["cluster"] == name and data["count"] == len(data["papers"])
    assert all(p.get("id") for p in data["papers"])
    assert c.get("/api/cluster/不存在的聚类/papers").status_code == 404
    print(f"[3] 聚类下钻 ✓（{name[:20]}… {data['count']} 篇）")
else:
    print("[3] 跳过（无聚类）")

print("\n归因+下钻测试通过 ✅")
