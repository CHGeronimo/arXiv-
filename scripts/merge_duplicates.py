#!/usr/bin/env python3
"""合并跨源重复论文（一次性运维脚本）。

分组规则与入库去重一致：DOI（小写）/ arXiv 别名 / 标题+发布日期归一。
每组保留一个 canonical（优先有 AI 结果的，其次最早入库），子表
（ai_results / feedback / knowledge_cards / fulltext_analysis /
ignored_papers）重指到 canonical 后删除重复行。

用法:
    python3 scripts/merge_duplicates.py --dry-run   # 只打印分组，不写库
    python3 scripts/merge_duplicates.py             # 执行合并
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db import get_conn, init_db, sync_write  # noqa: E402

_ARXIV_ID_RE = re.compile(r"arxiv\.org/(?:pdf|abs)/([0-9]{4}\.[0-9]{4,5})", re.I)
_CHILD_TABLES = ("ai_results", "feedback", "knowledge_cards", "fulltext_analysis", "ignored_papers")


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def _aliases(row) -> set[str]:
    out = {row["id"].strip().lower()} if row["id"] else set()
    doi = (row["doi"] or "").strip().lower()
    if doi:
        out.add(doi)
        if doi.startswith("10.48550/arxiv."):
            out.add(doi.split("arxiv.", 1)[1].lower())
    for u in (row["pdf"] or "", row["url"] or ""):
        m = _ARXIV_ID_RE.search(u)
        if m:
            out.add(m.group(1).lower())
    out.discard("")
    return out


class _UnionFind:
    def __init__(self, n): self.p = list(range(n))
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x
    def union(self, a, b): self.p[self.find(a)] = self.find(b)


def find_duplicate_groups(conn) -> list[list[dict]]:
    rows = [dict(r) for r in conn.execute(
        "SELECT rowid AS _rid, id, doi, title, pdf, url, published_date FROM papers")]
    uf = _UnionFind(len(rows))
    idx = {r["id"]: i for i, r in enumerate(rows)}

    by_alias: dict[str, int] = {}
    for i, r in enumerate(rows):
        for a in _aliases(r):
            if a in by_alias:
                uf.union(i, by_alias[a])
            else:
                by_alias[a] = i
    # 注：不再单独按 doi 建映射——_aliases 已含 doi，且此处曾因字典推导式
    # 误用外层泄漏的 i（全部 DOI 映射到同一行）把 1188 篇链成一个巨型分量
    by_title: dict[tuple, int] = {}
    for i, r in enumerate(rows):
        key = (_norm_title(r["title"]), r["published_date"])
        if key[0] and key[1]:
            if key in by_title:
                uf.union(i, by_title[key])
            else:
                by_title[key] = i
    del idx

    groups: dict[int, list[dict]] = {}
    for i, r in enumerate(rows):
        groups.setdefault(uf.find(i), []).append(r)
    return [g for g in groups.values() if len(g) > 1]


def _pick_canonical(conn, group: list[dict]) -> dict:
    ai = {r[0] for r in conn.execute("SELECT paper_id FROM ai_results")}
    with_ai = [r for r in group if r["id"] in ai]
    pool = with_ai or group
    return min(pool, key=lambda r: r["_rid"])  # 最早入库的


def merge(dry_run: bool = True) -> dict:
    init_db()
    # 写队列可能是异步批量刷盘——直接读 conn 前先同步清空（无待写时是空操作）
    sync_write("SELECT 1")
    conn = get_conn()
    groups = find_duplicate_groups(conn)
    if dry_run:
        for g in groups:
            print(f"  [{len(g)} 篇] {g[0]['title'][:56]}")
            for r in g:
                print(f"      - {r['id'][:44]:<44} {r['doi'] or '-'}")
        return {"groups": len(groups), "dups": sum(len(g) - 1 for g in groups), "merged": 0}

    moved, deleted = 0, 0
    for g in groups:
        canon = _pick_canonical(conn, g)["id"]
        for r in g:
            if r["id"] == canon:
                continue
            dup_id = r["id"]
            # 子表搬到 canonical（已有 canonical 行的表保持 canonical 数据）
            for table in _CHILD_TABLES:
                moved += conn.execute(
                    f"UPDATE OR IGNORE {table} SET paper_id = ? WHERE paper_id = ?",
                    (canon, dup_id)).rowcount
                conn.execute(f"DELETE FROM {table} WHERE paper_id = ?", (dup_id,))
            # 聚类里的 paper_ids 同步剔除被合并方（否则图谱节点计数与下钻列表不一致）
            for row in conn.execute("SELECT cluster_id, paper_ids FROM knowledge_clusters").fetchall():
                try:
                    pids = json.loads(row["paper_ids"]) if isinstance(row["paper_ids"], str) else row["paper_ids"]
                except json.JSONDecodeError:
                    continue
                if dup_id in pids:
                    pids = [x for x in pids if x != dup_id]
                    conn.execute("UPDATE knowledge_clusters SET paper_ids = ? WHERE cluster_id = ?",
                                 (json.dumps(pids, ensure_ascii=False), row["cluster_id"]))
            conn.execute("DELETE FROM papers WHERE id = ?", (dup_id,))
            deleted += 1
        print(f"  合并 {len(g)} 篇 → {canon[:44]}")
    conn.commit()
    return {"groups": len(groups), "dups": deleted, "moved": moved}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        print("══ 重复分组（dry-run，不写库）══")
    else:
        print("══ 执行合并 ══")
    r = merge(dry_run=args.dry_run)
    print(f"\n分组 {r['groups']} 组，重复 {r['dups']} 篇"
          + (f"，子表迁移 {r['moved']} 行" if not args.dry_run else "（dry-run）"))
