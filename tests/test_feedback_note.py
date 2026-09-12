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
# 完全隔离：测试期间把 api 的 profile 指到临时副本，
# 与运行中 daemon 的跨进程写互不干扰（锁只在本进程内有效）
tmp_prof = Path("/tmp/arxivsci-test-profile.json")
tmp_prof.write_text(prof_path.read_text(encoding="utf-8"), encoding="utf-8")
api._PROFILE_PATH = str(tmp_prof)
prof_path = tmp_prof  # 后续断言读临时副本
profile_backup = prof_path.read_text(encoding="utf-8")
json.loads(profile_backup)  # 校验可解析

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

    # [1b] 空串显式清除评语（旧 bug：''被转None→COALESCE保留→评语复活）
    c.post("/api/feedback", json={"paper_id": TESTPID, "rating": "like", "note": ""})
    row = conn.execute("SELECT note FROM feedback WHERE paper_id=?", (TESTPID,)).fetchone()
    assert row[0] in ("", None), f"清空失败: {row}"
    print("[1b] 空串清除评语 ✓")

    # [3] 评语进主题提取 prompt + 原文入 profile.feedback_notes（[1b]已清空，重设）
    conn.execute("UPDATE feedback SET note='方法太老，没有MARL实证' WHERE paper_id=?", (TESTPID,))
    conn.commit()
    class FakeResp:
        content = '["note topic A"]'
    class FakeLLM:
        def __init__(self, *a, **k): pass
        def invoke(self, prompt):
            captured.append(prompt)
            return FakeResp()
    captured = []
    import time as _t

    def _wait_note(sub, timeout=8):
        # 运行中 daemon 的后台线程可能并发写 profile（旧快照覆盖）——轮询等待
        for _ in range(int(timeout / 0.3)):
            notes_list = json.loads(prof_path.read_text(encoding="utf-8")).get("feedback_notes", [])
            if any(sub in n for n in notes_list):
                return notes_list
            _t.sleep(0.3)
        return json.loads(prof_path.read_text(encoding="utf-8")).get("feedback_notes", [])

    with patch("ai.llm.build_chat", return_value=FakeLLM()), \
         patch.object(api, "reset_ai_chain"):
        api._update_profile_from_feedback(TESTPID, "like")
    assert any("方法太老" in p for p in captured), "评语必须进入提取 prompt"
    assert any("方法太老" in n for n in _wait_note("方法太老")), "feedback_notes 应包含测试评语"
    print("[2] 评语进提取 prompt + feedback_notes 持久化 ✓")

    # [2b] 改评语 → feedback_notes 替换旧条目（note_index），不堆积
    conn.execute("UPDATE feedback SET note='新评语：希望多推实证' WHERE paper_id=?", (TESTPID,))
    conn.commit()
    with patch("ai.llm.build_chat", return_value=FakeLLM()), \
         patch.object(api, "reset_ai_chain"):
        api._update_profile_from_feedback(TESTPID, "like")
    notes_final = _wait_note("新评语")
    assert any("新评语" in n for n in notes_final), notes_final
    assert not any("方法太老" in n for n in notes_final), f"旧评语未替换: {notes_final}"
    print("[2b] 改评语 → 旧条目被替换（note_index）✓")

    # [2c] 取消投票 → 该论文评语条目被移除
    api._remove_paper_note(TESTPID)
    prof = json.loads(prof_path.read_text(encoding="utf-8"))
    assert not any("新评语" in n for n in prof.get("feedback_notes", []))
    print("[2c] 取消投票 → 评语条目清理 ✓")

    # [4] feedback_notes 直通评分提示词（[2c]已按生命周期清理测试评语，重新种入验证模板管道）
    from ai.enhance import enhance_single

    prof = json.loads(prof_path.read_text(encoding="utf-8"))
    prof["feedback_notes"] = ["[like] 方法太老，没有MARL实证"]

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
    prof_path.write_text(profile_backup, encoding="utf-8")
    api._PROFILE_PATH = "research_profile.json"  # 还原
    conn.execute("DELETE FROM papers WHERE id=?", (TESTPID,))
    conn.commit()
    conn.close()
    stop_writer()

print("\n评语闭环回归通过 ✅")
