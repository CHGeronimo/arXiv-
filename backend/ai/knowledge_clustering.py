"""Cluster papers using LLM-based semantic grouping.

Two-phase approach:
1. Extract high-level research themes from all paper keywords via LLM.
2. Assign each paper to its best-matching theme based on keyword overlap,
   allowing multi-cluster membership.
"""

import json
import logging
import os
import re
from collections import Counter, defaultdict
from difflib import get_close_matches

from backend.db import get_conn

logger = logging.getLogger(__name__)

MIN_CLUSTER_SIZE = 3
MAX_CLUSTERS = 30


def _progress(msg: str, done: int | None = None, total: int | None = None) -> None:
    """进度双通道：日志 + clustering 任务状态（⚡ 任务中心轮询）。"""
    logger.info(msg)
    try:
        from backend.jobs import _set_job_status
        prog = {"done": done, "total": total} if (done is not None and total) else None
        _set_job_status("clustering", "running", msg, progress=prog)
    except Exception:
        pass


def _norm_theme(s: str) -> str:
    """主题名归一化（大小写/空白/连字符/逗号），供精确匹配。"""
    return re.sub(r"[\s\-_,，、]+", "", s.lower())


def _extract_themes(all_keywords: list[str], kw_counter: Counter) -> list[str]:
    """Use LLM to identify high-level research themes from keywords."""
    # Get top keywords by frequency as input
    top_kws = kw_counter.most_common(120)
    kw_list = [kw for kw, _ in top_kws]

    try:
        from .llm import build_chat, task_model
        llm = build_chat(
            task_model("cluster"),
            thinking=False, temperature=0.1, timeout=60,
        )
        prompt = (
            "You are a CS research taxonomy expert. Given a list of research keywords extracted from papers, "
            "identify 15-25 high-level research themes that cover ALL areas represented. "
            "IMPORTANT: Themes must be DISTINCT — do NOT create themes that are subsets of others. "
            "For example, 'multi-agent RL' and 'game theory' are separate themes; "
            "'multi-agent RL' and 'MARL' are NOT separate. "
            "Each theme should be a short phrase (2-5 words). "
            "Include BOTH applied and theoretical themes. "
            "Return ONLY a JSON array of strings, no explanation.\n\n"
            + json.dumps(kw_list, ensure_ascii=False)
        )
        resp = llm.invoke(prompt)
        content = resp.content.strip()
        # Extract JSON from possible markdown wrapper
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            themes = json.loads(json_match.group())
        else:
            themes = json.loads(content)
        if isinstance(themes, list) and len(themes) >= 5:
            return [t.strip() for t in themes if isinstance(t, str) and t.strip()]
    except Exception as e:
        logger.warning(f"LLM theme extraction failed: {e}, falling back to frequency seeds")

    # Fallback: use top frequency keywords as seeds
    return [kw for kw, _ in kw_counter.most_common(MAX_CLUSTERS) if kw_counter[kw] >= 2]


def _resolve_theme(t: str, themes: list[str], norm_map: dict[str, str]) -> str | None:
    """LLM 返回的主题名 → 主题表里的规范名。

    2026-09-19 实锤：旧版只接受与主题表完全相等的字符串，LLM 轻微改写
    （大小写/冠词/标点）就被判无效 → 整篇掉进"其他"，87% 论文堆积。
    先归一化精确匹配，再 difflib 模糊救回（cutoff 0.75），仍不中才算真不匹配。
    """
    if not isinstance(t, str) or not t.strip():
        return None
    exact = norm_map.get(_norm_theme(t))
    if exact:
        return exact
    if t == "其他":
        return "其他"
    close = get_close_matches(t, themes, n=1, cutoff=0.75)
    return close[0] if close else None


