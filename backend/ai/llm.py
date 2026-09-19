"""Shared ChatOpenAI factory with per-task GLM thinking-intensity control.

GLM-5.x thinking models burn most of their latency on reasoning. Volume and
interactive tasks don't need it, so each call site picks a default:

  thinking=False → {"type": "disabled"}  ~3x faster; fine for classification,
                   keyword expansion, extraction, short JSON output
  thinking=True  → {"type": "enabled"}   deep reasoning for quality-critical,
                   low-frequency analysis (scoring, fulltext, trend, digest)

The THINKING env var overrides globally: auto (default, per-task defaults)
| on | off.

全局 LLM 频率控制（2026-09-12 实锤 Error 1302 速率限制）：
所有 LLM 请求经此处的信号量+最小间隔节流，并对 429/1302 做指数退避重试。
LLM_MAX_CONCURRENT（默认4）与 LLM_MIN_INTERVAL（默认0.8s）可调。
2026-09-19 实测标定（GLM Coding Plan）：并发4 三轮全绿；并发6 16/18
（~11% 触发 1302，由指数退避吸收后净吞吐仍高于 4）；并发8 7/8 且明显恶化。
默认取 6（激进档，用户指定）——退避兜底，撞线自动回落重试不丢任务。
"""
from __future__ import annotations

import logging
import os
import threading
import time

from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# ── 全局频率控制 ─────────────────────────────────────────────
# 双闸设计：总闸 = LLM_MAX_CONCURRENT（实测安全边界），bulk 闸 = 总数-1。
# 批量爬取任务（快筛/增强/聚类…）走 bulk 闸；简报/趋势/想法/关键词提取
# 这类用户点一下就等结果的"交互式单发"走 priority——不与爬取风暴排队
# （2026-09-19 实锤：两抓取任务并行时简报单发调用排在 10 个 worker 队尾）。
LLM_MAX_CONCURRENT = int(os.environ.get("LLM_MAX_CONCURRENT", "6"))
LLM_MIN_INTERVAL = float(os.environ.get("LLM_MIN_INTERVAL", "0.8"))
_LLM_SEM = threading.Semaphore(LLM_MAX_CONCURRENT)
_BULK_SEM = threading.Semaphore(max(1, LLM_MAX_CONCURRENT - 1))
_llm_lock = threading.Lock()
_llm_last = 0.0

_RATE_LIMIT_MARKERS = ("1302", "429", "速率限制", "rate limit", "Rate limit")

# 任务级模型覆盖：行为 → 环境变量（未设则跟随 MODEL_NAME）。
# 前端 ⚙️ 设置面板的任务模型表直接读写这些变量。
TASK_MODEL_VARS = {
    "quick_filter": "QUICK_FILTER_MODEL",   # 快速相关性预筛（关思考）
    "keyword": "KEYWORD_MODEL",             # 关键词扩展/类别推荐（关思考）
    "topic": "TOPIC_MODEL",                 # feedback 主题提取/评语改写（关思考）
    "cluster": "CLUSTER_MODEL",             # 知识图谱聚类（关思考）
    "enhance": "ENHANCE_MODEL",             # 深度增强/评分（开思考）
    "fulltext": "FULLTEXT_MODEL",           # 全文深读（开思考）
    "trend": "TREND_MODEL",                 # 周/月趋势雷达（开思考）
    "digest": "DIGEST_MODEL",               # 今日简报（开思考）
    "knowledge": "KNOWLEDGE_MODEL",         # 知识卡片提取（关思考）
    "idea": "IDEA_MODEL",                   # 研究想法查重（开思考）
}


def task_model(task: str) -> str:
    """任务模型解析：任务级覆盖 → MODEL_NAME → glm-5.3-flash。"""
    var = TASK_MODEL_VARS.get(task, "")
    return ((os.environ.get(var, "") if var else "")
            or os.environ.get("MODEL_NAME", "")
            or "glm-5.3-flash")


def _acquire_llm_slot(priority: bool = False) -> list:
    """占并发槽并对请求起点做全局最小间隔。返回持有的闸（供释放）。

    priority=True 只占总闸不占 bulk 闸——爬取风暴占满 bulk 时，
    交互式单发（简报/趋势/想法）仍有 1 个保留槽可用。
    """
    global _llm_last
    held = []
    try:
        if not priority:
            _BULK_SEM.acquire()
            held.append(_BULK_SEM)
        _LLM_SEM.acquire()
        held.append(_LLM_SEM)
        with _llm_lock:
            wait = _llm_last + LLM_MIN_INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            _llm_last = time.monotonic()
    except BaseException:
        for sem in held:
            sem.release()
        raise
    return held


def _is_rate_limit_error(e: Exception) -> bool:
    msg = str(e)
    return any(m in msg for m in _RATE_LIMIT_MARKERS)


class _RateLimitedChat(ChatOpenAI):
    """invoke 级节流 + 429/1302 指数退避重试（3/6/9s，共3次）。"""

    _priority: bool = False  # build_chat(priority=True) 注入

    def invoke(self, input, *args, **kwargs):  # noqa: A002
        last_err: Exception | None = None
        for attempt in range(4):
            held = _acquire_llm_slot(priority=self._priority)
            try:
                return super().invoke(input, *args, **kwargs)
            except Exception as e:
                if _is_rate_limit_error(e) and attempt < 3:
                    import random
                    base = 3 * (attempt + 1)
                    wait = base + random.uniform(0, base * 0.5)  # 抖动：惊群错峰
                    logger.warning(f"GLM 限流（{str(e)[:80]}...），退避 {wait:.1f}s 后重试（第 {attempt + 1}/3 次）")
                    time.sleep(wait)
                    last_err = e
                    continue
                raise
            finally:
                for sem in reversed(held):
                    sem.release()
        raise last_err  # pragma: no cover — 4次全限流


def build_chat(
    model: str,
    *,
    thinking: bool = False,
    temperature: float | None = None,
    timeout: float = 120,
    **kwargs,
) -> ChatOpenAI:
    mode = os.environ.get("THINKING", "auto").strip().lower()
    if mode in ("on", "1", "true", "enabled"):
        thinking = True
    elif mode in ("off", "0", "false", "disabled"):
        thinking = False

    # SDK 自带 429 重试（默认2次）会与我们的指数退避叠加成双层重试风暴，
    # 1302 高发期实际请求量翻倍——关掉，统一走本模块的抖动退避
    params: dict = {"timeout": timeout, "max_retries": 0}
    # thinking 开关是 GLM 专属参数：DeepSeek 等其他 OpenAI 兼容端点不认识，
    # 可能直接 400——只在 bigmodel 端点上附带
    effective_base = kwargs.get("base_url") or os.environ.get("OPENAI_BASE_URL", "") or ""
    if "bigmodel" in effective_base:
        params["extra_body"] = {"thinking": {"type": "enabled" if thinking else "disabled"}}
    if temperature is not None:
        params["temperature"] = temperature
    priority = bool(kwargs.pop("priority", False))
    params.update(kwargs)
    chat = _RateLimitedChat(model=model, **params)
    chat._priority = priority
    return chat
