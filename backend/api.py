"""arXiv 每日电讯 — Flask API layer."""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import threading
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from backend.crawler.subs_store import Subscriptions, Journal, Conference, Author

from backend.paper_store import (
    append_paper, find_paper_by_id, load_all_papers,
    reset_ai_chain,
)
from backend.db import get_conn, queue_write, sync_write
from backend.jobs import (
    get_job_status, run_arxiv_job, run_crossref_job, run_dblp_job,
    run_s2_job, run_author_job, run_citations_job,
    run_retro_enhance, run_digest_job, _subs_lock,
)


# ── Logging setup ──────────────────────────────────────────────────
_LOG_DIR = os.environ.get("LOG_DIR", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_log_fmt = logging.Formatter(
    "%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(_LOG_DIR, "arxivsci.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setFormatter(_log_fmt)

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_log_fmt)

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
# Clear any handlers added by basicConfig or Flask reloader
_root_logger.handlers.clear()
_root_logger.addHandler(_file_handler)
_root_logger.addHandler(_console_handler)
# Prevent basicConfig from adding another StreamHandler
logging.getLogger().propagate = False

_log_path = os.path.abspath(os.path.join(_LOG_DIR, "arxivsci.log"))
_root_logger.info(f"日志文件: {_log_path}")

_WEB_DIR = str(Path(__file__).resolve().parent.parent / "web")
app = Flask(__name__, static_folder=_WEB_DIR, static_url_path="")

SUBS_PATH = "subscriptions.json"
CARD_COLS = ["paper_id", "problem", "method_extracted", "result_extracted", "keywords", "relation_to_profile"]


def _git_hash() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


_DAEMON_VERSION = _git_hash()
_disk_version_cache: dict = {"hash": "", "checked": 0.0}


def _load_subs() -> Subscriptions:
    return Subscriptions.load(SUBS_PATH)


def _save_subs(subs: Subscriptions) -> None:
    subs.save(SUBS_PATH)


_PROFILE_PATH = "research_profile.json"


def _write_profile_atomic(profile: dict) -> None:
    """Atomic profile write (tmp+replace) — concurrent readers (tests, the
    running daemon) never see a torn file."""
    tmp = _PROFILE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _PROFILE_PATH)


# ── Static ────────────────────────────────────────────────────────

# The project root doubles as the static dir; never serve secrets or data.
# Flask 的内置 static 路由（static_folder="."）会先于自定义路由匹配，
# 所以用 before_request 拦截，保证任何路径都过黑名单。
# ── LAN 暴露认证（审计 P0）：绑定 0.0.0.0 时，非本机请求必须携带 token ──
# token 首次进入 0.0.0.0 模式时自动生成并写入 .env；本机(127.0.0.1/::1)豁免，
# token 在设置面板仅对本机可见。同时校验 Host 头防 DNS rebinding。
_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


def _bind_is_lan() -> bool:
    return os.environ.get("DAEMON_HOST_ACTUAL", "") == "0.0.0.0"


def _ensure_lan_token() -> str:
    tok = os.environ.get("LAN_ACCESS_TOKEN", "")
    if not tok:
        import secrets
        tok = secrets.token_urlsafe(24)
        try:
            _write_env_vars({"LAN_ACCESS_TOKEN": tok})
            os.environ["LAN_ACCESS_TOKEN"] = tok
            logging.getLogger(__name__).info("已生成 LAN 访问 token（见 ⚙️ 设置面板）")
        except OSError:
            pass
    return tok


@app.before_request
def _lan_auth_guard():
    if request.path.startswith("/api/") and _bind_is_lan():
        if request.remote_addr not in ("127.0.0.1", "::1"):
            supplied = request.headers.get("X-Access-Token", "")
            if supplied != os.environ.get("LAN_ACCESS_TOKEN", ""):
                return jsonify({"error": "unauthorized: LAN 访问需 X-Access-Token（本机 ⚙️ 设置面板查看）"}), 401
    # Host 校验（防 DNS rebinding，两种绑定模式都查）
    host = (request.host or "").split(":")[0]
    if host and host not in _ALLOWED_HOSTS and host != _lan_local_ip():
        return jsonify({"error": "bad host"}), 403
    return None


def _lan_local_ip() -> str:
    cached = getattr(_lan_local_ip, "_ip", None)
    if cached:
        return cached
    ip = ""
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as _s:
            _s.connect(("8.8.8.8", 80))
            ip = _s.getsockname()[0]
    except Exception:
        pass
    _lan_local_ip._ip = ip
    return ip


_STATIC_BLOCKED_PREFIXES = (
    "backend/", "scripts/", "tests/", "data/", "logs/", ".git", ".claude", ".understand-anything",
    "__pycache__", "design-system/", "docs/",
)
_STATIC_BLOCKED_SUFFIXES = (".env", ".db", ".db-wal", ".db-shm", ".pyc")


@app.before_request
def _block_sensitive_static():
    p = request.path.lstrip("/").lower()
    if p.startswith(_STATIC_BLOCKED_PREFIXES) or p.endswith(_STATIC_BLOCKED_SUFFIXES):
        return jsonify({"error": "forbidden"}), 403
    return None


@app.route("/")
def index():
    return send_from_directory(_WEB_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path: str):
    return send_from_directory(_WEB_DIR, path)


# ── Papers ────────────────────────────────────────────────────────