def _assign_papers_to_themes_llm(
    paper_kw: dict[str, list[str]],
    themes: list[str],
    kw_counter: Counter,
    batch_size: int = 50,
) -> dict[str, list[str]]:
    """Assign papers to themes using LLM for semantic matching.

    防御性设计（2026-09-19 修复，此前 87% 论文掉进"其他"）：
    - 小批次（50 篇/批）避免长输出被截断导致整批 JSON 解析失败；
    - 单批解析失败只把该批送去关键词救援，不再整批判"其他"；
    - 主题名校验走归一化+模糊匹配，轻微改写可救回；
    - LLM 判"其他"或未返回的论文，再走一遍关键词宽匹配兜底。
    """
    try:
        from .llm import build_chat, task_model
        llm = build_chat(
            task_model("cluster"),
            thinking=False, temperature=0.05, timeout=120,
        )

        theme_list_str = json.dumps(themes, ensure_ascii=False)
        norm_map = {_norm_theme(t): t for t in themes}
        all_assignments: dict[str, list[str]] = {}
        rescue_pids: list[str] = []  # LLM 未给出有效主题的，走关键词救援
        pids = list(paper_kw.keys())
        batches = [pids[i:i + batch_size] for i in range(0, len(pids), batch_size)]

        def _paper_prompt(batch: list[str]) -> str:
            paper_data = {pid: paper_kw[pid][:8] for pid in batch}  # limit keywords per paper
            return (
                "You are a CS research taxonomy expert. Assign each paper to the 1-2 most relevant themes "
                "from the given theme list. Return each theme EXACTLY as written in the list "
                "(do not paraphrase, translate, abbreviate or merge themes).\n"
                "Use '其他' ONLY when a paper truly matches none of the themes — "
                "this should apply to fewer than 10% of papers.\n\n"
                f"Themes: {theme_list_str}\n\n"
                f"Papers: {json.dumps(paper_data, ensure_ascii=False)}\n\n"
                "Return ONLY a JSON object mapping paper_id to an array of theme strings. No explanation."
            )

        def _run_batch(idx_batch: tuple[int, list[str]]) -> tuple[list[str], dict]:
            """单批：调用 + 解析。异常/解析失败返回空 dict（该批走关键词救援）。"""
            idx, batch = idx_batch
            try:
                resp = llm.invoke(_paper_prompt(batch))
                content = resp.content.strip()
                m = re.search(r'\{.*\}', content, re.DOTALL)
                if m:
                    parsed = json.loads(m.group())
                    if isinstance(parsed, dict):
                        return batch, parsed
            except Exception as e:
                logger.warning(f"批次 {idx + 1} 调用失败（{len(batch)} 篇转关键词救援）: {e}")
            return batch, {}

        # 2 路并行（= LLM_MAX_CONCURRENT，全局速率限制仍在 build_chat 内生效）
        from concurrent.futures import ThreadPoolExecutor
        done = 0
        with ThreadPoolExecutor(max_workers=2) as ex:
            for batch, batch_result in ex.map(_run_batch, enumerate(batches)):
                done += 1
                for pid in batch:
                    assigned = batch_result.get(pid, [])
                    if not isinstance(assigned, list):
                        assigned = []
                    valid: list[str] = []
                    for t in assigned:
                        r = _resolve_theme(t, themes, norm_map)
                        if r and r not in valid:
                            valid.append(r)
                    if valid:
                        all_assignments[pid] = valid[:2]
                    else:
                        rescue_pids.append(pid)
                if done % 5 == 0 or done == len(batches):
                    ndone = min(done * batch_size, len(pids))
                    _progress(f"主题分配批次 {done}/{len(batches)}（{ndone}/{len(pids)} 篇）",
                              done=ndone, total=len(pids))

        # 救援通道：LLM 判"其他"/未返回的论文 → 关键词宽匹配（真不相关才会留在"其他"）
        if rescue_pids:
            logger.info(f"关键词救援 {len(rescue_pids)} 篇（LLM 未给出有效主题）")
            rescued = _assign_papers_to_themes_kw(
                {pid: paper_kw[pid] for pid in rescue_pids}, themes, kw_counter,
            )
            for pid, theme_list in rescued.items():
                all_assignments[pid] = theme_list

        other_n = sum(1 for v in all_assignments.values() if v == ["其他"])
        logger.info(f"主题分配完成：{len(all_assignments)} 篇，其中'其他' {other_n} 篇（{other_n * 100 // max(1, len(all_assignments))}%）")
        return all_assignments

    except Exception as e:
        logger.warning(f"LLM assignment failed: {e}, falling back to keyword matching")
        return _assign_papers_to_themes_kw(paper_kw, themes, kw_counter)


