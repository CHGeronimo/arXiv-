"""Cluster papers by extracted method keywords using topic-based grouping.

Strategy: identify high-frequency keywords as cluster seeds, then assign
each paper to its best-matching seed topic. Papers with no strong match
form a "misc" cluster.
"""

import json
import logging
from collections import Counter

from db import get_conn

logger = logging.getLogger(__name__)

MIN_CLUSTER_SIZE = 3
SEED_MIN_FREQ = 2
MAX_CLUSTERS = 30


def compute_clusters() -> list[dict]:
    """Build clusters from knowledge_cards keywords.

    Two-phase approach:
    1. Identify high-frequency keywords as cluster seeds (top-N by frequency).
    2. Assign each paper to its best-matching seed based on keyword overlap,
       preferring the most specific (lowest-frequency) seed when ties exist.
    """
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

    # Select seed keywords: top-N by frequency, minimum SEED_MIN_FREQ occurrences
    candidates = [(kw, cnt) for kw, cnt in kw_counter.items() if cnt >= SEED_MIN_FREQ]
    candidates.sort(key=lambda x: -x[1])
    # Skip overly broad top-2 seeds that swallow everything
    seeds = [kw for kw, _ in candidates[2:2 + MAX_CLUSTERS]]
    seed_set = set(seeds)

    # Assign each paper to its best-matching seed
    cluster_map: dict[str, list[str]] = {}
    assigned: set[str] = set()
    misc: list[str] = []

    for pid, kws in paper_kw.items():
        best_seed = None
        best_overlap = 0
        kw_set = set(kws)
        for seed in seeds:
            overlap = len(kw_set & {seed})
            if overlap > best_overlap:
                best_overlap = overlap
                best_seed = seed
        if best_seed and best_overlap > 0:
            cluster_map.setdefault(best_seed, []).append(pid)
            assigned.add(pid)
        else:
            misc.append(pid)

    # Build final clusters
    clusters: list[dict] = []
    for seed, pids in cluster_map.items():
        if len(pids) < MIN_CLUSTER_SIZE:
            continue
        all_kw: set[str] = set()
        for pid in pids:
            all_kw.update(paper_kw.get(pid, []))
        top_kw = sorted(all_kw, key=lambda k: -kw_counter[k])[:5]
        clusters.append({
            "cluster_name": ", ".join(top_kw[:3]),
            "method_keywords": json.dumps(top_kw, ensure_ascii=False),
            "paper_ids": json.dumps(pids, ensure_ascii=False),
            "problem_domains": "[]",
        })

    # Sort by size descending
    clusters.sort(key=lambda c: -len(json.loads(c["paper_ids"])))

    # Add misc cluster
    if misc and len(misc) >= MIN_CLUSTER_SIZE:
        misc_kw: set[str] = set()
        for pid in misc:
            misc_kw.update(paper_kw.get(pid, []))
        top_kw = sorted(misc_kw, key=lambda k: -kw_counter[k])[:5]
        clusters.append({
            "cluster_name": "其他 · " + ", ".join(top_kw[:2]),
            "method_keywords": json.dumps(top_kw, ensure_ascii=False),
            "paper_ids": json.dumps(misc, ensure_ascii=False),
            "problem_domains": "[]",
        })

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