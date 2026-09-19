#!/usr/bin/env python3
"""前端选择 AI 供应商：预设解析/Key 分供应商记忆/切换清按任务覆盖/thinking 参数按端点条件附加。"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from backend.db import init_db  # noqa: E402
init_db()

import backend.ai.llm as llm_mod  # noqa: E402
import backend.api as api  # noqa: E402


class FakeChat:
    fail_with = None
    last_kwargs = None

    def __init__(self, *a, **k):
        FakeChat.last_kwargs = k

    def invoke(self, _msg):
        if FakeChat.fail_with:
            raise RuntimeError(FakeChat.fail_with)
        return "pong"


GLM_KEY = "sk-" + "g" * 32
DS_KEY = "sk-" + "d" * 32
CU_KEY = "sk-" + "c" * 32
DS_BASE = "https://api.deepseek.com/v1"
CODING_BASE = "https://open.bigmodel.cn/api/coding/paas/v4/"

tmpdir = tempfile.mkdtemp(prefix="llmconf_")
env_file = Path(tmpdir) / ".env"
env_file.write_text(
    "# 注释要保留\n"
    f"OPENAI_BASE_URL={CODING_BASE}\n"
    "MODEL_NAME=glm-5.3-flash\n"
    "QUICK_FILTER_MODEL=glm-5.3-flash\n",
    encoding="utf-8",
)

_MANAGE_ENV = ["LLM_PROVIDER", "OPENAI_BASE_URL", "MODEL_NAME", "OPENAI_API_KEY",
               "QUICK_FILTER_MODEL", "KEYWORD_MODEL", "TOPIC_MODEL", "CLUSTER_MODEL",
               "CUSTOM_BASE_URL", "CUSTOM_MODEL",
               "PROVIDER_KEY_GLM_CODING", "PROVIDER_KEY_GLM_PAAS",
               "PROVIDER_KEY_DEEPSEEK", "PROVIDER_KEY_CUSTOM"]
saved = {k: os.environ.get(k) for k in _MANAGE_ENV}
for k in _MANAGE_ENV:
    os.environ.pop(k, None)
api._ENV_PATH = str(env_file)
c = api.app.test_client()
patcher = patch.object(llm_mod, "build_chat", lambda *a, **k: FakeChat(*a, **k))
patcher.start()

try:
    # [1] GET 默认：由 base_url 推断 glm_coding；四家供应商；无 Key
    r = c.get("/api/llm-config").get_json()
    assert r["provider"] == "glm_coding", r["provider"]
    assert len(r["providers"]) == 4 and r["key_configured"] is False
    print("[1] GET 供应商推断+列表 ✓")

    # [2] 未知供应商 / 缺 Key 拒绝
    assert c.put("/api/llm-config", json={"provider": "openai_gpt"}).status_code == 400
    assert c.put("/api/llm-config", json={"provider": "deepseek"}).status_code == 400
    assert FakeChat.last_kwargs is None, "参数校验失败不应发起验证"
    print("[2] 未知供应商/缺 Key 拒绝（不发起验证）✓")

    # [3] 验证失败不落盘
    FakeChat.fail_with = "Error code: 401 - Authentication Fails"
    assert c.put("/api/llm-config", json={"provider": "deepseek", "key": DS_KEY}).status_code == 400
    assert "LLM_PROVIDER" not in env_file.read_text(encoding="utf-8")
    print("[3] 验证失败不落盘 ✓")

    # [4] 先保存 GLM Key（记忆到 PROVIDER_KEY_GLM_CODING）
    FakeChat.fail_with = None
    r4 = c.put("/api/llm-config", json={"provider": "glm_coding", "key": GLM_KEY}).get_json()
    assert r4["ok"] is True and r4["cleared_overrides"] == []
    content = env_file.read_text(encoding="utf-8")
    assert f"PROVIDER_KEY_GLM_CODING={GLM_KEY}" in content
    print("[4] GLM Key 保存+分供应商记忆 ✓")

    # [5] 切到 DeepSeek：base/model 联动、清 QUICK_FILTER_MODEL、env 即时更新
    r5 = c.put("/api/llm-config", json={"provider": "deepseek", "key": DS_KEY}).get_json()
    assert r5["provider"] == "deepseek" and r5["model"] == "deepseek-chat"
    assert FakeChat.last_kwargs.get("base_url") == DS_BASE
    assert FakeChat.last_kwargs.get("api_key") == DS_KEY
    assert r5["cleared_overrides"] == ["QUICK_FILTER_MODEL"]
    content = env_file.read_text(encoding="utf-8")
    assert f"OPENAI_BASE_URL={DS_BASE}" in content and "MODEL_NAME=deepseek-chat" in content
    assert "LLM_PROVIDER=deepseek" in content and "QUICK_FILTER_MODEL" not in content
    assert "# 注释要保留" in content, "注释被破坏"
    assert os.environ["MODEL_NAME"] == "deepseek-chat" and "QUICK_FILTER_MODEL" not in os.environ
    g = c.get("/api/llm-config").get_json()
    assert g["provider"] == "deepseek" and g["key_configured"] is True
    print("[5] 切换 DeepSeek（联动+清覆盖+即时生效）✓")

    # [6] 切回 GLM 不带 Key：用记忆的 PROVIDER_KEY_GLM_CODING
    r6 = c.put("/api/llm-config", json={"provider": "glm_coding"}).get_json()
    assert r6["ok"] is True and FakeChat.last_kwargs.get("api_key") == GLM_KEY
    assert os.environ["MODEL_NAME"] == "glm-5.3-flash" and os.environ["OPENAI_BASE_URL"] == CODING_BASE
    print("[6] Key 记忆免重填 ✓")

    # [7] 自定义供应商：缺 base 拒绝；完整参数成功并记忆
    assert c.put("/api/llm-config", json={"provider": "custom", "key": CU_KEY}).status_code == 400
    r7 = c.put("/api/llm-config", json={"provider": "custom", "key": CU_KEY,
                                        "base_url": "http://localhost:8000/v1",
                                        "model": "my-model"}).get_json()
    assert r7["ok"] is True and r7["model"] == "my-model"
    content = env_file.read_text(encoding="utf-8")
    assert "CUSTOM_BASE_URL=http://localhost:8000/v1" in content and "CUSTOM_MODEL=my-model" in content
    print("[7] 自定义 OpenAI 兼容端点 ✓")
finally:
    patcher.stop()
    api._ENV_PATH = "backend/ai/.env"
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)

# [8] thinking 参数按端点条件附加（真实 build_chat，不发请求）
os.environ["OPENAI_API_KEY"] = "sk-test-dummy"
os.environ["OPENAI_BASE_URL"] = CODING_BASE
chat_glm = llm_mod.build_chat("glm-5.3-flash", thinking=False)
assert chat_glm.extra_body == {"thinking": {"type": "disabled"}}
chat_ds = llm_mod.build_chat("deepseek-chat", thinking=True, base_url=DS_BASE)
assert not getattr(chat_ds, "extra_body", None), "DeepSeek 端点不应携带 thinking 参数"
print("[8] thinking 仅 GLM 端点附带 ✓")

print("\nAI 供应商切换测试通过 ✅")
