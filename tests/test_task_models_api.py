#!/usr/bin/env python3
"""按任务指定模型：task_model 解析链/GET 列表/PUT 覆盖与清除/校验拒绝。"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from db import init_db  # noqa: E402
init_db()

import api  # noqa: E402
from ai.llm import task_model, TASK_MODEL_VARS  # noqa: E402

# [1] task_model 解析链：任务覆盖 > MODEL_NAME > glm-5.3-flash
_M = ["MODEL_NAME", *TASK_MODEL_VARS.values()]
saved = {k: os.environ.get(k) for k in _M}
for k in _M:
    os.environ.pop(k, None)
try:
    assert task_model("enhance") == "glm-5.3-flash", "无任何配置时兜底"
    os.environ["MODEL_NAME"] = "glm-5.3"
    assert task_model("enhance") == "glm-5.3", "跟随默认"
    os.environ["ENHANCE_MODEL"] = "glm-5.3-flash"
    assert task_model("enhance") == "glm-5.3-flash", "任务覆盖优先"
    assert task_model("trend") == "glm-5.3", "其他任务不受影响"
    print("[1] task_model 解析链 ✓")
finally:
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)

tmpdir = tempfile.mkdtemp(prefix="llmmodels_")
env_file = Path(tmpdir) / ".env"
env_file.write_text("MODEL_NAME=glm-5.3-flash\nQUICK_FILTER_MODEL=glm-5.3-flash\n", encoding="utf-8")
api._ENV_PATH = str(env_file)
c = api.app.test_client()

try:
    # [2] GET：默认 + 10 任务 + 既有覆盖回显
    r = c.get("/api/llm-models").get_json()
    assert r["default"] == "glm-5.3-flash"
    assert len(r["tasks"]) == len(TASK_MODEL_VARS)
    qf = [t for t in r["tasks"] if t["id"] == "quick_filter"][0]
    assert qf["model"] == "glm-5.3-flash" and qf["label"], qf
    print("[2] GET 任务列表 ✓")

    # [3] PUT 校验拒绝：未知任务/非法模型名/空默认
    assert c.put("/api/llm-models", json={"nonexistent": "x"}).status_code == 400
    assert c.put("/api/llm-models", json={"trend": "bad name!"}).status_code == 400
    assert c.put("/api/llm-models", json={"default": ""}).status_code == 400
    print("[3] 非法输入拒绝 ✓")

    # [4] PUT 设置覆盖 + 改默认：.env 与进程 env 同步
    r4 = c.put("/api/llm-models", json={"trend": "glm-5.3", "default": "glm-5.3-flash"}).get_json()
    assert r4["default"] == "glm-5.3-flash"
    tr = [t for t in r4["tasks"] if t["id"] == "trend"][0]
    assert tr["model"] == "glm-5.3"
    content = env_file.read_text(encoding="utf-8")
    assert "TREND_MODEL=glm-5.3" in content and "QUICK_FILTER_MODEL=glm-5.3-flash" in content
    assert os.environ["TREND_MODEL"] == "glm-5.3"
    print("[4] 覆盖写入+即时生效 ✓")

    # [5] PUT 空值 = 清除覆盖（行删除，跟随默认）
    r5 = c.put("/api/llm-models", json={"trend": "", "quick_filter": ""}).get_json()
    content = env_file.read_text(encoding="utf-8")
    assert "TREND_MODEL" not in content and "QUICK_FILTER_MODEL" not in content
    assert "TREND_MODEL" not in os.environ
    tr = [t for t in r5["tasks"] if t["id"] == "trend"][0]
    assert tr["model"] == ""
    print("[5] 空值清除覆盖 ✓")
finally:
    api._ENV_PATH = "ai/.env"
    for k in (*TASK_MODEL_VARS.values(), "MODEL_NAME"):
        os.environ.pop(k, None)
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v

print("\n任务模型测试通过 ✅")
