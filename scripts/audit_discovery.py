#!/usr/bin/env python3
"""发现质量审计：预筛误杀结构 + 评分×反馈混淆矩阵 + 引文锚点池。

用法：python scripts/audit_discovery.py [--sample N]
--sample N 随机抽 N 条本地预筛拒绝的论文标题人工核对误杀。
"""
from __future__ import annotations

import argparse
import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0, help="抽查本地预筛拒绝的论文数")
    args = parser.parse_args()

    conn = sqlite3.connect("data/papers.db")

    print("═" * 60)
    print("① 拒绝漏斗结构（ignored_papers 按原因）")
    print("═" * 60)
    rows = conn.execute("""
        SELECT CASE
            WHEN reason = 'local_filter_reject' THEN '1_本地预筛(免费)'
            WHEN reason = 'quick_filter_reject' THEN '2_快速过滤(便宜LLM)'
            WHEN reason IN ('user_deleted','purge','purge_before_date') THEN '9_用户删除'
            ELSE '3_AI判定ignore'
        END AS stage, COUNT(*) AS n
        FROM ignored_papers GROUP BY stage ORDER BY stage
    """).fetchall()
    total = sum(r[1] for r in rows)
    for stage, n in rows:
        bar = "█" * max(1, n * 40 // max(total, 1))
        print(f"  {stage:24s} {n:7d}  {bar}")
    print(f"  {'合计':24s} {total:7d}")

    print()
    print("═" * 60)
    print("② 评分 × 用户反馈混淆矩阵（AI推荐级别 vs like/dislike）")
    print("═" * 60)
    rows = conn.execute("""
        SELECT COALESCE(a.recommendation, '(无AI)'), COALESCE(f.rating, '(未评)'),
               COUNT(*) AS n
        FROM feedback f
        LEFT JOIN ai_results a ON a.paper_id = f.paper_id
        WHERE f.rating IN ('like', 'dislike')
        GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchall()
    recs, data = set(), {}
    for rec, rating, n in rows:
        recs.add(rec)
        data[(rec, rating)] = n
    ratings = ["like", "dislike"]
    print(f"  {'推荐级别':<14s}" + "".join(f"{r:>10s}" for r in ratings) + f"{'like占比':>10s}")
    for rec in sorted(recs):
        like = data.get((rec, "like"), 0)
        dis = data.get((rec, "dislike"), 0)
        tot = like + dis
        ratio = f"{like / tot * 100:.0f}%" if tot else "-"
        print(f"  {rec:<14s}" + "".join(f"{data.get((rec, r), 0):>10d}" for r in ratings) + f"{ratio:>10s}")
    print("  （must-read 的 dislike 占比高 → system.txt 校准阈值该收紧）")

    print()
    print("═" * 60)
    print("③ 引文顺藤摸瓜锚点池")
    print("═" * 60)
    n_must = conn.execute(
        "SELECT COUNT(*) FROM ai_results WHERE recommendation='must-read'").fetchone()[0]
    n_liked = conn.execute(
        "SELECT COUNT(*) FROM feedback WHERE rating='like'").fetchone()[0]
    n_anchor = conn.execute("""
        SELECT COUNT(DISTINCT p.id) FROM papers p
        LEFT JOIN feedback f ON f.paper_id = p.id
        WHERE p.doi IS NOT NULL AND p.doi != ''
          AND (EXISTS (SELECT 1 FROM ai_results a WHERE a.paper_id=p.id AND a.recommendation='must-read')
               OR f.rating='like')
    """).fetchone()[0]
    n_cited = conn.execute("SELECT COUNT(*) FROM papers WHERE source='citation'").fetchone()[0]
    print(f"  must-read: {n_must} | 用户点赞: {n_liked} | 有DOI可用锚点: {n_anchor} | 已入库引文论文: {n_cited}")
    print(f"  （每轮取前 CITATION_ANCHORS_PER_RUN=10 个锚点轮换，约 {n_anchor // 10 if n_anchor else 0} 天一轮）")

    if args.sample > 0:
        print()
        print("═" * 60)
        print(f"④ 抽查 {args.sample} 条本地预筛拒绝的论文（人工判断是否误杀）")
        print("═" * 60)
        rows = conn.execute("""
            SELECT paper_id FROM ignored_papers
            WHERE reason='local_filter_reject' ORDER BY RANDOM() LIMIT ?
        """, (args.sample,)).fetchall()
        if not rows:
            print("  （暂无 local_filter_reject 记录——本地预筛上线后的首轮爬取还未发生）")
        for (pid,) in rows:
            row = conn.execute("SELECT title FROM papers WHERE id=?", (pid,)).fetchone()
            title = row[0] if row else "(论文未入库，仅记录了ID)"
            print(f"  - [{pid}] {title}")

    conn.close()


if __name__ == "__main__":
    main()