def _assign_papers_to_themes_kw(
    paper_kw: dict[str, list[str]],
    themes: list[str],
    kw_counter: Counter,
) -> dict[str, list[str]]:
    """Assign each paper to its best-matching theme based on keyword overlap.

    Specificity rule: if a paper matches both a broad theme (e.g. '强化学习')
    and a more specific one (e.g. '多智能体强化学习'), only keep the specific one.
    """
    theme_kw_map: dict[str, set[str]] = {}
    for theme in themes:
        terms = set(theme.lower().replace("-", " ").replace(",", " ").split())
        theme_kw_map[theme] = terms

    # Pre-compute theme specificity: longer/more-specific themes first
    theme_specificity: dict[str, int] = {}
    for i, t1 in enumerate(themes):
        # A theme is "broad" if another theme's name contains it as substring
        is_broad = any(
            t1.lower() != t2.lower() and t1.lower() in t2.lower()
            for t2 in themes
        )
        theme_specificity[t1] = 0 if is_broad else 1

    theme_assignments: dict[str, list[str]] = defaultdict(list)

    for pid, kws in paper_kw.items():
        scores: dict[str, int] = {}
        for theme in themes:
            score = 0
            for kw in kws:
                kw_lower = kw.lower()
                theme_lower = theme.lower()
                if kw_lower in theme_lower or theme_lower in kw_lower:
                    score += 2
                kw_terms = set(kw_lower.replace("-", " ").replace(",", " ").split())
                overlap = kw_terms & theme_kw_map[theme]
                if overlap:
                    score += len(overlap)
            scores[theme] = score

        # Rank by score (desc), then specificity (specific first)
        ranked = sorted(
            scores.items(),
            key=lambda x: (-x[1], -theme_specificity[x[0]]),
        )

        # Collect candidates with score > 0
        candidates = [(theme, score) for theme, score in ranked if score > 0]

        # Specificity filter: if a specific theme is selected, drop broad parents
        assigned = []
        for theme, score in candidates:
            if len(assigned) >= 2:
                break
            # Check if this theme is a broad parent of an already-assigned theme
            is_parent = any(
                theme.lower() != a.lower() and theme.lower() in a.lower()
                for a in assigned
            )
            if is_parent:
                continue
            assigned.append(theme)

        # If no match, try broader matching
        if not assigned and kws:
            for theme in themes:
                theme_lower = theme.lower()
                for kw in kws:
                    kw_lower = kw.lower()
                    kw_words = {w for w in kw_lower.split() if len(w) > 2}
                    theme_words = {w for w in theme_lower.split() if len(w) > 2}
                    if kw_words & theme_words:
                        assigned.append(theme)
                        break
                if len(assigned) >= 2:
                    break

        if not assigned:
            assigned = ["其他"]

        theme_assignments[pid] = assigned

    return dict(theme_assignments)


def _label_problem_domains(cluster_names: list[str]) -> dict[str, str]:
    """One cheap LLM call: label each cluster with its problem domain
    (e.g. 序贯决策/机制设计/感知估计). Returns {} on failure —
    problem_domains then stays empty, which the UI tolerates."""
    if not cluster_names:
        return {}
    try:
        from .llm import build_chat, task_model
        llm = build_chat(
            task_model("cluster"),
            thinking=False, temperature=0.1, timeout=60,
        )
        prompt = (
            "为每个研究主题标注其所属的问题域（研究问题所属的更粗粒度领域，"
            "如：序贯决策与控制、机制设计与激励、感知与状态估计、学习理论与泛化、"
            "系统与安全、应用落地等，6-12字）。"
            '返回 JSON 对象 {"主题": "问题域"}，不要解释。\n'
            + json.dumps(cluster_names, ensure_ascii=False)
        )
        resp = llm.invoke(prompt)
        import re
        m = re.search(r'\{.*\}', resp.content, re.DOTALL)
        if not m:
            return {}
        data = json.loads(m.group())
        return {str(k): str(v) for k, v in data.items() if isinstance(v, str)} if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"问题域标注失败（保持为空）: {e}")
        return {}