@app.route("/api/papers", methods=["GET"])
def get_papers():
    source_filter = request.args.get("source", "all")
    article_type = request.args.get("type", "all")
    light = request.args.get("light", "1") != "0"
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = min(50000, max(1, int(request.args.get("per_page", 50))))
    except (ValueError, TypeError):
        per_page = 50

    papers = load_all_papers(light=light)

    if source_filter != "all":
        papers = [p for p in papers if p.get("source") == source_filter]
    if article_type != "all":
        papers = [p for p in papers if p.get("article_type") == article_type]

    total = len(papers)
    start = (page - 1) * per_page
    return jsonify({
        "papers": papers[start:start + per_page],
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@app.route("/api/paper/<path:paper_id>", methods=["GET"])
def get_paper(paper_id: str):
    """Full paper record incl. all AI text fields (detail-modal lazy load)."""
    paper = find_paper_by_id(paper_id)
    if paper is None:
        return jsonify({"error": "not found"}), 404
    # 评分归因：论文文本 ↔ 反馈学到的偏好主题匹配（详情页"为什么推荐"）
    try:
        profile = json.loads(Path(_PROFILE_PATH).read_text(encoding="utf-8")) \
            if Path(_PROFILE_PATH).exists() else {}
    except (OSError, json.JSONDecodeError):
        profile = {}
    card = get_conn().execute(
        "SELECT keywords FROM knowledge_cards WHERE paper_id = ?", (paper_id,)).fetchone()
    card_kw = ""
    if card and card[0]:
        try:
            kws = json.loads(card[0]) if isinstance(card[0], str) else card[0]
            card_kw = " ".join(kws) if isinstance(kws, list) else str(kws)
        except (json.JSONDecodeError, TypeError):
            card_kw = str(card[0])
    text = " ".join([
        str(paper.get("title", "")), str(paper.get("summary", ""))[:500],
        str(paper.get("categories", "")), card_kw,
    ])
    paper["preference"] = {
        "liked": _match_preference_topics(profile.get("liked_topics", []), text),
        "disliked": _match_preference_topics(profile.get("disliked_topics", []), text),
    }
    return jsonify(paper)


def _match_preference_topics(topics: list, text: str) -> list:
    """主题 ↔ 论文文本宽松匹配：主题整体为子串，或主题词项几乎全部出现。"""
    text_l = (text or "").lower()
    if not text_l:
        return []
    hits = []
    for t in topics:
        t = str(t or "").strip()
        if not t:
            continue
        tl = t.lower()
        if tl in text_l:
            hits.append(t)
            continue
        toks = [w for w in re.split(r"[^a-z0-9\u4e00-\u9fff]+", tl) if len(w) >= 4]
        if toks and sum(1 for w in toks if w in text_l) >= max(1, len(toks) - 1):
            hits.append(t)
    return hits


@app.route("/api/stats")
def get_stats():
    import time as _time
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    source_counts: dict[str, int] = {}
    for row in conn.execute("SELECT source, COUNT(*) as cnt FROM papers GROUP BY source"):
        source_counts[row[0]] = row[1]
    must_read = conn.execute(
        "SELECT COUNT(*) FROM ai_results WHERE recommendation='must-read'").fetchone()[0]
    # 磁盘代码 hash 60s 缓存（stats 被 15s 轮询，不能每次都起子进程）
    now = _time.monotonic()
    if now - _disk_version_cache["checked"] > 60:
        _disk_version_cache["hash"] = _git_hash()
        _disk_version_cache["checked"] = now
    subs = _load_subs()
    return jsonify({
        "total_papers": total,
        "by_source": source_counts,
        "arxiv_categories": subs.arxiv_categories,
        "crossref_journals": len(subs.crossref_journals),
        "must_read": must_read,
        "daemon_version": _DAEMON_VERSION,
        "disk_version": _disk_version_cache["hash"],
        "code_stale": _disk_version_cache["hash"] != _DAEMON_VERSION,
    })


# ── Subscriptions ─────────────────────────────────────────────────

@app.route("/api/subscriptions", methods=["GET"])
def get_subscriptions():
    return jsonify(_load_subs().to_dict())


@app.route("/api/subscriptions", methods=["PUT"])
def put_subscriptions():
    data = request.get_json()
    if not data:
        return jsonify({"error": "empty body"}), 400
    # 持有与夜间任务相同的锁：否则任务 _post_run 在锁内"读旧→写新"期间，
    # 本接口的直接覆写会被其旧快照回滚（用户订阅修改丢失）
    with _subs_lock:
        try:
            cats = data.get("arxiv", {}).get("categories", [])
            journals_data = data.get("crossref", {}).get("journals", [])
            conferences_data = data.get("conferences", [])
            search_keywords = data.get("search", {}).get("keywords", [])
            use_profile = data.get("search", {}).get("useProfile", True)
            authors_data = data.get("authors", [])
            journals = [
                Journal(issn=j["issn"], name=j["name"], last_updated=j.get("lastUpdated"))
                for j in journals_data
            ]
            conferences = [
                Conference(venue=c["venue"], last_updated=c.get("lastUpdated"))
                for c in conferences_data
            ]
            authors = [
                Author(
                    name=a["name"],
                    author_id=a.get("authorId", a.get("author_id", "")),
                    affiliation=a.get("affiliation", ""),
                    paper_count=a.get("paperCount", a.get("paper_count", 0)),
                    last_updated=a.get("lastUpdated"),
                )
                for a in authors_data
            ]
            subs = Subscriptions(
                arxiv_categories=cats,
                crossref_journals=journals,
                conferences=conferences,
                search_keywords=search_keywords,
                use_profile_keywords=use_profile,
                authors=authors,
            )
            _save_subs(subs)
            return jsonify(subs.to_dict())
        except Exception as e:
            return jsonify({"error": str(e)}), 400


# ── Profile ───────────────────────────────────────────────────────

@app.route("/api/profile", methods=["GET"])
def get_profile():
    profile_path = Path(_PROFILE_PATH)
    if profile_path.exists():
        return jsonify(json.loads(profile_path.read_text(encoding="utf-8")))
    return jsonify({"direction": "", "keywords": [], "quality_criteria": ""})


@app.route("/api/profile", methods=["PUT"])
def put_profile():
    data = request.get_json()
    if not data:
        return jsonify({"error": "empty body"}), 400
    # Merge with existing profile: the UI forms only send direction/keywords/
    # quality_criteria, so blindly overwriting would wipe feedback-learned
    # fields (liked_topics / disliked_topics). Payload keys still win.
    profile_path = Path(_PROFILE_PATH)
    merged: dict = {}
    if profile_path.exists():
        try:
            merged = json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception:
            merged = {}
    merged.update(data)
    _write_profile_atomic(merged)
    reset_ai_chain()
    return jsonify(merged)


# ── Keyword Extraction from Direction ─────────────────────────────

@app.route("/api/extract-keywords", methods=["POST"])
def extract_keywords():
    """Two-stage LLM extraction of search keywords from a research direction.

    Stage 1 mines every concept in the direction (Chinese→English); stage 2
    expands seeds + concepts into query variants. liked/disliked topics are
    pulled from the saved profile for personalization. Results are cached
    by expand_keywords, so repeated clicks with the same inputs are fast.
    """
    data = request.get_json() or {}
    direction = data.get("direction", "").strip()
    if not direction:
        return jsonify({"error": "direction required"}), 400

    seeds = data.get("seed_keywords") or []
    profile = {}
    try:
        profile = json.loads(Path(_PROFILE_PATH).read_text(encoding="utf-8"))
    except Exception:
        pass
    if not seeds:
        seeds = profile.get("keywords", [])

    from backend.ai.keyword_expander import extract_keywords_strict
    try:
        keywords = extract_keywords_strict(
            direction=direction,
            seed_keywords=seeds,
            quality_criteria=data.get("quality_criteria") or profile.get("quality_criteria", ""),
            liked=profile.get("liked_topics", []),
            disliked=profile.get("disliked_topics", []),
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"关键词提取失败: {e}")
        return jsonify({"error": str(e)}), 502
    return jsonify({"keywords": keywords, "count": len(keywords)})


# ── Jobs / Triggers ───────────────────────────────────────────────

@app.route("/api/selftest", methods=["GET"])
def get_selftest_report():
    """最近一次 🧪 系统自检报告（未跑过返回 404）。"""
    from backend.selfcheck import get_last_report
    report = get_last_report()
    if not report:
        return jsonify({"error": "尚未运行过自检"}), 404
    return jsonify(report)


@app.route("/api/trigger/<job>", methods=["POST"])
def trigger_job(job: str):
    from backend.selfcheck import run_selftest_job
    from backend.jobs import get_job_status as _gjs
    _cur = (_gjs().get(job) or {})
    if _cur.get("status") == "running":
        return jsonify({"error": f"任务 {job} 正在运行中（进度见 ⚡ 任务中心），已拒绝重复触发"}), 409
    job_funcs = {
        "arxiv": run_arxiv_job,
        "crossref": run_crossref_job,
        "dblp": run_dblp_job,
        "s2": run_s2_job,
        "author": run_author_job,
        "citations": run_citations_job,
        "selftest": run_selftest_job,
    }
    if job not in job_funcs:
        return jsonify({"error": "unknown job"}), 400
    threading.Thread(target=job_funcs[job], daemon=True).start()
    return jsonify({"status": "triggered", "job": job})


@app.route("/api/trigger/enhance", methods=["POST"])
def trigger_enhance():
    threading.Thread(target=run_retro_enhance, daemon=True).start()
    return jsonify({"status": "triggered", "job": "enhance"})


@app.route("/api/trigger/digest", methods=["POST"])
def trigger_digest():
    """Regenerate today's digest on demand (normally nightly after arxiv)."""
    from backend.ai.digest import generate_digest
    threading.Thread(target=generate_digest, daemon=True).start()
    return jsonify({"status": "triggered", "job": "digest"})


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    from backend.jobs import get_scheduled_at
    return jsonify({**get_job_status(), "__scheduled__": get_scheduled_at()})


# ── Runtime Settings（前端可改的抓取/调度配置）────────────────────

_SETTINGS_META = {
    "NIGHT_START": {"label": "每日起始小时（0-23，默认2=凌晨）", "type": "int", "min": 0, "max": 23, "restart": False},
    "STAGGER_MINUTES": {"label": "任务错峰间隔分钟（5-120）", "type": "int", "min": 5, "max": 120, "restart": False},
    "RUN_ON_START": {"label": "daemon 启动立即全量跑一轮", "type": "bool", "restart": True},
    "DBLP_ROTATE_DAYS": {"label": "DBLP 会议轮换天数（1=每天全量）", "type": "int", "min": 1, "max": 30, "restart": False},
    "S2_ROTATE_DAYS": {"label": "S2 关键词轮换天数（1=每天全量）", "type": "int", "min": 1, "max": 30, "restart": False},
    "LOCAL_FILTER": {"label": "本地零成本预筛（省 LLM 配额）", "type": "bool", "restart": False},
    "LLM_NIGHT_START": {"label": "LLM 凌晨放宽起始小时（0-23）", "type": "int", "min": 0, "max": 23, "restart": False},
    "LLM_NIGHT_END": {"label": "LLM 凌晨放宽结束小时（0-23）", "type": "int", "min": 0, "max": 23, "restart": False},
    "LLM_DAY_CONCURRENCY": {"label": "LLM 白天并发（实测安全 6）", "type": "int", "min": 1, "max": 12, "restart": False},
    "LLM_NIGHT_CONCURRENCY": {"label": "LLM 凌晨并发（低峰可放宽，如 9）", "type": "int", "min": 1, "max": 12, "restart": False},
    "CONVERGE_PCT": {"label": "夜间收敛百分比（每轮处理旧版量%，1-50）", "type": "int", "min": 1, "max": 50, "restart": False},
    "CONVERGE_MAX_MIN": {"label": "夜间收敛时间上限分钟（5-120）", "type": "int", "min": 5, "max": 120, "restart": False},
}


@app.route("/api/settings", methods=["GET"])
def get_settings():
    from backend.db import get_runtime_settings
    from backend.jobs import get_scheduled_at
    s = get_runtime_settings(force=True)
    resp = {"settings": s, "meta": _SETTINGS_META, "scheduled": get_scheduled_at()}
    if _bind_is_lan():
        resp["lan_access_token"] = _ensure_lan_token()
    return jsonify(resp)


@app.route("/api/settings", methods=["PUT"])
def put_settings():
    data = request.get_json() or {}
    from backend.db import save_runtime_settings
    clean = {}
    for key, val in data.items():
        if key not in _SETTINGS_META:
            continue
        meta = _SETTINGS_META[key]
        if meta["type"] == "bool":
            clean[key] = bool(val)
        else:
            try:
                iv = int(val)
            except (TypeError, ValueError):
                return jsonify({"error": f"{key} 需为整数"}), 400
            if not (meta["min"] <= iv <= meta["max"]):
                return jsonify({"error": f"{key} 需在 {meta['min']}-{meta['max']} 之间"}), 400
            clean[key] = iv
    if not clean:
        return jsonify({"error": "无有效设置项"}), 400
    merged = save_runtime_settings(clean)
    try:
        from backend.jobs import replan_scheduler
        replan_scheduler()  # 时间类设置变更立即重排
    except Exception as e:
        logging.getLogger(__name__).warning(f"重排时间表失败（下次调度仍会生效）: {e}")
    from backend.jobs import get_scheduled_at
    return jsonify({"settings": merged, "scheduled": get_scheduled_at()})


# ── LLM 供应商配置（前端选择 GLM/DeepSeek/自定义：验证→写回 ai/.env→即时生效）──

_ENV_PATH = "backend/ai/.env"

_LLM_PROVIDERS = {
    "glm_coding": {"label": "GLM Coding Plan（订阅）", "base_url": "https://open.bigmodel.cn/api/coding/paas/v4/", "model": "glm-5.3-flash"},
    "glm_paas": {"label": "GLM 按量付费", "base_url": "https://open.bigmodel.cn/api/paas/v4/", "model": "glm-5.3-flash"},
    "deepseek": {"label": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "custom": {"label": "自定义（OpenAI 兼容端点）", "base_url": "", "model": ""},
}
# 切换供应商时必须清掉的按任务模型覆盖——它们指向旧供应商的模型名，
# 留着会让部分任务打到新端点时报 model not found（全集见 ai.llm.TASK_MODEL_VARS）
def _task_model_var_names() -> tuple:
    from backend.ai.llm import TASK_MODEL_VARS
    return tuple(TASK_MODEL_VARS.values())


def _provider_key_var(pid: str) -> str:
    return f"PROVIDER_KEY_{pid.upper()}"


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 10:
        return "****"
    return f"{key[:5]}****{key[-4:]}"


def _read_env_vars() -> dict:
    out = {}
    try:
        for line in Path(_ENV_PATH).read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


def _effective_env() -> dict:
    """ai/.env 内容叠加进程 env（PUT 后的即时修改体现在这里）。"""
    env = _read_env_vars()
    env.update(dict(os.environ))
    return env


def _write_env_vars(updates: dict, removes: tuple = ()) -> None:
    """按键更新/删除 ai/.env 行，其余配置与注释原样保留；原子写。"""
    path = Path(_ENV_PATH)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    out, done = [], set()
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            out.append(line)
            continue
        key = s.split("=", 1)[0].strip()
        if key in removes:
            continue
        if key in updates:
            out.append(f"{key}={updates[key]}")
            done.add(key)
        else:
            out.append(line)
    for k, v in updates.items():
        if k not in done:
            out.append(f"{k}={v}")
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tmp, path)


def _active_provider_id(env: dict | None = None) -> str:
    env = env or _effective_env()
    pid = (env.get("LLM_PROVIDER") or "").strip()
    if pid in _LLM_PROVIDERS:
        return pid
    base = (env.get("OPENAI_BASE_URL") or "").strip()
    for k, v in _LLM_PROVIDERS.items():
        if v["base_url"] and base == v["base_url"]:
            return k
    return "custom" if base else "glm_coding"


@app.route("/api/llm-config", methods=["GET"])
def get_llm_config():
    env = _effective_env()
    pid = _active_provider_id(env)
    providers = []
    for k, v in _LLM_PROVIDERS.items():
        providers.append({
            "id": k,
            "label": v["label"],
            # 当前供应商显示实际生效值（模型名可能被用户改过），其余显示预设
            "base_url": env.get("OPENAI_BASE_URL", "") if k == pid else v["base_url"],
            "model": env.get("MODEL_NAME", "") if k == pid else v["model"],
            "key_set": bool(env.get(_provider_key_var(k), "")),
        })
    key = env.get("OPENAI_API_KEY", "")
    return jsonify({
        "provider": pid,
        "base_url": env.get("OPENAI_BASE_URL", ""),
        "model": env.get("MODEL_NAME", ""),
        "key_configured": bool(key),
        "key_masked": _mask_key(key),
        "providers": providers,
    })


@app.route("/api/llm-config", methods=["PUT"])
def put_llm_config():
    data = request.get_json() or {}
    pid = (data.get("provider") or "").strip()
    if pid not in _LLM_PROVIDERS:
        return jsonify({"error": "未知供应商"}), 400
    preset = _LLM_PROVIDERS[pid]
    env = _effective_env()
    prev_pid = _active_provider_id(env)

    if pid == "custom":
        base_url = (data.get("base_url") or env.get("CUSTOM_BASE_URL", "")).strip()
        model = (data.get("model") or env.get("CUSTOM_MODEL", "")).strip()
        if not base_url.startswith(("http://", "https://")) or not model:
            return jsonify({"error": "自定义供应商需填写 Base URL（http(s):// 开头）和模型名"}), 400
    else:
        base_url = (data.get("base_url") or "").strip() or preset["base_url"]
        model = (data.get("model") or "").strip() or preset["model"]

    # Key：本次提交 > 该供应商记忆 > （未切换时）当前生效 Key
    key = (data.get("key") or "").strip()
    if not key:
        key = env.get(_provider_key_var(pid), "").strip()
        if not key and pid == prev_pid:
            key = env.get("OPENAI_API_KEY", "").strip()
    if len(key) < 16:
        return jsonify({"error": "缺少有效 API Key（请先粘贴该供应商的 Key）"}), 400

    # 用目标供应商的 base/model/key 实测一次最小请求；失败不落盘
    from backend.ai.llm import build_chat, task_model
    try:
        chat = build_chat(model, thinking=False, timeout=20, api_key=key, base_url=base_url)
        chat.invoke("ping")
    except Exception as e:
        logging.getLogger(__name__).warning(f"LLM 供应商验证失败 [{pid}]: {str(e)[:120]}")
        return jsonify({"error": f"验证失败（未保存）: {str(e)[:160]}"}), 400

    updates = {
        "LLM_PROVIDER": pid,
        "OPENAI_BASE_URL": base_url,
        "MODEL_NAME": model,
        "OPENAI_API_KEY": key,
        _provider_key_var(pid): key,
    }
    removes, cleared = [], []
    if pid == "custom":
        updates["CUSTOM_BASE_URL"] = base_url
        updates["CUSTOM_MODEL"] = model
    if pid != prev_pid:
        # 清掉指向旧供应商模型名的按任务覆盖
        for v in _task_model_var_names():
            if env.get(v):
                removes.append(v)
                cleared.append(v)

    try:
        _write_env_vars(updates, tuple(removes))
    except OSError as e:
        return jsonify({"error": f"验证通过但写入 ai/.env 失败: {e}"}), 500
    # 即时生效：pipeline 每次 build_chat 都重新解析 env，无需重启 daemon
    for k, v in updates.items():
        os.environ[k] = v
    for v in removes:
        os.environ.pop(v, None)
    logging.getLogger(__name__).info(
        f"LLM 供应商切换: {prev_pid} → {pid}（{model} @ {base_url}，Key {_mask_key(key)}）"
    )
    return jsonify({"ok": True, "provider": pid, "model": model, "base_url": base_url,
                    "key_masked": _mask_key(key), "cleared_overrides": cleared})


@app.route("/api/llm-key", methods=["GET"])
def get_llm_key():
    k = _effective_env().get("OPENAI_API_KEY", "")
    return jsonify({"configured": bool(k), "masked": _mask_key(k)})


@app.route("/api/llm-key", methods=["PUT"])
def put_llm_key():
    """只更新当前供应商的 Key（供应商切换走 /api/llm-config）。"""
    data = request.get_json() or {}
    key = (data.get("key") or "").strip()
    if len(key) < 16:
        return jsonify({"error": "Key 格式不对（API Key 通常 30+ 位）"}), 400
    env = _effective_env()
    from backend.ai.llm import build_chat, task_model
    try:
        chat = build_chat(env.get("MODEL_NAME", "glm-5.3-flash"), thinking=False, timeout=20, api_key=key)
        chat.invoke("ping")
    except Exception as e:
        logging.getLogger(__name__).warning(f"LLM Key 验证失败: {str(e)[:120]}")
        return jsonify({"error": f"验证失败（未保存）: {str(e)[:160]}"}), 400
    updates = {"OPENAI_API_KEY": key, _provider_key_var(_active_provider_id(env)): key}
    try:
        _write_env_vars(updates)
    except OSError as e:
        return jsonify({"error": f"验证通过但写入 ai/.env 失败: {e}"}), 500
    for k, v in updates.items():
        os.environ[k] = v
    logging.getLogger(__name__).info(f"LLM API Key 已更新（{_mask_key(key)}）")
    return jsonify({"ok": True, "configured": True, "masked": _mask_key(key)})


# ── 任务级模型（前端逐任务指定模型；空 = 跟随默认）─────────────────

_TASK_LABELS = {
    "quick_filter": "快速预筛（关思考）",
    "keyword": "关键词扩展 / 类别推荐（关思考）",
    "topic": "主题提取 / 评语改写（关思考）",
    "cluster": "知识图谱聚类（关思考）",
    "enhance": "深度增强 / 评分（开思考）",
    "fulltext": "全文深读（开思考）",
    "trend": "周/月趋势雷达（开思考）",
    "digest": "今日简报（开思考）",
    "knowledge": "知识卡片提取（关思考）",
    "idea": "研究想法查重（开思考）",
}

_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,63}$")


def _model_suggestions() -> list:
    pid = _active_provider_id()
    if pid == "deepseek":
        return ["deepseek-chat", "deepseek-reasoner"]
    if pid.startswith("glm"):
        return ["glm-5.3-flash"]
    return []


@app.route("/api/llm-models", methods=["GET"])
def get_llm_models():
    from backend.ai.llm import TASK_MODEL_VARS
    env = _effective_env()
    tasks = [
        {"id": tid, "label": _TASK_LABELS.get(tid, tid), "model": env.get(var, "")}
        for tid, var in TASK_MODEL_VARS.items()
    ]
    return jsonify({"default": env.get("MODEL_NAME", ""),
                    "tasks": tasks, "suggestions": _model_suggestions()})


@app.route("/api/llm-models", methods=["PUT"])
def put_llm_models():
    from backend.ai.llm import TASK_MODEL_VARS
    data = request.get_json() or {}
    env = _effective_env()
    updates, removes = {}, []
    for k, v in data.items():
        if k == "default":
            var = "MODEL_NAME"
        else:
            var = TASK_MODEL_VARS.get(k)
            if not var:
                return jsonify({"error": f"未知任务: {k}"}), 400
        m = (v or "").strip()
        if m:
            if not _MODEL_NAME_RE.match(m):
                return jsonify({"error": f"模型名不合法: {m[:40]}"}), 400
            updates[var] = m
        else:
            if var == "MODEL_NAME":
                return jsonify({"error": "默认模型不能为空"}), 400
            if env.get(var):
                removes.append(var)  # 空 = 清除覆盖，跟随默认
    if not updates and not removes:
        return jsonify({"error": "无有效修改"}), 400
    try:
        _write_env_vars(updates, tuple(removes))
    except OSError as e:
        return jsonify({"error": f"写入 ai/.env 失败: {e}"}), 500
    for k, v in updates.items():
        os.environ[k] = v
    for v in removes:
        os.environ.pop(v, None)
    logging.getLogger(__name__).info(
        f"任务模型已更新: {[f'{k}={v}' for k, v in updates.items()] + [f'-{r}' for r in removes]}"
    )
    return get_llm_models()


# ── 监听地址（HOST/PORT 写入 ai/.env，重启 daemon 生效）────────────

_BIND_HOST_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


@app.route("/api/bind", methods=["GET"])
def get_bind():
    env = _effective_env()
    try:
        actual_port = int(os.environ.get("DAEMON_PORT_ACTUAL", "0") or 0)
    except ValueError:
        actual_port = 0
    return jsonify({
        "host": env.get("DAEMON_HOST", "") or "127.0.0.1",
        "port": env.get("DAEMON_PORT", "") or "8080",
        "actual_host": os.environ.get("DAEMON_HOST_ACTUAL", ""),
        "actual_port": actual_port,
        # 配置与实际不一致 = 改过但 daemon 未重启
        "pending_restart": (env.get("DAEMON_HOST", "") or "127.0.0.1") != (os.environ.get("DAEMON_HOST_ACTUAL", "") or "127.0.0.1")
        or str(env.get("DAEMON_PORT", "") or "8080") != str(actual_port or "8080"),
    })


@app.route("/api/bind", methods=["PUT"])
def put_bind():
    data = request.get_json() or {}
    host = (data.get("host") or "").strip()
    if host == "localhost":
        host = "127.0.0.1"
    try:
        port = int(data.get("port"))
    except (TypeError, ValueError):
        return jsonify({"error": "端口需为整数"}), 400
    if not (1 <= port <= 65535):
        return jsonify({"error": "端口需在 1-65535 之间"}), 400
    if host not in ("127.0.0.1", "0.0.0.0") and not _BIND_HOST_RE.match(host):
        return jsonify({"error": "地址需为 127.0.0.1 / 0.0.0.0 或具体 IPv4"}), 400
    try:
        _write_env_vars({"DAEMON_HOST": host, "DAEMON_PORT": str(port)})
    except OSError as e:
        return jsonify({"error": f"写入 ai/.env 失败: {e}"}), 500
    os.environ["DAEMON_HOST"] = host
    os.environ["DAEMON_PORT"] = str(port)
    logging.getLogger(__name__).info(f"监听地址已更新: {host}:{port}（重启 daemon 后生效）")
    return jsonify({"ok": True, "host": host, "port": port, "restart_required": True,
                    "lan_warning": host == "0.0.0.0"})


# ── Digest ────────────────────────────────────────────────────────

@app.route("/api/digest/<date_str>", methods=["GET"])
def get_digest(date_str: str):
    # 文件优先，文件缺失（被清理/换机器）时从 digests 表回退
    digest_path = Path("digests") / f"{date_str}.md"
    if digest_path.exists():
        return digest_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/markdown"}
    row = get_conn().execute("SELECT content FROM digests WHERE date = ?", (date_str,)).fetchone()
    if row:
        return row[0], 200, {"Content-Type": "text/markdown"}
    return jsonify({"error": "digest not found"}), 404


@app.route("/api/digests", methods=["GET"])
def list_digests():
    digest_dir = Path("digests")
    file_dates = {d.stem for d in digest_dir.glob("*.md")} if digest_dir.exists() else set()
    db_dates = {r[0] for r in get_conn().execute("SELECT date FROM digests")}
    return jsonify({"digests": sorted(file_dates | db_dates, reverse=True)})


# ── Feedback ──────────────────────────────────────────────────────

@app.route("/api/feedback", methods=["POST"])
def save_feedback():
    """字段级更新：每个 UI 动作只写自己的字段，其余 COALESCE 保留。

    这样点赞/评语/滑杆三类 POST 的到达顺序无关紧要（此前评语请求携带
    快照里的 rating，与点赞请求竞争会互相覆盖）。取消投票用
    clear_rating=true 显式表达（rating 缺省/空 = 不修改）。"""
    data = request.json or {}
    paper_id = data.get("paper_id", "")
    if not paper_id:
        return jsonify({"error": "paper_id required"}), 400

    clear_rating = bool(data.get("clear_rating"))
    rating = data.get("rating") or None
    relevance = data.get("relevance")
    novelty = data.get("novelty")
    # note 三态：缺省=None(保留)；空串=显式清除；非空=更新
    note = data.get("note")
    if note is not None:
        note = str(note).strip()[:200]

    if rating and rating not in ("like", "dislike"):
        return jsonify({"error": "invalid rating"}), 400

    sync_write(
        """INSERT INTO feedback (paper_id, rating, relevance, novelty, note, updated_at)
           VALUES (?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(paper_id) DO UPDATE SET
             rating = CASE WHEN ? THEN NULL ELSE COALESCE(?, rating) END,
             relevance = COALESCE(excluded.relevance, relevance),
             novelty = COALESCE(excluded.novelty, novelty),
             note = COALESCE(excluded.note, note),
             updated_at = datetime('now')""",
        (paper_id, rating, relevance, novelty, note,
         1 if clear_rating else 0, rating),
    )
    # 按写后生效的 rating 决定画像动作（与请求字段无关，彻底免竞态）
    row = get_conn().execute(
        "SELECT rating FROM feedback WHERE paper_id = ?", (paper_id,)
    ).fetchone()
    eff = row["rating"] if row else None
    if eff in ("like", "dislike"):
        # LLM 主题提取可能耗时数秒，放后台线程避免阻塞点赞请求
        threading.Thread(target=_update_profile_from_feedback, args=(paper_id, eff), daemon=True).start()
    elif eff is None:
        # 取消投票：清理该论文在 feedback_notes 中的评语条目
        threading.Thread(target=_remove_paper_note, args=(paper_id,), daemon=True).start()
    return jsonify({"status": "saved"})


@app.route("/api/feedback", methods=["GET"])
def get_feedback():
    conn = get_conn()
    rows = conn.execute("SELECT paper_id, rating, relevance, novelty, note, updated_at FROM feedback").fetchall()
    result = {}
    for row in rows:
        result[row[0]] = {
            "rating": row[1], "relevance": row[2],
            "novelty": row[3], "note": row[4], "updated_at": row[5],
        }
    return jsonify(result)


# ── Bookmarks / Read state (server-side, was localStorage-only) ────

def _set_feedback_flag(paper_id: str, column: str, value: bool) -> bool:
    if column not in ("bookmarked", "is_read"):
        return False
    import sqlite3
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT OR IGNORE INTO feedback (paper_id) VALUES (?)", (paper_id,))
        conn.execute(f"UPDATE feedback SET {column} = ? WHERE paper_id = ?", (1 if value else 0, paper_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        logging.getLogger(__name__).warning(f"收藏/已读目标论文不存在: {paper_id}")
        return False


@app.route("/api/bookmarks", methods=["GET"])
def get_bookmarks():
    conn = get_conn()
    bookmarks = [r[0] for r in conn.execute("SELECT paper_id FROM feedback WHERE bookmarked = 1")]
    reads = [r[0] for r in conn.execute("SELECT paper_id FROM feedback WHERE is_read = 1")]
    return jsonify({"bookmarks": bookmarks, "reads": reads})


@app.route("/api/bookmark", methods=["POST"])
def set_bookmark():
    data = request.get_json() or {}
    pid = data.get("paper_id", "")
    if not pid:
        return jsonify({"error": "paper_id required"}), 400
    if not _set_feedback_flag(pid, "bookmarked", bool(data.get("on"))):
        return jsonify({"error": "paper not found"}), 404
    return jsonify({"status": "saved"})


@app.route("/api/read", methods=["POST"])
def mark_read_api():
    data = request.get_json() or {}
    pid = data.get("paper_id", "")
    if not pid:
        return jsonify({"error": "paper_id required"}), 400
    if not _set_feedback_flag(pid, "is_read", True):
        return jsonify({"error": "paper not found"}), 404
    return jsonify({"status": "saved"})


# ── Knowledge Cards (L1) ──────────────────────────────────────────

@app.route("/api/knowledge-cards", methods=["GET"])
def get_knowledge_cards():
    query = request.args.get("q", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
    except (ValueError, TypeError):
        per_page = 50

    conn = get_conn()
    if query:
        like_q = f"%{query}%"
        rows = conn.execute("""
            SELECT kc.paper_id, kc.problem, kc.method_extracted, kc.result_extracted,
                   kc.keywords, kc.relation_to_profile, kc.extracted_at, p.title, p.source
            FROM knowledge_cards kc JOIN papers p ON kc.paper_id = p.id
            WHERE kc.keywords LIKE ? OR kc.problem LIKE ? OR kc.method_extracted LIKE ? OR kc.result_extracted LIKE ?
            ORDER BY kc.extracted_at DESC
        """, (like_q, like_q, like_q, like_q)).fetchall()
    else:
        rows = conn.execute("""
            SELECT kc.paper_id, kc.problem, kc.method_extracted, kc.result_extracted,
                   kc.keywords, kc.relation_to_profile, kc.extracted_at, p.title, p.source
            FROM knowledge_cards kc JOIN papers p ON kc.paper_id = p.id
            ORDER BY kc.extracted_at DESC
        """).fetchall()

    cards = []
    for row in rows:
        keywords = row["keywords"]
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except (json.JSONDecodeError, TypeError):
                keywords = []
        cards.append({
            "paper_id": row["paper_id"], "problem": row["problem"],
            "method_extracted": row["method_extracted"], "result_extracted": row["result_extracted"],
            "keywords": keywords, "relation_to_profile": row["relation_to_profile"],
            "extracted_at": row["extracted_at"], "title": row["title"], "source": row["source"],
        })

    total = len(cards)
    start = (page - 1) * per_page
    return jsonify({"cards": cards[start:start + per_page], "total": total, "page": page})


@app.route("/api/paper/<path:paper_id>/card", methods=["GET"])
def get_paper_card(paper_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM knowledge_cards WHERE paper_id = ?", (paper_id,)).fetchone()
    if row is None:
        return jsonify({"card": None})
    keywords = row["keywords"]
    if isinstance(keywords, str):
        try:
            keywords = json.loads(keywords)
        except (json.JSONDecodeError, TypeError):
            keywords = []
    return jsonify({"card": {
        "paper_id": row["paper_id"], "problem": row["problem"],
        "method_extracted": row["method_extracted"], "result_extracted": row["result_extracted"],
        "keywords": keywords, "relation_to_profile": row["relation_to_profile"],
        "extracted_at": row["extracted_at"],
    }})


@app.route("/api/trigger/knowledge-extract", methods=["POST"])
def trigger_knowledge_extract():
    threading.Thread(target=_retro_knowledge_extract, daemon=True).start()
    return jsonify({"status": "triggered", "job": "knowledge-extract"})


def _retro_knowledge_extract():
    from backend.ai.knowledge_extractor import extract_knowledge_card
    from backend.ai.enhance import load_research_profile

    conn = get_conn()
    profile = load_research_profile()
    rows = conn.execute("""
        SELECT a.paper_id, a.tldr, a.motivation, a.method, a.result, a.conclusion, p.title, p.summary
        FROM ai_results a JOIN papers p ON a.paper_id = p.id
        LEFT JOIN knowledge_cards kc ON a.paper_id = kc.paper_id
        WHERE kc.paper_id IS NULL AND a.recommendation != 'ignore'
    """).fetchall()

    logger = logging.getLogger("knowledge-extract")
    logger.info(f"知识卡片抽取: {len(rows)} 篇待处理")
    from backend.jobs import _set_job_status as _kstat
    _kstat("knowledge", "running", f"{len(rows)} 篇待提取卡片",
           progress={"done": 0, "total": len(rows)})

    for i, row in enumerate(rows):
        paper = {
            "id": row["paper_id"], "title": row["title"], "summary": row["summary"],
            "AI": {"tldr": row["tldr"], "motivation": row["motivation"], "method": row["method"], "result": row["result"], "conclusion": row["conclusion"]},
        }
        card = extract_knowledge_card(paper, profile)
        if card:
            queue_write(
                "INSERT OR REPLACE INTO knowledge_cards (paper_id, problem, method_extracted, result_extracted, keywords, relation_to_profile) VALUES (?,?,?,?,?,?)",
                (card["paper_id"], card["problem"], card["method_extracted"], card["result_extracted"], card["keywords"], card["relation_to_profile"]),
            )
        if (i + 1) % 50 == 0 or (i + 1) == len(rows):
            logger.info(f"知识卡片进度: {i + 1}/{len(rows)}")
            _kstat("knowledge", "running", f"{i + 1}/{len(rows)}",
                   progress={"done": i + 1, "total": len(rows)})
    logger.info(f"知识卡片抽取完成: {len(rows)} 篇已处理")
    _kstat("knowledge", "done", f"{len(rows)} 篇卡片已提取，触发聚类")

    if len(rows) > 0:
        from backend.ai.knowledge_clustering import run_clustering
        n = run_clustering()
        logger.info(f"自动触发聚类完成: {n} 个聚类")


# ── Fulltext Analysis ─────────────────────────────────────────────

@app.route("/api/trigger/fulltext-analyze", methods=["POST"])
def trigger_fulltext_analyze():
    threading.Thread(target=_retro_fulltext_analyze, daemon=True).start()
    return jsonify({"status": "triggered", "job": "fulltext-analyze"})


def _retro_fulltext_analyze():
    from backend.ai.fulltext_analyzer import analyze_fulltext
    from backend.ai.enhance import load_research_profile

    conn = get_conn()
    profile = load_research_profile()
    rows = conn.execute("""
        SELECT a.paper_id, a.tldr, a.motivation, a.method, a.result, a.conclusion,
               p.title, p.summary, p.source, p.id
        FROM ai_results a JOIN papers p ON a.paper_id = p.id
        LEFT JOIN fulltext_analysis ft ON a.paper_id = ft.paper_id
        WHERE ft.paper_id IS NULL AND a.recommendation IN ('must-read', 'recommended')
              AND p.source = 'arxiv'
    """).fetchall()

    logger = logging.getLogger("fulltext-analyze")
    logger.info(f"正文深度分析: {len(rows)} 篇待处理")
    from backend.jobs import _set_job_status as _fstat
    _fstat("fulltext", "running", f"{len(rows)} 篇待深读",
           progress={"done": 0, "total": len(rows)})

    analyzed = 0
    for i, row in enumerate(rows):
        paper = {
            "id": row["id"], "source": row["source"],
            "title": row["title"], "summary": row["summary"],
            "AI": {"tldr": row["tldr"], "motivation": row["motivation"],
                   "method": row["method"], "result": row["result"], "conclusion": row["conclusion"]},
        }
        result = analyze_fulltext(paper, profile)
        if result:
            queue_write(
                "INSERT OR REPLACE INTO fulltext_analysis (paper_id, method_implementation, experimental_design, key_results_detail, limitations, reproducibility, relevance_to_profile, analyzed_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (result["paper_id"], result["method_implementation"], result["experimental_design"],
                 result["key_results_detail"], result["limitations"], result["reproducibility"],
                 result["relevance_to_profile"]),
            )
            analyzed += 1
        if (i + 1) % 10 == 0 or (i + 1) == len(rows):
            logger.info(f"正文分析进度: {i + 1}/{len(rows)} ({analyzed} 篇已分析)")
            _fstat("fulltext", "running", f"{i + 1}/{len(rows)}（成功 {analyzed}）",
                   progress={"done": i + 1, "total": len(rows)})

    logger.info(f"正文深度分析完成: {analyzed}/{len(rows)}")
    _fstat("fulltext", "done", f"{analyzed}/{len(rows)} 篇深读完成")


@app.route("/api/paper/<path:paper_id>/fulltext", methods=["GET"])
def get_paper_fulltext(paper_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM fulltext_analysis WHERE paper_id = ?", (paper_id,)).fetchone()
    if row is None:
        return jsonify({"analysis": None})
    return jsonify({"analysis": dict(row)})


# ── Knowledge Graph (L2) ──────────────────────────────────────────

@app.route("/api/knowledge-graph", methods=["GET"])
def get_knowledge_graph():
    conn = get_conn()
    saved = conn.execute("SELECT * FROM knowledge_clusters").fetchall()
    if saved:
        clusters = [dict(r) for r in saved]
    else:
        from backend.ai.knowledge_clustering import compute_clusters
        clusters = compute_clusters()
    nodes, edges = [], []
    for i, c in enumerate(clusters):
        pids = json.loads(c["paper_ids"]) if isinstance(c["paper_ids"], str) else c["paper_ids"]
        kws = json.loads(c["method_keywords"]) if isinstance(c["method_keywords"], str) else c["method_keywords"]
        domains = json.loads(c["problem_domains"]) if isinstance(c.get("problem_domains"), str) else (c.get("problem_domains") or [])
        nodes.append({"id": i, "name": c["cluster_name"], "size": len(pids), "keywords": kws[:5], "domains": [d for d in domains if d]})
    for i in range(len(clusters)):
        ki = set(json.loads(clusters[i]["method_keywords"]) if isinstance(clusters[i]["method_keywords"], str) else clusters[i]["method_keywords"])
        for j in range(i + 1, len(clusters)):
            kj = set(json.loads(clusters[j]["method_keywords"]) if isinstance(clusters[j]["method_keywords"], str) else clusters[j]["method_keywords"])
            shared = ki & kj
            if shared:
                edges.append({"source": i, "target": j, "weight": len(shared), "keywords": sorted(shared)})
    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/cluster/<path:cluster_name>/papers", methods=["GET"])
def cluster_papers(cluster_name: str):
    """某个聚类的论文列表（图谱下钻：点节点 → 弹窗列表 → 点开详情）。"""
    row = get_conn().execute(
        "SELECT paper_ids FROM knowledge_clusters WHERE cluster_name = ?",
        (cluster_name,)).fetchone()
    if not row:
        return jsonify({"error": "cluster not found"}), 404
    try:
        ids = set(json.loads(row[0]) if isinstance(row[0], str) else row[0])
    except (json.JSONDecodeError, TypeError):
        ids = set()
    # 审计 P2：SQL IN 直接取，不再全库加载（原来点一个节点=JOIN 2837 行）
    id_list = list(ids)
    papers = []
    for i in range(0, len(id_list), 900):  # SQLite 变量上限
        chunk = id_list[i:i + 900]
        ph = ",".join("?" * len(chunk))
        rows = get_conn().execute(
            f"SELECT p.id, p.title, p.published_date FROM papers p WHERE p.id IN ({ph})", chunk)
        papers.extend(dict(r) for r in rows)
    papers.sort(key=lambda p: (p.get("published_date") or ""), reverse=True)
    return jsonify({"cluster": cluster_name, "count": len(papers), "papers": papers})


@app.route("/api/trigger/card-rerun", methods=["POST"])
def trigger_card_rerun():
    """组件级重跑：只重提知识卡片（快 5 倍）。"""
    from backend.jobs import run_card_rerun
    threading.Thread(target=run_card_rerun, daemon=True).start()
    return jsonify({"status": "triggered", "job": "card_rerun"})


@app.route("/api/stale-counts", methods=["GET"])
def get_stale_counts():
    """各层旧版本计数（♻️ 菜单/自动收敛决策用）。"""
    from backend.jobs import _stale_counts
    return jsonify(_stale_counts())


@app.route("/api/trigger/enhance-rerun", methods=["POST"])
def trigger_enhance_rerun():
    """重跑旧流程 AI 结果（按 PIPELINE_VERSION 识别；中断可续）。"""
    from backend.jobs import run_stale_rerun
    threading.Thread(target=run_stale_rerun, daemon=True).start()
    return jsonify({"status": "triggered", "job": "enhance_rerun"})


@app.route("/api/trigger/clustering", methods=["POST"])
def trigger_clustering():
    threading.Thread(target=_run_clustering_job, daemon=True).start()
    return jsonify({"status": "triggered"})


def _run_clustering_job():
    from backend.ai.knowledge_clustering import run_clustering
    run_clustering()


# ── Trend Radar (L3a) ─────────────────────────────────────────────

@app.route("/api/trend-radar", methods=["GET"])
def get_latest_trend():
    scope = request.args.get("scope", "weekly")
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM trend_reports WHERE period_type = ? ORDER BY week_start DESC LIMIT 1",
        (scope,),
    ).fetchone()
    if not row:
        return jsonify({"report": None})
    return jsonify({"report": dict(row)})


@app.route("/api/trend-radar/<week>", methods=["GET"])
def get_trend_by_week(week: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM trend_reports WHERE week_start = ?", (week,)).fetchone()
    if not row:
        return jsonify({"report": None})
    return jsonify({"report": dict(row)})


@app.route("/api/trend-radars", methods=["GET"])
def list_trend_weeks():
    """Available trend report periods, split by type (history browsers)."""
    conn = get_conn()
    weeks = [r[0] for r in conn.execute(
        "SELECT week_start FROM trend_reports WHERE period_type = 'weekly' ORDER BY week_start DESC")]
    months = [r[0] for r in conn.execute(
        "SELECT week_start FROM trend_reports WHERE period_type = 'monthly' ORDER BY week_start DESC")]
    return jsonify({"weeks": weeks, "months": months})


@app.route("/api/trigger/trend", methods=["POST"])
def trigger_trend():
    scope = (request.get_json(silent=True) or {}).get("scope", "weekly")
    if scope not in ("weekly", "monthly"):
        scope = "weekly"

    def _run_trend():
        from backend.jobs import _set_job_status
        _set_job_status("trend", "running")
        try:
            from backend.ai.trend_analyzer import generate_trend_report_period
            result = generate_trend_report_period(scope)
            if result:
                _set_job_status("trend", "done", f"{'周' if scope == 'weekly' else '月'}报 {result['week_start']}: {result['paper_count']} 篇论文分析完成")
            else:
                _set_job_status("trend", "done", f"本期({'周' if scope == 'weekly' else '月'})无论文入库，未生成报告")
        except Exception as e:
            logging.getLogger(__name__).error(f"趋势报告生成失败: {e}", exc_info=True)
            _set_job_status("trend", "error", str(e)[:120])
    threading.Thread(target=_run_trend, daemon=True).start()
    return jsonify({"status": "triggered", "scope": scope})


# ── Logs ───────────────────────────────────────────────────────────

@app.route("/api/logs", methods=["GET"])
def get_logs():
    n = min(500, max(1, int(request.args.get("lines", 100))))
    log_path = os.path.join(_LOG_DIR, "arxivsci.log")
    if not os.path.exists(log_path):
        return jsonify({"logs": []})
    with open(log_path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()[-n:]
    return jsonify({"logs": [l.rstrip("\n") for l in lines]})


# ── Idea Check (L3b) ───────────────────────────────────────────────

@app.route("/api/idea-check", methods=["POST"])
def idea_check():
    data = request.get_json() or {}
    idea = data.get("idea", "").strip()
    if not idea:
        return jsonify({"error": "idea is required"}), 400
    from backend.ai.idea_checker import check_idea
    result = check_idea(idea)
    if result is None:
        return jsonify({"error": "analysis failed"}), 500
    return jsonify({"analysis": result})


# ── Category Recommendation ────────────────────────────────────────

ARXIV_CATEGORY_MAP = {
    "cs.AI": "Artificial Intelligence", "cs.AR": "Hardware Architecture",
    "cs.CC": "Computational Complexity", "cs.CE": "Computational Engineering",
    "cs.CG": "Computational Geometry", "cs.CL": "Computation and Language",
    "cs.CR": "Cryptography and Security", "cs.CV": "Computer Vision",
    "cs.CY": "Computers and Society", "cs.DB": "Databases",
    "cs.DC": "Distributed Computing", "cs.DL": "Digital Libraries",
    "cs.DM": "Discrete Mathematics", "cs.DS": "Data Structures and Algorithms",
    "cs.ET": "Emerging Technologies", "cs.FL": "Formal Languages",
    "cs.GL": "General Literature", "cs.GR": "Graphics",
    "cs.GT": "Computer Science and Game Theory", "cs.HC": "Human-Computer Interaction",
    "cs.IR": "Information Retrieval", "cs.IT": "Information Theory",
    "cs.LG": "Machine Learning", "cs.LO": "Logic in Computer Science",
    "cs.MA": "Multiagent Systems", "cs.MM": "Multimedia",
    "cs.MS": "Mathematical Software", "cs.NA": "Numerical Analysis",
    "cs.NE": "Neural and Evolutionary Computing", "cs.NI": "Networking and Internet Architecture",
    "cs.OH": "Other Computer Science", "cs.OS": "Operating Systems",
    "cs.PF": "Performance", "cs.PL": "Programming Languages",
    "cs.RO": "Robotics", "cs.SC": "Symbolic Computation",
    "cs.SD": "Sound", "cs.SE": "Software Engineering",
    "cs.SI": "Social and Information Networks", "cs.SY": "Systems and Control",
    "astro-ph.CO": "Cosmology", "astro-ph.EP": "Earth and Planetary Astrophysics",
    "astro-ph.GA": "Astrophysics of Galaxies", "astro-ph.HE": "High Energy Astrophysical Phenomena",
    "astro-ph.IM": "Astrophysics Instrumentation", "astro-ph.SR": "Solar and Stellar Astrophysics",
    "cond-mat.dis-nn": "Disordered Systems and Neural Networks",
    "cond-mat.mes-hall": "Mesoscale and Nanoscale Physics",
    "cond-mat.mtrl-sci": "Materials Science", "cond-mat.other": "Other Condensed Matter",
    "cond-mat.quant-gas": "Quantum Gases", "cond-mat.soft": "Soft Condensed Matter",
    "cond-mat.stat-mech": "Statistical Mechanics", "cond-mat.str-el": "Strongly Correlated Electrons",
    "cond-mat.supr-con": "Superconductivity",
    "gr-qc": "General Relativity and Quantum Cosmology",
    "hep-ex": "High Energy Physics - Experiment", "hep-lat": "High Energy Physics - Lattice",
    "hep-ph": "High Energy Physics - Phenomenology", "hep-th": "High Energy Physics - Theory",
    "math-ph": "Mathematical Physics",
    "nlin.AO": "Adaptation and Self-Organizing Systems", "nlin.CD": "Cellular Automata",
    "nlin.CG": "Chaotic Dynamics", "nlin.PS": "Pattern Formation and Solitons",
    "nlin.SI": "Exactly Solvable and Integrable Systems",
    "nucl-ex": "Nuclear Experiment", "nucl-th": "Nuclear Theory",
    "physics.acc-ph": "Accelerator Physics", "physics.ao-ph": "Atmospheric and Oceanic Physics",
    "physics.app-ph": "Applied Physics", "physics.atm-clus": "Atomic and Molecular Clusters",
    "physics.atom-ph": "Atomic Physics", "physics.bio-ph": "Biological Physics",
    "physics.chem-ph": "Chemical Physics", "physics.class-ph": "Classical Physics",
    "physics.comp-ph": "Computational Physics", "physics.data-an": "Data Analysis Statistics and Probability",
    "physics.flu-dyn": "Fluid Dynamics", "physics.gen-ph": "General Physics",
    "physics.geo-ph": "Geophysics", "physics.hist-ph": "History and Philosophy of Physics",
    "physics.ins-det": "Instrumentation and Detectors", "physics.med-ph": "Medical Physics",
    "physics.optics": "Optics", "physics.soc-ph": "Physics and Society",
    "physics.ed-ph": "Physics Education", "physics.plasm-ph": "Plasma Physics",
    "physics.pop-ph": "Popular Physics", "physics.space-ph": "Space Physics",
    "quant-ph": "Quantum Physics",
    "math.AG": "Algebraic Geometry", "math.AT": "Algebraic Topology",
    "math.AP": "Analysis of PDEs", "math.CT": "Category Theory",
    "math.CA": "Classical Analysis and ODEs", "math.CO": "Combinatorics",
    "math.AC": "Commutative Algebra", "math.CV": "Complex Variables",
    "math.DG": "Differential Geometry", "math.DS": "Dynamical Systems",
    "math.FA": "Functional Analysis", "math.GM": "General Mathematics",
    "math.GN": "General Topology", "math.GT": "Geometric Topology",
    "math.GR": "Group Theory", "math.HO": "History and Overview",
    "math.IT": "Information Theory", "math.KT": "K-Theory and Homology",
    "math.LO": "Logic", "math.MP": "Mathematical Physics",
    "math.MG": "Metric Geometry", "math.NT": "Number Theory",
    "math.NA": "Numerical Analysis", "math.OA": "Operator Algebras",
    "math.OC": "Optimization and Control", "math.PR": "Probability",
    "math.QA": "Quantum Algebra", "math.RT": "Representation Theory",
    "math.RA": "Rings and Algebras", "math.SP": "Spectral Theory",
    "math.ST": "Statistics Theory", "math.SG": "Symplectic Geometry",
    "q-bio.BM": "Biomolecules", "q-bio.CB": "Cell Behavior",
    "q-bio.GN": "Genomics", "q-bio.MN": "Molecular Networks",
    "q-bio.NC": "Neurons and Cognition", "q-bio.OT": "Other Quantitative Biology",
    "q-bio.PE": "Populations and Evolution", "q-bio.QM": "Quantitative Methods",
    "q-bio.SC": "Subcellular Processes", "q-bio.TO": "Tissues and Organs",
    "q-fin.CP": "Computational Finance", "q-fin.EC": "Economics",
    "q-fin.GN": "General Finance", "q-fin.MF": "Mathematical Finance",
    "q-fin.PM": "Portfolio Management", "q-fin.PR": "Pricing of Securities",
    "q-fin.RM": "Risk Management", "q-fin.ST": "Statistical Finance",
    "q-fin.TR": "Trading and Market Microstructure",
    "stat.AP": "Applications", "stat.CO": "Computation",
    "stat.ML": "Machine Learning", "stat.ME": "Methodology",
    "stat.OT": "Other Statistics", "stat.TH": "Theory",
    "eess.AS": "Audio and Speech Processing", "eess.IV": "Image and Video Processing",
    "eess.SP": "Signal Processing", "eess.SY": "Systems and Control",
    "econ.EM": "Econometrics", "econ.GN": "General Economics",
    "econ.TH": "Theoretical Economics",
}

@app.route("/api/recommend-categories", methods=["POST"])
def recommend_categories():
    """Use LLM to recommend arXiv categories based on research direction."""
    data = request.get_json() or {}
    direction = data.get("direction", "").strip()
    keywords = data.get("keywords", [])
    if not direction and not keywords:
        return jsonify({"error": "direction or keywords required"}), 400

    from pydantic import BaseModel, Field
    import os
    from backend.ai.llm import build_chat, task_model

    class CategoryRecommendation(BaseModel):
        primary: list[str] = Field(description="5-10 most relevant arXiv category codes (e.g. cs.CV, cs.LG)")
        secondary: list[str] = Field(description="3-5 tangentially relevant category codes")

    cat_list = "\n".join(f"- {code}: {name}" for code, name in ARXIV_CATEGORY_MAP.items())

    prompt = f"""Given a researcher's direction and keywords, select the most relevant arXiv categories. Return your answer as json with "primary" and "secondary" fields.

Research Direction: {direction}
Keywords: {', '.join(keywords) if keywords else 'N/A'}

Available arXiv categories:
{cat_list}

Select categories that would contain papers relevant to this researcher."""

    try:
        model_name = task_model("keyword")
        llm = build_chat(model_name, thinking=False, priority=True).with_structured_output(CategoryRecommendation, method="json_mode")
        from langchain_core.prompts import ChatPromptTemplate
        chain = ChatPromptTemplate.from_template(prompt) | llm
        try:
            result = chain.invoke({})
            primary = result.primary if isinstance(result.primary, list) else [result.primary]
            secondary = result.secondary if isinstance(result.secondary, list) else [result.secondary]
        except Exception as parse_err:
            # LLM sometimes returns strings instead of lists; extract manually
            import json, re
            err_str = str(parse_err)
            json_match = re.search(r'\{.*\}', err_str)
            if json_match:
                raw = json.loads(json_match.group())
                primary = raw.get("primary", []) if isinstance(raw.get("primary"), list) else [raw.get("primary", "")] if raw.get("primary") else []
                secondary = raw.get("secondary", []) if isinstance(raw.get("secondary"), list) else [raw.get("secondary", "")] if raw.get("secondary") else []
            else:
                primary, secondary = [], []
        all_codes = set(ARXIV_CATEGORY_MAP.keys())
        primary = [c for c in primary if c in all_codes]
        secondary = [c for c in secondary if c in all_codes]
        return jsonify({"primary": primary, "secondary": secondary})
    except Exception as e:
        logging.getLogger(__name__).error(f"分类推荐失败: {e}")
        return jsonify({"error": str(e)}), 500


def _deduplicate_topics(topics: list[str]) -> list[str]:
    """Use LLM to semantically deduplicate a topic list, keeping the most general phrasing.

    中英文同义/近义/混合表述视为重复（实测同一论文提取两次会得到
    '可执行不安全机会'与'executable unsafe opportunity'两种写法），
    归并为简体中文规范表述。容错 markdown 围栏与附带文字。"""
    if len(topics) <= 3:
        return topics
    try:
        from backend.ai.llm import build_chat, task_model
        llm = build_chat(
            task_model("topic"),
            thinking=False, temperature=0.1,
        )
        resp = llm.invoke(
            "Merge semantically duplicate or near-duplicate research topics into one entry: "
            "Chinese/English/mixed phrasings of the same concept are duplicates "
            "(e.g. '间接提示注入取证' ≡ 'indirect prompt injection forensics' ≡ '间接 prompt injection 取证'). "
            "Keep the concise Simplified-Chinese phrasing as canonical (standard technical terms stay in English). "
            "Do NOT invent new topics. Return ONLY a JSON array of strings, no explanation.\n\n"
            + json.dumps(topics, ensure_ascii=False)
        )
        content = (resp.content or "").strip()
        m = re.search(r'\[.*\]', content, re.DOTALL)
        if m:
            content = m.group()
        merged = json.loads(content)
        if isinstance(merged, list):
            # 防呆护栏：LLM 偶发返回空/畸缩列表（实测把 45 条 liked 清零），
            # 空结果或缩到不足 1/3 视为失败，保留原列表
            if not merged or len(merged) < max(1, len(topics) // 3):
                logging.getLogger(__name__).warning(
                    f"语义去重结果异常（{len(topics)}→{len(merged)}），保留原列表"
                )
                return topics
            return [t.strip() for t in merged if isinstance(t, str) and t.strip()] or topics
    except Exception as e:
        logging.getLogger(__name__).warning(f"语义去重失败: {e}")
    return topics


_profile_lock = threading.Lock()


def _academicize_note(note: str, rating: str) -> str:
    """将用户口语化评语改写为规范学术表述（保留原意与全部细节）。

    原始评语保留在 feedback 表供 UI 显示；画像 feedback_notes 存学术化
    版本供评分 prompt 使用——规范表述更利于评分模型解析与遵循。
    失败时退回原文（不阻塞反馈闭环）。"""
    try:
        from backend.ai.llm import build_chat, task_model
        llm = build_chat(task_model("topic"), thinking=False, temperature=0.2)
        resp = llm.invoke(
            "将下面的用户论文评语改写为规范的学术表述。要求：保留原始含义、"
            "倾向（认可/否定）与全部具体细节（方法名/机构/代码有无等）；"
            "1-2 句简体中文，标准术语保留英文；不添加评语中不存在的信息；"
            "只返回改写后的文本，不要任何解释或引号。\n\n"
            f"背景：用户对该论文持{'认可' if rating == 'like' else '否定'}态度。\n评语：{note[:200]}"
        )
        out = (resp.content or "").strip().strip('"“”').split("\n")[0][:200]
        if out:
            return out
    except Exception as e:
        logging.getLogger(__name__).warning(f"评语学术化失败，使用原文: {e}")
    return note


def _remove_paper_note(paper_id: str) -> None:
    """取消投票时移除该论文在 feedback_notes 中的评语条目（note_index 反查）。"""
    with _profile_lock:
        try:
            profile = json.loads(Path(_PROFILE_PATH).read_text(encoding="utf-8"))
        except Exception:
            return
        idx = profile.get("note_index", {})
        old = idx.pop(paper_id, None)
        if old:
            profile["feedback_notes"] = [n for n in profile.get("feedback_notes", []) if n != old]
            profile["note_index"] = idx
            _write_profile_atomic(profile)


def _update_profile_from_feedback(paper_id: str, rating: str):
    """Extract topics from a liked/disliked paper and update research_profile.json.

    Uses LLM to extract 5-7 topic phrases from the paper's AI analysis,
    then appends them to liked_topics or disliked_topics in the profile.
    After appending, runs LLM semantic dedup on the full list.
    Keeps the most recent 100 entries per list. Serialized by _profile_lock —
    concurrent feedback threads must not read-modify-write over each other.
    """
    if rating not in ("like", "dislike"):
        return
    with _profile_lock:
        conn = get_conn()
        row = conn.execute(
            "SELECT method, motivation FROM ai_results WHERE paper_id = ?", (paper_id,)
        ).fetchone()
        if not row or (not row["method"] and not row["motivation"]):
            return

        # 用户滑杆分值 + 评语一并提供：精细反馈参与画像提取
        fb = conn.execute(
            "SELECT relevance, novelty, note FROM feedback WHERE paper_id = ?", (paper_id,)
        ).fetchone()
        score_hint = ""
        if fb and (fb["relevance"] or fb["novelty"]):
            score_hint = f"\nUser scores (1-5): relevance={fb['relevance'] or '-'}, novelty={fb['novelty'] or '-'}."
        note = (fb["note"] if fb and fb["note"] else "").strip()
        note_hint = f"\nUser comment (highest-priority signal, extract topics it emphasizes): {note}" if note else ""

        method = row["method"] or ""
        motivation = row["motivation"] or ""
        if not method.strip() and not motivation.strip():
            return

        # 评语原文进入 profile.feedback_notes（最近20条），直通 AI 评分提示词。
        # note_index 记录 paper→当前评语：改评语/换投票时替换旧条目而非堆积
        if note:
            try:
                profile = json.loads(Path(_PROFILE_PATH).read_text(encoding="utf-8"))
            except Exception:
                profile = {}
            notes = profile.get("feedback_notes", [])
            idx = profile.get("note_index", {})
            old = idx.get(paper_id)
            if old and old in notes:
                notes.remove(old)
            # 学术化改写：原文留 UI，画像存规范版本（利于评分模型解析）
            normalized = _academicize_note(note, rating)
            tagged = f"[{rating}] {normalized}"
            if tagged not in notes:
                notes.append(tagged)
            idx[paper_id] = tagged
            profile["note_index"] = idx
            profile["feedback_notes"] = notes[-20:]
            _write_profile_atomic(profile)
            logging.getLogger(__name__).info(
                f"评语入画像: [{rating}] 原文「{note[:30]}{'…' if len(note) > 30 else ''}」→ 学术化「{normalized[:50]}{'…' if len(normalized) > 50 else ''}」 "
                f"feedback_notes({len(profile['feedback_notes'])}条){'（替换旧条目）' if old else ''}"
            )

        try:
            from backend.ai.llm import build_chat, task_model
            llm = build_chat(task_model("topic"), thinking=False, temperature=0.2)
            resp = llm.invoke(
                f"Extract 5-7 short topic phrases (2-5 words each) from this paper's method and motivation. "
                f"用简体中文输出主题（标准技术术语保留英文），与用户画像语言一致。"
                f"Return ONLY a JSON array of strings, no explanation.\n\n"
                f"Method: {method[:500]}\nMotivation: {motivation[:300]}{score_hint}{note_hint}"
            )
            topics = json.loads(resp.content)
            if not isinstance(topics, list):
                return
            topics = [t.strip() for t in topics if isinstance(t, str) and t.strip()][:7]
        except Exception as e:
            logging.getLogger(__name__).warning(f"主题提取失败 {paper_id}: {e}")
            return

        if not topics:
            return

        try:
            profile = json.loads(Path(_PROFILE_PATH).read_text(encoding="utf-8"))
        except Exception:
            return

        key = "liked_topics" if rating == "like" else "disliked_topics"
        current = profile.get(key, [])

        existing_lower = {t.lower() for t in current}
        new_added = []
        for t in topics:
            if t.lower() not in existing_lower:
                current.append(t)
                existing_lower.add(t.lower())
                new_added.append(t)

        if new_added and len(current) > 5:
            current = _deduplicate_topics(current)

        profile[key] = current[-100:]
        _write_profile_atomic(profile)
        # 立即失效缓存的 AI 链画像，否则反馈闭环要等 daemon 重启才生效
        reset_ai_chain()
        logging.getLogger(__name__).info(f"Profile updated: {key} += {new_added} (after dedup: {len(profile[key])} topics)")


# ── Author Search ─────────────────────────────────────────────────

@app.route("/api/author/search", methods=["GET"])
def search_author_api():
    query = request.args.get("query", "").strip()
    if not query or len(query) < 2:
        return jsonify({"authors": []})
    from backend.crawler.author_crawler import search_authors, resolve_orcid_to_author
    if query.startswith("0000-") or "orcid.org" in query:
        author = resolve_orcid_to_author(query)
        return jsonify({"authors": [author] if author else []})
    results = search_authors(query, limit=10)
    return jsonify({"authors": results})


# ── BibTeX Export ─────────────────────────────────────────────────

def _bibtex_for(paper: dict) -> str:
    authors_list = paper.get("authors") or []
    authors = " and ".join(authors_list)
    year = (paper.get("published_date") or "")[:4]
    # authorYear 风格引用键（LaTeX 惯例）：第一作者姓氏+年份+标题首个实义词
    first_author = (authors_list[0].split()[-1] if authors_list else "anon").lower()
    title_words = [w for w in (paper.get("title") or "").split() if w]
    content_words = [w for w in title_words if w.lower() not in ("a", "an", "the")]
    first_word = "".join(ch for ch in (content_words[0] if content_words else "paper") if ch.isalpha()).lower()
    key = "".join(ch for ch in f"{first_author}{year}{first_word}" if ch.isalnum()) or "unknown"
    title = paper.get("title") or ""
    venue = paper.get("venue") or paper.get("journal_title") or ""
    doi = paper.get("doi") or ""
    lines = [f"@article{{{key},"]
    if title: lines.append(f"  title = {{{title}}},")
    if authors: lines.append(f"  author = {{{authors}}},")
    if year: lines.append(f"  year = {{{year}}},")
    if venue: lines.append(f"  journal = {{{venue}}},")
    if doi: lines.append(f"  doi = {{{doi}}},")
    url = paper.get("url") or ""
    if url: lines.append(f"  url = {{{url}}},")
    lines.append("}")
    return "\n".join(lines)


@app.route("/api/export/bibtex", methods=["POST"])
def export_bibtex():
    data = request.get_json()
    ids = data.get("ids", []) if data else []
    if not ids:
        return jsonify({"error": "no ids provided"}), 400
    entries = []
    for pid in ids:
        paper = find_paper_by_id(pid)
        if paper:
            entries.append(_bibtex_for(paper))
    if not entries:
        return jsonify({"error": "no papers found"}), 404
    return "\n\n".join(entries), 200, {"Content-Type": "application/x-bibtex"}


# ── Paper deletion ───────────────────────────────────────────────

# schema 无外键级联——删除必须连带子表，否则留孤儿行（2026-09-19 审查实锤）
_PAPER_CHILD_TABLES = ("ai_results", "feedback", "knowledge_cards", "fulltext_analysis")


def _delete_papers_with_children(conn, ids: list) -> int:
    if not ids:
        return 0
    ph = ",".join("?" * len(ids))
    for table in _PAPER_CHILD_TABLES:
        conn.execute(f"DELETE FROM {table} WHERE paper_id IN ({ph})", ids)
    cur = conn.execute(f"DELETE FROM papers WHERE id IN ({ph})", ids)
    return cur.rowcount


@app.route("/api/paper/<path:paper_id>", methods=["DELETE"])
def delete_paper(paper_id: str):
    """Delete a single paper and all related data. Records as ignored."""
    conn = get_conn()
    deleted = _delete_papers_with_children(conn, [paper_id])
    if deleted:
        conn.execute("INSERT OR REPLACE INTO ignored_papers (paper_id, reason) VALUES (?, ?)",
                     (paper_id, "user_deleted"))
        conn.commit()
        logging.getLogger(__name__).info(f"已删除论文 {paper_id}（含子表）")
        return jsonify({"deleted": paper_id})
    return jsonify({"error": "not found"}), 404


@app.route("/api/papers/before/<date_str>", methods=["DELETE"])
def delete_papers_before_date(date_str: str):
    """Delete all papers published before the given date (YYYY-MM-DD). Records as ignored."""
    conn = get_conn()
    ids = [r[0] for r in conn.execute("SELECT id FROM papers WHERE published_date < ?", (date_str,)).fetchall()]
    if ids:
        _delete_papers_with_children(conn, ids)
        conn.executemany("INSERT OR REPLACE INTO ignored_papers (paper_id, reason) VALUES (?, ?)",
                         [(pid, "purge_before_date") for pid in ids])
        conn.commit()
    logging.getLogger(__name__).info(f"已删除 {len(ids)} 篇 {date_str} 之前的论文")
    return jsonify({"deleted_count": len(ids), "before": date_str})


@app.route("/api/papers/purge", methods=["POST"])
def purge_papers():
    """Delete papers matching criteria: skip-rated, older-than-N-days, or specific recommendation."""
    data = request.get_json() or {}
    conn = get_conn()
    count = 0
    ignored_ids = []

    if data.get("skip_rated"):
        # 审计 P1：用户点赞/收藏过的论文绝不随 purge 物理删除（反馈历史不可逆）
        rows = conn.execute(
            """SELECT p.id FROM papers p JOIN ai_results a ON p.id = a.paper_id
               WHERE a.recommendation = 'ignore'
                 AND NOT EXISTS (SELECT 1 FROM feedback f WHERE f.paper_id = p.id
                                 AND (f.rating = 'like' OR f.bookmarked = 1))"""
        ).fetchall()
        ids = [r[0] for r in rows]
        if ids:
            _delete_papers_with_children(conn, ids)
            ignored_ids.extend(ids)
            count += len(ids)

    if data.get("older_than_days"):
        cutoff = f"datetime('now', '-{int(data['older_than_days'])} days')"
        rows = conn.execute(f"SELECT id FROM papers WHERE published_date < date({cutoff})").fetchall()
        ids = [r[0] for r in rows]
        if ids:
            _delete_papers_with_children(conn, ids)
            ignored_ids.extend(ids)
            count += len(ids)

    if ignored_ids:
        conn.executemany("INSERT OR REPLACE INTO ignored_papers (paper_id, reason) VALUES (?, ?)",
                         [(pid, "purge") for pid in ignored_ids])
        conn.commit()

    conn.commit()
    logging.getLogger(__name__).info(f"Purged {count} papers")
    return jsonify({"purged": count})


# ── Ignored papers audit ─────────────────────────────────────────

@app.route("/api/ignored", methods=["GET"])
def get_ignored_papers():
    """View papers that were filtered out (quick_filter_reject or AI ignore)."""
    conn = get_conn()
    reason = request.args.get("reason", "")
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(200, max(1, int(request.args.get("per_page", 50))))

    if reason:
        if reason == 'ai_ignore':
            where = "WHERE reason NOT IN ('quick_filter_reject', 'user_deleted', 'purge', 'purge_before_date')"
            total = conn.execute(f"SELECT COUNT(*) FROM ignored_papers {where}").fetchone()[0]
            rows = conn.execute(
                f"SELECT paper_id, reason, reason_detail, ignored_at FROM ignored_papers {where} ORDER BY ignored_at DESC LIMIT ? OFFSET ?",
                (per_page, (page - 1) * per_page),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) FROM ignored_papers WHERE reason = ?", (reason,)).fetchone()[0]
            rows = conn.execute(
                "SELECT paper_id, reason, reason_detail, ignored_at FROM ignored_papers WHERE reason = ? ORDER BY ignored_at DESC LIMIT ? OFFSET ?",
                (reason, per_page, (page - 1) * per_page),
            ).fetchall()
    else:
        total = conn.execute("SELECT COUNT(*) FROM ignored_papers").fetchone()[0]
        rows = conn.execute(
            "SELECT paper_id, reason, reason_detail, ignored_at FROM ignored_papers ORDER BY ignored_at DESC LIMIT ? OFFSET ?",
            (per_page, (page - 1) * per_page),
        ).fetchall()

    # Group by category for stats
    stats = conn.execute("""
        SELECT
            CASE
                WHEN reason = 'quick_filter_reject' THEN 'quick_filter_reject'
                WHEN reason IN ('user_deleted', 'purge', 'purge_before_date') THEN reason
                ELSE 'ai_ignore'
            END as category,
            COUNT(*) as cnt
        FROM ignored_papers GROUP BY category ORDER BY cnt DESC
    """).fetchall()

    return jsonify({
        "ignored": [{"paper_id": r[0], "reason": r[1], "reason_detail": r[2], "ignored_at": r[3]} for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "stats": [{"reason": s[0], "count": s[1]} for s in stats],
    })


@app.route("/api/ignored/stats", methods=["GET"])
def get_ignored_stats():
    """Summary stats of ignored papers."""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM ignored_papers").fetchone()[0]
    stats = conn.execute("""
        SELECT
            CASE
                WHEN reason = 'quick_filter_reject' THEN 'quick_filter_reject'
                WHEN reason IN ('user_deleted', 'purge', 'purge_before_date') THEN reason
                ELSE 'ai_ignore'
            END as category,
            COUNT(*) as cnt
        FROM ignored_papers GROUP BY category ORDER BY cnt DESC
    """).fetchall()
    return jsonify({
        "total_ignored": total,
        "by_reason": [{"reason": s[0], "count": s[1]} for s in stats],
    })
