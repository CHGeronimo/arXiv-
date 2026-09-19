#!/usr/bin/env python3
"""监听地址：resolve_bind 优先级/PUT 校验与写入/待重启提示。"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from backend.db import init_db  # noqa: E402
init_db()

import backend.api as api  # noqa: E402
import backend.daemon as daemon  # noqa: E402

_M = ["DAEMON_HOST", "DAEMON_PORT", "DAEMON_HOST_ACTUAL", "DAEMON_PORT_ACTUAL"]
saved = {k: os.environ.get(k) for k in _M}
for k in _M:
    os.environ.pop(k, None)

try:
    # [1] resolve_bind 优先级：命令行 > env > 默认；非法 env 端口回退
    assert daemon.resolve_bind(None, None) == ("127.0.0.1", 8080)
    os.environ["DAEMON_HOST"] = "0.0.0.0"
    os.environ["DAEMON_PORT"] = "9090"
    assert daemon.resolve_bind(None, None) == ("0.0.0.0", 9090)
    assert daemon.resolve_bind("127.0.0.1", 8080) == ("127.0.0.1", 8080), "命令行最优先"
    os.environ["DAEMON_PORT"] = "not-a-port"
    assert daemon.resolve_bind(None, None) == ("0.0.0.0", 8080), "非法端口回退"
    del os.environ["DAEMON_HOST"]; del os.environ["DAEMON_PORT"]
    print("[1] resolve_bind 优先级链 ✓")

    tmpdir = tempfile.mkdtemp(prefix="bind_")
    env_file = Path(tmpdir) / ".env"
    env_file.write_text("MODEL_NAME=glm-5.3-flash\n", encoding="utf-8")
    api._ENV_PATH = str(env_file)
    c = api.app.test_client()

    # [2] GET 默认（未配置）
    r = c.get("/api/bind").get_json()
    assert r["host"] == "127.0.0.1" and r["port"] == "8080"
    print("[2] GET 默认监听 ✓")

    # [3] PUT 校验：非法端口/host 拒绝；localhost 归一化
    assert c.put("/api/bind", json={"host": "0.0.0.0", "port": 99999}).status_code == 400
    assert c.put("/api/bind", json={"host": "0.0.0.0", "port": "abc"}).status_code == 400
    assert c.put("/api/bind", json={"host": "evil.example.com", "port": 8080}).status_code == 400
    print("[3] 非法地址拒绝 ✓")

    # [4] PUT 成功：写 .env + 进程 env + 局域网警告标志 + 待重启
    r4 = c.put("/api/bind", json={"host": "localhost", "port": 9090}).get_json()
    assert r4["ok"] is True and r4["host"] == "127.0.0.1" and r4["port"] == 9090
    assert r4["restart_required"] is True and r4["lan_warning"] is False
    content = env_file.read_text(encoding="utf-8")
    assert "DAEMON_HOST=127.0.0.1" in content and "DAEMON_PORT=9090" in content
    assert "MODEL_NAME=glm-5.3-flash" in content, "其余配置保留"
    g = c.get("/api/bind").get_json()
    assert g["host"] == "127.0.0.1" and g["port"] == "9090"
    assert g["pending_restart"] is True, "改过但未重启应提示"
    print("[4] 写入+待重启提示 ✓")

    # [5] 0.0.0.0 带局域网警告；actual 与配置一致时无待重启
    r5 = c.put("/api/bind", json={"host": "0.0.0.0", "port": 9090}).get_json()
    assert r5["lan_warning"] is True
    os.environ["DAEMON_HOST_ACTUAL"] = "0.0.0.0"
    os.environ["DAEMON_PORT_ACTUAL"] = "9090"
    g5 = c.get("/api/bind").get_json()
    assert g5["pending_restart"] is False and g5["actual_port"] == 9090
    print("[5] 局域网警告+一致判定 ✓")
finally:
    api._ENV_PATH = "backend/ai/.env"
    for k in _M:
        if saved[k] is not None:
            os.environ[k] = saved[k]
        else:
            os.environ.pop(k, None)

print("\n监听地址测试通过 ✅")