def compute_clusters() -> list[dict]:
    """Build clusters using LLM-based theme extraction + multi-label assignment."""
    conn = get_conn()
    rows = conn.execute("SELECT paper_id, keywords FROM knowledge_cards").fetchall()

    paper_kw: dict[str, list[str]] = {}
    kw_counter: Counter = Counter()
    for r in rows:
        kws = json.loads(r["keywords"]) if isinstance(r["keywords"], str) else (r["keywords"] or [])
        paper_kw[r["paper_id"]] = kws
        kw_counter.update(kws)

    if not paper_kw:
        return []

    # Phase 1: Extract themes
    themes = _extract_themes(list(kw_counter.keys()), kw_counter)
    themes = themes[:MAX_CLUSTERS]
    logger.info(f"Extracted {len(themes)} themes: {themes[:10]}...")

    # Phase 2: Assign papers (LLM-first, keyword fallback)
    assignments = _assign_papers_to_themes_llm(paper_kw, themes, kw_counter)

    # Build clusters from assignments
    cluster_papers: dict[str, list[str]] = defaultdict(list)
    for pid, theme_list in assignments.items():
        for theme in theme_list:
            cluster_papers[theme].append(pid)

    # Build final clusters
    clusters: list[dict] = []
    for theme, pids in cluster_papers.items():
        if len(pids) < MIN_CLUSTER_SIZE:
            continue
        all_kw: set[str] = set()
        for pid in pids:
            all_kw.update(paper_kw.get(pid, []))
        top_kw = sorted(all_kw, key=lambda k: -kw_counter[k])[:5]
        clusters.append({
            "cluster_name": theme,
            "method_keywords": json.dumps(top_kw, ensure_ascii=False),
            "paper_ids": json.dumps(pids, ensure_ascii=False),
            "problem_domains": "[]",
        })

    # Sort by size descending
    clusters.sort(key=lambda c: -len(json.loads(c["paper_ids"])))

    # 问题域标注（单个 LLM 调用，失败保持空数组；"其他"聚类直接标注不走 LLM）
    domains = _label_problem_domains([c["cluster_name"] for c in clusters if c["cluster_name"] != "其他"])
    for c in clusters:
        if c["cluster_name"] == "其他":
            c["problem_domains"] = json.dumps(["其他"], ensure_ascii=False)
            continue
        domain = domains.get(c["cluster_name"], "")
        c["problem_domains"] = json.dumps([domain] if domain else [], ensure_ascii=False)

    return clusters


def save_clusters(clusters: list[dict]) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM knowledge_clusters")
    for c in clusters:
        conn.execute(
            "INSERT INTO knowledge_clusters (cluster_name, method_keywords, paper_ids, problem_domains) VALUES (?, ?, ?, ?)",
            (c["cluster_name"], c["method_keywords"], c["paper_ids"], c["problem_domains"]),
        )
    conn.commit()


def run_clustering() -> int:
    try:
        clusters = compute_clusters()
        save_clusters(clusters)
    except Exception as e:
        logger.error(f"聚类失败: {e}", exc_info=True)
        try:
            from backend.jobs import _set_job_status
            _set_job_status("clustering", "error", str(e)[:160])
        except Exception:
            pass
        raise
    total = sum(len(json.loads(c["paper_ids"])) for c in clusters)
    other = next((len(json.loads(c["paper_ids"])) for c in clusters if c["cluster_name"] == "其他"), 0)
    msg = f"{len(clusters)} 个聚类 / {total} 篇（'其他' {other} 篇，{other * 100 // max(1, total)}%）"
    logger.info(f"计算了 {msg}")
    try:
        from backend.jobs import _set_job_status
        _set_job_status("clustering", "done", msg)
    except Exception:
        pass
    return len(clusters)
