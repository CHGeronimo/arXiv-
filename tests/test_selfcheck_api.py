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


class _Msg:
    def __init__(self, content):
        self.content = content


class FakeChat:
    def invoke(self, _msg):
        return _Msg("pong 冒烟测试输出样本")


class FakeChain:
    def __init__(self, content):
        self.content = content

    def invoke(self, _inp):
        return _Msg(self.content)


def _httpx_by_url(url, **kw):
    return FakeResp()


FULLTEXT_JSON = ('{"method_implementation": "方法实现", "experimental_design": "实验设计",'
                 '"key_results_detail": "关键结果", "limitations": "局限",'
                 '"reproducibility": "可复现", "relevance_to_profile": "相关"}')


def _full_mocks():
    """网络/LLM 全部任务的 Mock 组合。"""
    from contextlib import ExitStack
    stack = ExitStack()
    stack.enter_context(patch.object(sc.httpx, "get", side_effect=_httpx_by_url))
    stack.enter_context(patch("backend.crawler.openalex_client.openalex_get",
                              return_value={"meta": {"count": 12345}}))
    stack.enter_context(patch("backend.crawler.openalex_client.quota_paused", return_value=False))
    stack.enter_context(patch("backend.jobs.get_scheduled_at",
                              return_value={"arxiv": "02:00", "crossref": "02:30"}))
    # LLM 基础设施（ping/digest/快筛链路/全文与趋势 chain 构造）
    stack.enter_context(patch("backend.ai.llm.build_chat", lambda *a, **k: FakeChat()))
    stack.enter_context(patch("backend.ai.quick_filter.build_quick_filter", return_value=FakeChat()))
    # 各任务入口（真实函数在自检里运行，测试替换为无副作用假实现）
    stack.enter_context(patch("backend.ai.keyword_expander.extract_keywords_strict",
                              return_value=["multi-agent", "POMDP", "game theory"]))
    stack.enter_context(patch("backend.api._academicize_note",
                              return_value="多智能体信用分配机制的规范性学术表述"))
    stack.enter_context(patch("backend.ai.knowledge_clustering._extract_themes",
                              return_value=["主题A", "主题B", "主题C"]))
    stack.enter_context(patch("backend.ai.enhance.build_chain", return_value=FakeChat()))
    stack.enter_context(patch("backend.ai.enhance.enhance_single",
                              return_value={"AI": {"tldr": "t", "recommendation": "recommended",
                                                  "relevance_score": 8}}))
    stack.enter_context(patch("backend.ai.knowledge_extractor.extract_knowledge_card_dict",
                              return_value={"paper_id": "x", "keywords": ["a"]}))
    stack.enter_context(patch("backend.ai.fulltext_analyzer._get_chain",
                              return_value=FakeChain(FULLTEXT_JSON)))
    stack.enter_context(patch("backend.ai.trend_analyzer._get_raw_chain",
                              return_value=FakeChain('{"hot_topics": ["MARL"]}')))
    stack.enter_context(patch("backend.ai.idea_checker._get_chain",
                              return_value=FakeChain("想法查重结构化输出样本")))
    # 反馈环主题去重（真实函数走 LLM，测试替换）
    stack.enter_context(patch("backend.api._deduplicate_topics",
                              return_value=["opponent modeling", "diffusion policy"]))
    return stack


c = api.app.test_client()

with _full_mocks():
    # [1] GET 未运行过 → 404
    assert c.get("/api/selftest").status_code == 404
    print("[1] 未运行时 404 ✓")

    # [2] 全 Mock 自检：全部 ok，30 项（网络6 + LLM 12 + API 5 + 数据3 + 存储/调度/版本/前端4）
    r = sc.run_selftest()
    fails = [ch for ch in r["checks"] if ch["status"] != "ok"]
    assert not fails, fails
    assert r["total"] == len(r["checks"]) == 30, r["total"]
    llm_names = [ch["name"] for ch in r["checks"] if ch["group"] == "LLM"]
    assert len(llm_names) == 12, llm_names
    assert sc.get_last_report() is r
    g = c.get("/api/selftest").get_json()
    assert g["ok"] == 30
    print(f"[2] 全 Mock 全通过（30 项，LLM {len(llm_names)} 条）✓")

    # [3] 失败路径：arXiv 网络异常 → 单项 fail，其余不受影响
    def _boom_arxiv(url, **kw):
        if "arxiv.org" in url:
            raise RuntimeError("connection refused")
        return FakeResp()
    with patch.object(sc.httpx, "get", side_effect=_boom_arxiv):
        r3 = sc.run_selftest()
    arxiv_ch = [ch for ch in r3["checks"] if ch["name"].startswith("arXiv")][0]
    assert arxiv_ch["status"] == "fail" and "connection refused" in arxiv_ch["detail"]
    assert r3["ok"] + r3["warn"] + r3["fail"] == r3["total"] == 30
    print("[3] 失败路径隔离 ✓")

    # [4] 警告路径：OpenAlex 配额熔断 → warn；评分任务失败独立成行
    with patch("backend.crawler.openalex_client.quota_paused", return_value=True), \
         patch("backend.ai.enhance.enhance_single",
               side_effect=RuntimeError("quota exhausted")):
        r4 = sc.run_selftest()
    quota_ch = [ch for ch in r4["checks"] if ch["name"] == "OpenAlex 配额"][0]
    enhance_ch = [ch for ch in r4["checks"] if ch["name"] == "深度评分（增强）"][0]
    assert quota_ch["status"] == "warn" and "熔断" in quota_ch["detail"]
    assert enhance_ch["status"] == "fail"
    print("[4] 警告路径 + LLM 任务失败独立成行 ✓")

    # [5] 触发端点：后台线程产出报告
    resp = c.post("/api/trigger/selftest")
    assert resp.status_code == 200 and resp.get_json()["job"] == "selftest"
    deadline = time.time() + 30
    st = None
    while time.time() < deadline:
        st = c.get("/api/jobs").get_json().get("selftest")
        if st and st["status"] == "done":
            break
        time.sleep(0.3)
    assert st and st["status"] == "done", st
    final = c.get("/api/selftest").get_json()
    assert final["total"] == 30
    print(f"[5] 触发→后台运行→状态+报告 ✓（{st['message']}）")

print("\n系统自检测试通过 ✅")
