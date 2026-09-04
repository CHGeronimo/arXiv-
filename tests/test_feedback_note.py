#!/usr/bin/env python3
"""评语闭环回归：note 存储 / COALESCE 保留 / 进提取prompt / feedback_notes 直通评分。"""
import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import init_db, stop_writer  # noqa: E402
init_db()

import api  # noqa: E402

DB = "data/papers.db"
TESTPID = "note-test-paper"
conn = sqlite3.connect(DB, timeout=10)
conn.execute("INSERT OR REPLACE INTO papers (id, source, title) VALUES (?,?,?)", (TESTPID, "arxiv", "Note Test"))
conn.execute("INSERT OR REPLACE INTO ai_results (paper_id, method, motivation, recommendation) VALUES (?,?,?,?)",
             (TESTPID, "multi-agent method", "coordination motivation", "recommended"))
conn.commit()

prof_path = Path("research_profile.json")
# 备份带校验：若 daemon 并发写导致瞬时读到空/坏文件，重试而非把坏内容当备份
profile_backup = None
for _ in range(5):
    try:
        profile_backup = prof_path.read_text(encoding="utf-8")
        json.loads(profile_backup)
        break
    except Exception:
        import time as _t
        _t.sleep(0.3)
assert profile_backup, "research_profile.json 不可读——请检查 daemon 状态"

c = api.app.test_client()
try:
    # [1] 评语入库（patch 掉后台画像线程，保持测试封闭——不真调 LLM、不写真 profile）
    with patch.object(api, "_update_profile_from_feedback", lambda *a: None):
        c.post("/api/feedback", json={"paper_id": TESTPID, "rating": "dislike", "note": "方法太老，没有MARL实证"})
        row = conn.execute("SELECT rating, note FROM feedback WHERE paper_id=?", (TESTPID,)).fetchone()
        assert row == ("dislike", "方法太老，没有MARL实证"), row

        # [2] 后续投票不带 note → 评语保留（COALESCE）；rating 正常更新
        c.post("/api/feedback", json={"paper_id": TESTPID, "rating": "like"})
        row = conn.execute("SELECT rating, note FROM feedback WHERE paper_id=?", (TESTPID,)).fetchone()
        assert row == ("like", "方法太老，没有MARL实证"), f"评语被抹: {row}"
    print("[1] 评语入库 + 投票不抹评语（COALESCE）✓")

    # [3] 评语进主题提取 prompt + 原文入 profile.feedback_notes
    class FakeResp:
        content = '["note topic A"]'
    class FakeLLM:
        def __init__(self, *a, **k): pass
        def invoke(self, prompt):
            captured.append(prompt)
            return FakeResp()
    captured = []
    with patch("ai.llm.build_chat", return_value=FakeLLM()), \
         patch.object(api, "reset_ai_chain"):
        api._update_profile_from_feedback(TESTPID, "like")
    assert any("方法太老" in p for p in captured), "评语必须进入提取 prompt"
    prof = json.loads(prof_path.read_text(encoding="utf-8"))
    assert any("方法太老" in n for n in prof.get("feedback_notes", [])), prof.get("feedback_notes")
    print("[2] 评语进提取 prompt + feedback_notes 持久化 ✓")

    # [4] feedback_notes 直通评分提示词（enhance_single 模板变量）
    from ai.enhance import enhance_single

    captured_inputs = {}
    class CaptureChain:
        def invoke(self, inputs):
            captured_inputs.update(inputs)
            raise RuntimeError("capture done")  # 会被 enhance_single 捕获，走 _llm_failed 分支
    paper = {"id": "x", "title": "t", "summary": "s"}
    enhance_single(paper, CaptureChain(), prof, "Chinese")
    assert "方法太老" in captured_inputs.get("recent_notes", ""), captured_inputs.get("recent_notes")
    print("[3] 评语原文经 recent_notes 直通 AI 评分模板 ✓")
finally:
    if profile_backup:
        tmp = prof_path.with_suffix(".json.tmp")
        tmp.write_text(profile_backup, encoding="utf-8")
        tmp.replace(prof_path)
    conn.execute("DELETE FROM papers WHERE id=?", (TESTPID,))
    conn.commit()
    conn.close()
    stop_writer()

print("\n评语闭环回归通过 ✅")
