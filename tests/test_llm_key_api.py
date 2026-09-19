#!/usr/bin/env python3
"""前端修改 GLM API Key：脱敏回显/验证失败不落盘/成功写回 .env 保留其他行/进程内即时生效。"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from db import init_db  # noqa: E402
init_db()

import ai.llm  # noqa: E402
import api  # noqa: E402


class FakeChat:
    fail_with = None
    last_kwargs = None

    def __init__(self, *a, **k):
        FakeChat.last_kwargs = k

    def invoke(self, _msg):
        if FakeChat.fail_with:
            raise RuntimeError(FakeChat.fail_with)
        return "pong"


GOOD_KEY = "sk-" + "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
GOOD_KEY2 = "sk-" + "z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4"

tmpdir = tempfile.mkdtemp(prefix="llmkey_")
env_file = Path(tmpdir) / ".env"
# 预置 .env 已有其他配置——写回时必须原样保留
env_file.write_text(
    "# 注释也要保留\nOPENAI_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4/\nMODEL_NAME=glm-5.3-flash\n",
    encoding="utf-8",
)

old_path = api._ENV_PATH
old_env = os.environ.get("OPENAI_API_KEY")
os.environ.pop("OPENAI_API_KEY", None)
api._ENV_PATH = str(env_file)
c = api.app.test_client()

# 全程 Mock 掉 build_chat（PUT 验证走 FakeChat，绝不打真实 GLM）
patcher = patch.object(ai.llm, "build_chat", lambda *a, **k: FakeChat(*a, **k))
patcher.start()

try:
    # [1] GET：未配置状态（.env 无 key 行且 env 为空）
    r = c.get("/api/llm-key").get_json()
    assert r["configured"] is False and r["masked"] == "", r
    print("[1] GET 未配置回显 ✓")

    # [2] PUT 格式校验：过短 key 拒绝且不触发验证
    assert c.put("/api/llm-key", json={"key": "short"}).status_code == 400
    assert FakeChat.last_kwargs is None, "格式错误不应发起验证请求"
    print("[2] 格式校验（不发起验证）✓")

    # [3] PUT 验证失败：不落盘、不改进程 env
    FakeChat.fail_with = "Error code: 401 - Incorrect API key"
    r3 = c.put("/api/llm-key", json={"key": GOOD_KEY})
    assert r3.status_code == 400 and "未保存" in r3.get_json()["error"]
    assert "OPENAI_API_KEY" not in env_file.read_text(encoding="utf-8")
    assert "OPENAI_API_KEY" not in os.environ
    print("[3] 验证失败不落盘 ✓")

    # [4] PUT 成功：写入 .env（替换式追加，保留其他行）+ 进程内即时生效 + 脱敏回显
    FakeChat.fail_with = None
    r4 = c.put("/api/llm-key", json={"key": GOOD_KEY}).get_json()
    assert r4["ok"] is True and r4["configured"] is True
    assert FakeChat.last_kwargs.get("api_key") == GOOD_KEY, "验证必须用提交的新 key"
    content = env_file.read_text(encoding="utf-8")
    assert f"OPENAI_API_KEY={GOOD_KEY}" in content
    assert "OPENAI_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4/" in content, "其他配置行被破坏"
    assert "MODEL_NAME=glm-5.3-flash" in content and "# 注释也要保留" in content
    assert os.environ.get("OPENAI_API_KEY") == GOOD_KEY, "进程 env 未即时更新"
    g = c.get("/api/llm-key").get_json()
    assert g["configured"] is True
    assert g["masked"].startswith("sk-a1") and g["masked"].endswith("5p6") and "****" in g["masked"]
    print("[4] 验证成功写回+即时生效+脱敏 ✓")

    # [5] 再次更新：key 行替换而非堆积
    c.put("/api/llm-key", json={"key": GOOD_KEY2})
    lines = [l for l in env_file.read_text(encoding="utf-8").splitlines() if l.startswith("OPENAI_API_KEY=")]
    assert lines == [f"OPENAI_API_KEY={GOOD_KEY2}"], lines
    assert os.environ.get("OPENAI_API_KEY") == GOOD_KEY2
    print("[5] 二次更新替换不堆积 ✓")
finally:
    patcher.stop()
    api._ENV_PATH = old_path
    if old_env is not None:
        os.environ["OPENAI_API_KEY"] = old_env
    else:
        os.environ.pop("OPENAI_API_KEY", None)

print("\nLLM Key 前端修改测试通过 ✅")
