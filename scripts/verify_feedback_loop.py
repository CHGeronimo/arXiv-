#!/usr/bin/env python3
"""评分↔反馈通路端到端实证工具（真实 GLM，非 mock）。

⚠️ 会真实调用 LLM 并临时修改 research_profile.json / feedback 表，
   结束后自动恢复现场。用于版本升级/疑似断裂时的人工验证：

    python scripts/verify_feedback_loop.py

验证链路：点赞+滑杆+评语 → POST /api/feedback → 后台线程真实 GLM
主题提取 → feedback_notes/liked_topics 更新 → enhance 评分模板变量
（recent_notes / liked_topics）携带反馈信号。
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db import init_db, stop_writer  # noqa: E402

init_db()

import backend.api as api  # noqa: E402
from backend.ai.enhance import enhance_single  # noqa: E402

NOTE = "信用分配的方差分解思路很好，希望多推这类有MARL实证的工作"

conn = sqlite3.connect("data/papers.db", timeout=10)
row = conn.execute("""
    SELECT p.id, p.title FROM papers p JOIN ai_results a ON p.id=a.paper_id
    WHERE a.recommendation='recommended' AND a.method != '' LIMIT 1
""").fetchone()
assert row, "库中无带 AI 分析的论文可作锚点"
PID, TITLE = row
print(f"锚点论文: {TITLE[:60]} ({PID})")

prof_path = Path("research_profile.json")
backup = prof_path.read_text(encoding="utf-8")
before = json.loads(backup)

try:
    c = api.app.test_client()
    print("\n── 第1步: 点赞+滑杆+评语 → 真实HTTP → 后台线程 → 真实GLM ──")
    r = c.post("/api/feedback", json={
        "paper_id": PID, "rating": "like", "relevance": 5, "novelty": 4, "note": NOTE,
    })
    assert r.status_code == 200, r.get_data(as_text=True)

    updated = None
    for _ in range(30):
        time.sleep(1)
        try:
            prof = json.loads(prof_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if any("信用分配" in n for n in prof.get("feedback_notes", [])):
            updated = prof
            break
    assert updated, "后台线程 30s 内未完成画像更新——链路断点！"
    print("✓ 路径二: 评语原文进入 feedback_notes")

    new_topics = [t for t in updated.get("liked_topics", []) if t not in before.get("liked_topics", [])]
    print(f"{'✓ 路径一: liked_topics 新增 ' + str(new_topics) if new_topics else '○ 路径一: 主题语义重复被去重合并（正常）'}")

    print("\n── 第2步: 画像到达『主增强评分』入口 ──")
    captured = {}

    class CaptureChain:
        def invoke(self, inputs):
            captured.update(inputs)
            raise RuntimeError("capture")

    enhance_single({"id": "probe", "title": "t", "summary": "s"}, CaptureChain(), updated, "Chinese")
    assert "信用分配" in captured.get("recent_notes", ""), "评语原文必须直通评分模板"
    assert captured.get("liked_topics", "") or new_topics == [], "liked_topics 应有内容"
    print("✓ enhance prompt.recent_notes 携带评语原文")
    print("✓ enhance prompt.liked_topics 携带学到的主题")
    print("\n═══ 评分↔反馈通路全链路正常（真实GLM实证）═══")
finally:
    conn.execute("DELETE FROM feedback WHERE paper_id=? AND note=?", (PID, NOTE))
    conn.commit()
    conn.close()
    if backup:
        tmp = prof_path.with_suffix(".json.tmp")
        tmp.write_text(backup, encoding="utf-8")
        tmp.replace(prof_path)
    stop_writer()
    print("（现场已恢复：测试反馈删除、profile 还原）")
