"""Cluster papers using LLM-based semantic grouping.

Two-phase approach:
1. Extract high-level research themes from all paper keywords via LLM.
2. Assign each paper to its best-matching theme based on keyword overlap,
   allowing multi-cluster membership.
"""

import json
import logging
import os
from collections import Counter, defaultdict

from backend.db import get_conn

logger = logging.getLogger(__name__)

MIN_CLUSTER_SIZE = 3
MAX_CLUSTERS = 30


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


def _assign_papers_to_themes_llm(
    paper_kw: dict[str, list[str]],
    themes: list[str],
    kw_counter: Counter,
    batch_size: int = 200,
) -> dict[str, list[str]]:
    """Assign papers to themes using LLM for semantic matching."""
    try:
        from .llm import build_chat, task_model
        llm = build_chat(
            task_model("cluster"),
            thinking=False, temperature=0.05, timeout=120,
        )

        theme_list_str = json.dumps(themes, ensure_ascii=False)
        all_assignments: dict[str, list[str]] = {}
        pids = list(paper_kw.keys())

        for i in range(0, len(pids), batch_size):
            batch = pids[i:i + batch_size]
            paper_data = {pid: paper_kw[pid][:8] for pid in batch}  # limit keywords per paper
            prompt = (
                "You are a CS research taxonomy expert. Given a list of research themes and papers (with keywords), "
                "assign each paper to 1-2 most relevant themes. If no theme fits well, assign '其他'.\n\n"
                f"Themes: {theme_list_str}\n\n"
                f"Papers: {json.dumps(paper_data, ensure_ascii=False)}\n\n"
                "Return ONLY a JSON object mapping paper_id to an array of theme strings. No explanation."
            )
            resp = llm.invoke(prompt)
            content = resp.content.strip()
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                batch_result = json.loads(json_match.group())
                for pid in batch:
                    assigned = batch_result.get(pid, [])
                    if isinstance(assigned, list) and assigned:
                        # Validate themes exist
                        valid = [t for t in assigned if t in themes or t == "其他"]
                        all_assignments[pid] = valid if valid else ["其他"]
                    else:
                        all_assignments[pid] = ["其他"]
            else:
                for pid in batch:
                    all_assignments[pid] = ["其他"]

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

    # 问题域标注（单个 LLM 调用，失败保持空数组）
    domains = _label_problem_domains([c["cluster_name"] for c in clusters])
    for c in clusters:
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
    clusters = compute_clusters()
    save_clusters(clusters)
    logger.info(f"计算了 {len(clusters)} 个聚类")
    return len(clusters)
