#!/usr/bin/env python3
"""One-time backfill: extract GitHub links from existing papers' abstracts.

New papers get code_url at insert time (paper_store.extract_code_url);
this script enriches the existing corpus. Safe to re-run (skips filled rows).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

from db import init_db
from paper_store import extract_code_url

init_db()
conn = sqlite3.connect("data/papers.db", timeout=30)
rows = conn.execute("SELECT id, summary, comment FROM papers WHERE code_url IS NULL OR code_url = ''").fetchall()
print(f"待回填: {len(rows)} 篇")
updated = 0
for pid, summary, comment in rows:
    url = extract_code_url({"summary": summary, "comment": comment})
    if url:
        conn.execute("UPDATE papers SET code_url = ? WHERE id = ?", (url, pid))
        updated += 1
conn.commit()
conn.close()
print(f"✅ 提取到代码链接: {updated}/{len(rows)} 篇")
