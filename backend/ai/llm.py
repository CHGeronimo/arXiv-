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

# ── 全局频率控制（分时段动态限流） ─────────────────────────────
# 双闸设计：总闸 + bulk 闸（总数-1，留 1 槽给交互式单发——简报/趋势/想法
# 不与爬取风暴排队）。凌晨低峰期（GLM 配额更宽）自动放宽并发/间隔，
# 时段与两档并发均可在 ⚙️ 设置面板调整（LLM_NIGHT_* / LLM_DAY_CONCURRENCY）。
# 实测标定（白天）：并发4全绿 / 6约11%撞线由退避吸收 / 8恶化。
LLM_MAX_CONCURRENT = int(os.environ.get("LLM_MAX_CONCURRENT", "6"))   # 白天默认（保留供 env 覆盖）
LLM_MIN_INTERVAL = float(os.environ.get("LLM_MIN_INTERVAL", "0.8"))
_LIMITS_OVERRIDE: tuple | None = None  # 测试钩子：(concurrency, interval)
_llm_lock = threading.Lock()
_llm_last = 0.0


def _is_night_hour(h: int, start: int, end: int) -> bool:
    """凌晨窗口判定；start==end 视为不启用。支持跨午夜（如 22→6）。"""
    if start == end:
        return False
    if start < end:
        return start <= h < end
    return h >= start or h < end


def _llm_limits() -> tuple:
    """当前 (并发上限, 最小间隔)。凌晨档走夜窗设置，间隔减半。"""
    if _LIMITS_OVERRIDE is not None:
        return _LIMITS_OVERRIDE
    conc, interval = LLM_MAX_CONCURRENT, LLM_MIN_INTERVAL
    try:
        from backend.db import get_runtime_settings
        s = get_runtime_settings()
        h = __import__("datetime").datetime.now().hour
        if _is_night_hour(h, int(s.get("LLM_NIGHT_START", 0)), int(s.get("LLM_NIGHT_END", 8))):
            conc = int(s.get("LLM_NIGHT_CONCURRENCY", 9))
            interval = min(interval, 0.5)
        else:
            conc = int(s.get("LLM_DAY_CONCURRENCY", conc))
    except Exception:
        pass  # db 未就绪（早期导入）→ 用模块默认
    return max(1, conc), max(0.0, interval)


class _DynGate:
    """动态闸：限值随时段/设置变化（线程安全，限值上调后等待者自动放行）。"""

    def __init__(self, limit_fn):
        self._cond = threading.Condition()
        self._active = 0
        self._limit_fn = limit_fn

    def acquire(self) -> None:
        with self._cond:
            while self._active >= self._limit_fn():
                self._cond.wait(5.0)  # 限值上调后最多 5s 内被唤醒/重查
            self._active += 1

    def release(self) -> None:
        with self._cond:
            self._active -= 1
            self._cond.notify_all()


_TOTAL_GATE = _DynGate(lambda: _llm_limits()[0])
_BULK_GATE = _DynGate(lambda: max(1, _llm_limits()[0] - 1))

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
            _BULK_GATE.acquire()
            held.append(_BULK_GATE)
        _TOTAL_GATE.acquire()
        held.append(_TOTAL_GATE)
        with _llm_lock:
            wait = _llm_last + _llm_limits()[1] - time.monotonic()
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
