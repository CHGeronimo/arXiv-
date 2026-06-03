"""Cluster papers by extracted method keywords."""

import json
import logging

from db import get_conn, queue_write

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.3


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def compute_clusters() -> list[dict]:
    """Build clusters from knowledge_cards keywords. Returns list of cluster dicts."""
    conn = get_conn()
    rows = conn.execute("SELECT paper_id, keywords FROM knowledge_cards").fetchall()

    paper_kw: dict[str, set[str]] = {}
    for r in rows:
        kws = json.loads(r["keywords"]) if isinstance(r["keywords"], str) else (r["keywords"] or [])
        paper_kw[r["paper_id"]] = set(kws)

    if not paper_kw:
        return []

    papers = list(paper_kw.keys())
    assigned: set[str] = set()
    clusters: list[dict] = []

    for p in papers:
        if p in assigned:
            continue
        cluster_papers = [p]
        assigned.add(p)
        for q in papers:
            if q in assigned:
                continue
            if _jaccard(paper_kw[p], paper_kw[q]) >= SIMILARITY_THRESHOLD:
                cluster_papers.append(q)
                assigned.add(q)
        all_kw: set[str] = set()
        for cp in cluster_papers:
            all_kw |= paper_kw.get(cp, set())
        clusters.append({
            "cluster_name": ", ".join(sorted(all_kw)[:3]),
            "method_keywords": json.dumps(sorted(all_kw), ensure_ascii=False),
            "paper_ids": json.dumps(cluster_papers, ensure_ascii=False),
            "problem_domains": "[]",
        })

    return clusters


def save_clusters(clusters: list[dict]) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM knowledge_clusters")
    for c in clusters:
        queue_write(
            "INSERT INTO knowledge_clusters (cluster_name, method_keywords, paper_ids, problem_domains) VALUES (?, ?, ?, ?)",
            (c["cluster_name"], c["method_keywords"], c["paper_ids"], c["problem_domains"]),
        )


def run_clustering() -> int:
    clusters = compute_clusters()
    save_clusters(clusters)
    logger.info(f"计算了 {len(clusters)} 个聚类")
    return len(clusters)
