#!/usr/bin/env python3
"""科研使用者功能回归：code_url 提取 / authorYear BibTeX 键 / light payload 扩展字段。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.paper_store import extract_code_url, load_all_papers  # noqa: E402
import backend.api as api  # noqa: E402

# 1) GitHub 链接提取（含归一化与边界）
assert extract_code_url({"summary": "code at https://github.com/foo/Bar.baz please", "comment": ""}) == "https://github.com/foo/Bar.baz"
assert extract_code_url({"summary": "no link", "comment": "see https://github.com/org/repo/tree/main"}) == "https://github.com/org/repo"  # 归一化到仓库根
assert extract_code_url({"summary": "visit https://www.github.com/a/b, ok", "comment": ""}) == "https://www.github.com/a/b"
assert extract_code_url({"summary": "", "comment": ""}) == ""
assert extract_code_url({"summary": "gitlab.com/x/y only", "comment": ""}) == ""  # 只认 GitHub
print("[1] GitHub 链接提取（归一化/边界）✓")

# 2) BibTeX authorYear 键（跳过冠词）
line1 = api._bibtex_for({"authors": ["Yann LeCun", "A B"], "title": "A Great Method",
                         "published_date": "2026-01-05", "doi": "10.x/y"}).split("\n")[0]
assert line1 == "@article{lecun2026great,", line1
assert " and ".join(["Yann LeCun", "A B"]) in api._bibtex_for({"authors": ["Yann LeCun", "A B"], "title": "T", "published_date": "2026"})
print(f"[2] BibTeX authorYear 键（{line1}）✓")

# 3) light payload 扩展字段：created_at（今日新到）/ relation（推荐理由）/ code_url
ps = load_all_papers(light=True)
assert all("created_at" in p and "relation" in p and "code_url" in p for p in ps[:50])
n_code = sum(1 for p in ps if p.get("code_url"))
n_rel = sum(1 for p in ps if p.get("relation"))
assert n_code > 100, f"回填后应有 200+ 篇带代码链接, got {n_code}"
print(f"[3] light payload: {len(ps)} 篇 · {n_code} 有代码 · {n_rel} 有推荐理由 ✓")

# 4) profile PUT merge 仍保留 liked/disliked（防止偏好可视化删除路径被回归）
import json  # noqa: E402
c = api.app.test_client()
before = json.loads(Path("research_profile.json").read_text(encoding="utf-8"))
try:
    r = c.put("/api/profile", json={"liked_topics": before["liked_topics"]})
    assert r.status_code == 200
    after = json.loads(Path("research_profile.json").read_text(encoding="utf-8"))
    assert after["disliked_topics"] == before["disliked_topics"] and "direction" in after
finally:
    Path("research_profile.json").write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
print("[4] 偏好字段 merge 保存不被覆盖 ✓")

print("\n科研功能回归通过 ✅")
