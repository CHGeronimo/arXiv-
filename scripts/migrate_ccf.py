"""One-shot migration: backfill ccf_tier column from venue/journal_title."""
import sqlite3
from backend.paper_store import _match_ccf

DB_PATH = "data/papers.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, venue, journal_title, ccf_tier FROM papers").fetchall()

    updated = 0
    for row in rows:
        existing = row["ccf_tier"]
        if existing:
            continue
        tier = _match_ccf(row["venue"] or "", row["journal_title"] or "")
        if tier:
            conn.execute("UPDATE papers SET ccf_tier = ? WHERE id = ?", (tier, row["id"]))
            updated += 1

    conn.commit()
    conn.close()
    print(f"Backfilled {updated}/{len(rows)} papers with CCF tier")

    conn = sqlite3.connect(DB_PATH)
    stats = conn.execute("SELECT ccf_tier, COUNT(*) FROM papers GROUP BY ccf_tier ORDER BY ccf_tier").fetchall()
    for tier, count in stats:
        print(f"  {tier or '(unmatched)'}: {count}")
    conn.close()

if __name__ == "__main__":
    main()
