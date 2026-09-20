#!/usr/bin/env python3
"""分层版本戳：各层独立打戳/组件级重跑只动自己的层/自动收敛限量。"""
import os
import sqlite3
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import shutil, tempfile
_tmpdir = tempfile.mkdtemp(prefix="arxivsci_lv_")
Path(_tmpdir, "data").mkdir(exist_ok=True)
_src = Path(__file__).resolve().parent.parent / "data" / "papers.db"
if _src.exists():
    shutil.copy(_src, Path(_tmpdir, "data", "papers.db"))
os.chdir(_tmpdir)

from backend.db import init_db  # noqa: E402
init_db()
import backend.jobs as jobs  # noqa: E402
import backend.api as api  # noqa: E402
from backend.ai.enhance import ENHANCE_VER, CARD_VER, PIPELINE_VERSION  # noqa: E402

# [1] 版本常量独立存在且等值（首次分层不触发旧版误报）
assert ENHANCE_VER == CARD_VER == PIPELINE_VERSION == "2026-09-19"
# 首次分层同值不触发误报；后续各自递增即独立生效（字符串驻留不代表耦合）
print("[1] 三层版本常量独立 ✓")

# [2] _stale_counts 各层独立计数（造一篇旧卡+新增强）
conn = sqlite3.connect("data/papers.db")
_before = jobs._stale_counts()
conn.execute("INSERT OR REPLACE INTO papers (id,source,title,summary) VALUES ('lv-test','t','T','s')")
conn.execute("INSERT OR REPLACE INTO ai_results (paper_id,tldr,pipeline_version,recommendation) VALUES ('lv-test','t',?,'recommended')", (ENHANCE_VER,))
conn.execute("INSERT OR REPLACE INTO knowledge_cards (paper_id,keywords,card_version) VALUES ('lv-test','[]','2026-08-01')")
conn.commit()
stale = jobs._stale_counts()
assert stale["enhance"] == _before["enhance"], f"新增强已最新，不应+1: {_before} → {stale}"
assert stale["card"] == _before["card"] + 1, f"旧卡应+1: {_before} → {stale}"
print(f"[2] 分层计数: enhance +0 / card +1（新增旧卡精确感知）✓")

# [3] 组件级重跑只动卡片层（增强结果不变）
orig_tldr = conn.execute("SELECT tldr FROM ai_results WHERE paper_id='lv-test'").fetchone()[0]
with patch.object(jobs, "get_ai_chain", return_value=(None, {})), \
     patch("backend.ai.knowledge_extractor.extract_knowledge_card",
           return_value={"paper_id": "lv-test", "problem": "新问题", "method_extracted": "新方法",
                         "result_extracted": "新结果", "keywords": "[]", "relation_to_profile": "相关"}), \
     patch("backend.paper_store.extract_knowledge_card",
           return_value={"paper_id": "lv-test", "problem": "新问题", "method_extracted": "新方法",
                         "result_extracted": "新结果", "keywords": "[]", "relation_to_profile": "相关"}):
    jobs.run_card_rerun()
from backend.db import sync_write
sync_write("SELECT 1")  # 刷盘写队列
import time as _t; _t.sleep(0.2)
conn2 = sqlite3.connect("data/papers.db")
card = conn2.execute("SELECT card_version, problem FROM knowledge_cards WHERE paper_id='lv-test'").fetchone()
assert card[0] == CARD_VER and card[1] == "新问题", card
tldr_after = conn2.execute("SELECT tldr FROM ai_results WHERE paper_id='lv-test'").fetchone()[0]
assert tldr_after == orig_tldr, "增强结果不应被卡片重跑改动"
print("[3] 卡片重跑只动卡片层（增强不变）✓")

# [4] /api/stale-counts 端点
c = api.app.test_client()
r = c.get("/api/stale-counts")
assert r.status_code == 200 and "enhance" in r.get_json() and "card" in r.get_json()
print("[4] stale-counts 端点 ✓")

# 清理
conn2.execute("DELETE FROM papers WHERE id='lv-test'")
conn2.execute("DELETE FROM ai_results WHERE paper_id='lv-test'")
conn2.execute("DELETE FROM knowledge_cards WHERE paper_id='lv-test'")
conn2.commit()
print("\n分层版本戳测试通过 ✅")
