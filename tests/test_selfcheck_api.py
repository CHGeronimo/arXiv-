#!/usr/bin/env python3
"""🧪 系统自检：全 Mock 冒烟（不打真实网络/LLM）、失败与警告路径、API 往返。"""
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from backend.db import init_db  # noqa: E402
init_db()

import backend.selfcheck as sc  # noqa: E402
import backend.api as api  # noqa: E402


class FakeResp:
    status_code = 200
    content = b"x" * 2048

    def raise_for_status(self):
        return None


class FakeChat:
    def invoke(self, _msg):
        return "pong"


def _httpx_by_url(url, **kw):
    return FakeResp()


def _full_mocks():
    """网络/LLM/调度全 Mock 的 patch 组合（with 嵌套用 ExitStack）。"""
    from contextlib import ExitStack
    stack = ExitStack()
    stack.enter_context(patch.object(sc.httpx, "get", side_effect=_httpx_by_url))
    stack.enter_context(patch("backend.crawler.openalex_client.openalex_get",
                              return_value={"meta": {"count": 12345}}))
    stack.enter_context(patch("backend.crawler.openalex_client.quota_paused", return_value=False))
    stack.enter_context(patch("backend.ai.llm.build_chat", lambda *a, **k: FakeChat()))
    stack.enter_context(patch("backend.ai.quick_filter.build_quick_filter", return_value=FakeChat()))
    stack.enter_context(patch("backend.jobs.get_scheduled_at",
                              return_value={"arxiv": "02:00", "crossref": "02:30"}))
    return stack


c = api.app.test_client()

with _full_mocks():
    # [1] GET 未运行过 → 404
    assert c.get("/api/selftest").status_code == 404
    print("[1] 未运行时 404 ✓")

    # [2] 全 Mock 自检：全部 ok，报告结构完整
    r = sc.run_selftest()
    assert r["fail"] == 0 and r["warn"] == 0, r
    assert r["total"] == len(r["checks"]) == 12, r["total"]
    assert all(ch["ms"] >= 0 and ch["detail"] for ch in r["checks"])
    groups = {ch["group"] for ch in r["checks"]}
    assert {"网络", "LLM", "存储", "调度", "版本", "前端"} <= groups
    assert sc.get_last_report() is r
    g = c.get("/api/selftest").get_json()
    assert g["ok"] == 12 and g["total"] == 12
    print("[2] 全 Mock 全通过（12 项）+ GET 报告 ✓")

    # [3] 失败路径：arXiv 网络异常 → 单项 fail，其余不受影响
    def _boom_arxiv(url, **kw):
        if "arxiv.org" in url:
            raise RuntimeError("connection refused")
        return FakeResp()
    with patch.object(sc.httpx, "get", side_effect=_boom_arxiv):
        r3 = sc.run_selftest()
    arxiv_ch = [ch for ch in r3["checks"] if ch["name"].startswith("arXiv")][0]
    assert arxiv_ch["status"] == "fail" and "connection refused" in arxiv_ch["detail"]
    assert r3["ok"] + r3["warn"] + r3["fail"] == r3["total"] == 12
    print("[3] 失败路径隔离 ✓")

    # [4] 警告路径：OpenAlex 配额熔断 → warn
    with patch("backend.crawler.openalex_client.quota_paused", return_value=True):
        r4 = sc.run_selftest()
    quota_ch = [ch for ch in r4["checks"] if ch["name"] == "OpenAlex 配额"][0]
    assert quota_ch["status"] == "warn" and "熔断" in quota_ch["detail"]
    print("[4] 警告路径（配额熔断）✓")

    # [5] 触发端点：selftest 已入白名单，后台线程产出报告
    resp = c.post("/api/trigger/selftest")
    assert resp.status_code == 200 and resp.get_json()["job"] == "selftest"
    deadline = time.time() + 20
    while time.time() < deadline:
        st = c.get("/api/jobs").get_json().get("selftest")
        if st and st["status"] == "done":
            break
        time.sleep(0.3)
    assert st and st["status"] == "done", st
    assert "✓" in st["message"] and "✗" in st["message"]
    final = c.get("/api/selftest").get_json()
    assert final["total"] == 12
    print(f"[5] 触发→后台运行→状态+报告 ✓（{st['message']}）")

print("\n系统自检测试通过 ✅")
