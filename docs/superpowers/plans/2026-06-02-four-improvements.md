# arxivSCI-daily 四项改进实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 4 项基础设施问题：CCF 等级持久化、ignored reason 结构化、反馈系统重设计、L1 知识卡片打通。

**Architecture:** 4 个独立任务，按基础→反馈→知识管线排序。每个任务独立可验证，不依赖后续任务。

**Tech Stack:** Python 3.12, SQLite, Flask, LangChain, vanilla JS (ES modules)

**数据库当前状态:** 872 papers (arxiv:334, crossref:7, dblp:188, openalex:309, s2:34), 1024 ignored_papers (quick_filter_reject:884, ai_ignore:140), knowledge_cards/clusters/trend_reports 全部为空, feedback 全部为空。

---

## File Structure

| File | Role | Task |
|:-----|:-----|:-----|
| `db.py` | SQLite schema + write queue | T1 (add ccf_tier column) |
| `paper_store.py` | Paper CRUD + AI enhance | T1 (write ccf_tier on insert), T2 (structured ignore reason) |
| `migrate_ccf.py` | One-shot migration: backfill ccf_tier | T1 (new file) |
| `ai/structure.py` | Pydantic models | T2 (add structured reason enum) |
| `ai/system.txt` | AI enhance system prompt | T2 (instruct structured skip_reason) |
| `api.py` | Flask REST endpoints | T3 (new feedback endpoints) |
| `js/render.js` | Paper card rendering | T3 (feedback UI in card footer) |
| `js/modal.js` | Paper detail modal | T3 (feedback UI in detail) |
| `js/app.js` | Event binding | T3 (feedback event handlers) |
| `js/state.js` | Shared state | T3 (feedback state) |
| `css/styles.css` | Styling | T3 (feedback slider styles) |
| `ai/knowledge_extractor.py` | L1 knowledge card extraction | T4 (verify + fix pipeline) |
| `jobs.py` | Background job runner | T4 (ensure knowledge extraction runs) |

---

### Task 1: CCF Tier DB Column + Backfill

**Problem:** `_match_ccf()` computes tier at query time in `_row_to_dict()`, but papers table has no `ccf_tier` column. The value is never persisted, causing repeated computation and making CCF-based SQL queries impossible.

**Files:**
- Modify: `db.py:72-94` (schema)
- Modify: `paper_store.py:64-71` (PAPER_COLS), `paper_store.py:110-126` (_insert_paper_row), `paper_store.py:216-250` (_row_to_dict)
- Create: `migrate_ccf.py` (one-shot backfill script)

- [ ] **Step 1: Add ccf_tier column to papers table schema**

In `db.py`, add `ccf_tier TEXT` column after `citation_count` in the CREATE TABLE statement:

```python
# db.py line ~89, inside the papers CREATE TABLE
            citation_count INTEGER DEFAULT 0,
            ccf_tier TEXT,
            version TEXT,
```

Also add an index for the new column, after the existing indexes:

```python
        CREATE INDEX IF NOT EXISTS idx_papers_ccf_tier ON papers(ccf_tier);
```

- [ ] **Step 2: Add ccf_tier to PAPER_COLS in paper_store.py**

In `paper_store.py`, add `ccf_tier` to the column list:

```python
PAPER_COLS = [
    "id", "source", "title", "summary",
    "authors", "categories",
    "doi", "published_date", "url", "pdf",
    "publisher", "journal_title", "issn",
    "comment", "article_type",
    "venue", "acceptance", "citation_count", "ccf_tier", "version",
]
```

- [ ] **Step 3: Compute and store ccf_tier in _insert_paper_row**

In `paper_store.py`, modify `_insert_paper_row` to compute CCF tier before insert:

```python
def _insert_paper_row(p: dict) -> None:
    row: dict = {}
    for col in PAPER_COLS:
        val = p.get(col)
        if col in _JSON_FIELDS and val is not None:
            val = json.dumps(val, ensure_ascii=False)
        row[col] = val

    # Compute CCF tier from venue/journal_title if not already set
    if not row.get("ccf_tier"):
        row["ccf_tier"] = _match_ccf(row.get("venue", ""), row.get("journal_title", "")) or None

    placeholders = ", ".join(f":{c}" for c in PAPER_COLS)
    cols = ", ".join(PAPER_COLS)
    sql = f"INSERT OR IGNORE INTO papers ({cols}) VALUES ({placeholders})"
    queue_write(sql, tuple(row[c] for c in PAPER_COLS))
```

- [ ] **Step 4: Read ccf_tier from DB instead of computing at query time**

In `paper_store.py`, modify `_row_to_dict` to read `ccf_tier` from the row directly, falling back to computation only if the column is empty:

```python
    # Replace the last 3 lines of _row_to_dict:
    # ccf_tier from DB column, fallback to computation
    ccf = d.get("ccf_tier")
    if not ccf:
        ccf = _match_ccf(d.get("venue", ""), d.get("journal_title", ""))
    d["ccf_tier"] = ccf

    return d
```

- [ ] **Step 5: Create migration script to backfill ccf_tier**

Create `migrate_ccf.py`:

```python
"""One-shot migration: backfill ccf_tier column from venue/journal_title."""
import sqlite3
from paper_store import _match_ccf

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

    # Print stats
    conn = sqlite3.connect(DB_PATH)
    stats = conn.execute("SELECT ccf_tier, COUNT(*) FROM papers GROUP BY ccf_tier ORDER BY ccf_tier").fetchall()
    for tier, count in stats:
        print(f"  {tier or '(unmatched)'}: {count}")
    conn.close()

if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run migration and verify**

```bash
# First, add the column to existing DB (ALTER TABLE for already-created databases)
sqlite3 data/papers.db "ALTER TABLE papers ADD COLUMN ccf_tier TEXT;"
sqlite3 data/papers.db "CREATE INDEX IF NOT EXISTS idx_papers_ccf_tier ON papers(ccf_tier);"

# Run backfill
cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python migrate_ccf.py
```

Expected output: `Backfilled ~408/872 papers with CCF tier` (A:228, B:61, C:119)

- [ ] **Step 7: Verify CCF tier in API response**

```bash
curl -s localhost:8080/api/papers?per_page=5 | python3 -m json.tool | grep ccf_tier
```

Expected: some papers show `"ccf_tier": "A"`, `"B"`, `"C"`, or `""`

- [ ] **Step 8: Commit**

```bash
git add db.py paper_store.py migrate_ccf.py
git commit -m "feat: persist CCF tier in DB column with backfill migration"
```

---

### Task 2: Structured Ignore Reasons

**Problem:** `ignored_papers.reason` is inconsistent: 884 entries use `"quick_filter_reject"`, 140 entries use long Chinese AI-generated sentences. This makes statistical analysis impossible. New AI-rejected papers should use fixed labels.

**Files:**
- Modify: `ai/structure.py:14-15` (skip_reason field)
- Modify: `ai/system.txt` (system prompt for AI enhance — instruct structured reason)
- Modify: `paper_store.py:190-196` (map skip_reason to label)

- [ ] **Step 1: Update Structure model skip_reason description**

In `ai/structure.py`, change the `skip_reason` field description:

```python
    skip_reason: str = Field(default="", description='when recommendation is ignore: one of "low_relevance", "weak_method", "no_empirical", "domain_mismatch", "poor_quality"; otherwise empty string')
```

- [ ] **Step 2: Update AI system prompt to enforce structured reasons**

Read the current `ai/system.txt` file first, then append the following instruction at the end:

```
When you set recommendation to "ignore", the skip_reason field MUST be exactly one of these labels:
- "low_relevance": paper topic is outside the researcher's direction
- "weak_method": method lacks novelty or is incremental
- "no_empirical": no experimental results or validation
- "domain_mismatch": application domain is unrelated to the researcher
- "poor_quality": paper quality is below threshold (missing abstract, trivial result, etc.)

Do NOT write free-text explanations in skip_reason. Use only these exact labels.
```

- [ ] **Step 3: Add skip_reason mapping in paper_store.py**

In `paper_store.py`, add a mapping function after the imports:

```python
_SKIP_REASON_MAP = {
    "low_relevance": "low_relevance",
    "weak_method": "weak_method",
    "no_empirical": "no_empirical",
    "domain_mismatch": "domain_mismatch",
    "poor_quality": "poor_quality",
}
```

Then modify the AI reject section in `append_paper`:

```python
                if ai_data.get("recommendation") in ("skip", "ignore"):
                    raw_reason = ai_data.get("skip_reason", "") or "low_relevance"
                    reason = _SKIP_REASON_MAP.get(raw_reason, "low_relevance")
                    ignore_paper(paper.id, reason)
                    logger.debug(f"AI rated ignore ({reason}): {paper.id}")
                    return "ai_reject"
```

- [ ] **Step 4: Verify with a test crawl or manual check**

```bash
# Check that existing reasons are preserved (not overwritten)
sqlite3 data/papers.db "SELECT reason, COUNT(*) FROM ignored_papers GROUP BY reason ORDER BY COUNT(*) DESC LIMIT 10;"
```

The existing 140 long-text reasons remain unchanged (no backfill per user decision). Only new AI rejections will use structured labels.

- [ ] **Step 5: Commit**

```bash
git add ai/structure.py ai/system.txt paper_store.py
git commit -m "feat: structured ignore reason labels for AI-rejected papers"
```

---

### Task 3: Feedback System Redesign (3 dimensions)

**Problem:** Current feedback table only stores `useful`/`not_useful` binary rating. Frontend has like/dislike buttons but feedback table is empty — the API endpoint exists (`POST /api/feedback`) but the UI interaction chain is broken. User wants 3 dimensions: like/dislike + relevance (1-5) + novelty (1-5). UI should be embedded in cards with expandable sliders.

**Files:**
- Modify: `db.py:113-118` (feedback table schema — expand columns)
- Modify: `api.py:217-241` (feedback API — accept new dimensions)
- Modify: `js/render.js:59-77` (card footer — expandable feedback UI)
- Modify: `js/modal.js:67-78` (detail modal — feedback buttons + sliders)
- Modify: `js/app.js` (feedback event delegation — handle sliders)
- Modify: `js/state.js` (feedback state — store user ratings)
- Modify: `css/styles.css` (feedback slider + rating styles)

- [ ] **Step 1: Update feedback table schema in db.py**

Replace the current feedback CREATE TABLE with expanded schema:

```python
        CREATE TABLE IF NOT EXISTS feedback (
            paper_id TEXT PRIMARY KEY,
            rating TEXT CHECK (rating IN ('like', 'dislike', '')),
            relevance INTEGER CHECK (relevance BETWEEN 1 AND 5),
            novelty INTEGER CHECK (novelty BETWEEN 1 AND 5),
            note TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
        );
```

- [ ] **Step 2: Migrate existing feedback table**

For existing DB, run ALTER TABLE to add new columns:

```bash
sqlite3 data/papers.db "ALTER TABLE feedback ADD COLUMN relevance INTEGER;"
sqlite3 data/papers.db "ALTER TABLE feedback ADD COLUMN novelty INTEGER;"
sqlite3 data/papers.db "ALTER TABLE feedback ADD COLUMN note TEXT;"
sqlite3 data/papers.db "ALTER TABLE feedback ADD COLUMN updated_at TEXT NOT NULL DEFAULT (datetime('now'));"
```

- [ ] **Step 3: Update feedback API endpoint in api.py**

Replace the existing `save_feedback` and `get_feedback` endpoints:

```python
@app.route("/api/feedback", methods=["POST"])
def save_feedback():
    data = request.json or {}
    paper_id = data.get("paper_id", "")
    if not paper_id:
        return jsonify({"error": "paper_id required"}), 400

    rating = data.get("rating", "")
    relevance = data.get("relevance")
    novelty = data.get("novelty")
    note = data.get("note", "")

    if rating and rating not in ("like", "dislike"):
        return jsonify({"error": "invalid rating"}), 400

    queue_write(
        "INSERT OR REPLACE INTO feedback (paper_id, rating, relevance, novelty, note, updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
        (paper_id, rating or None, relevance, novelty, note or None),
    )
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
```

Remove the `_update_profile_from_feedback` function body — keep it as a no-op for now (feedback is stored only, not used to modify profile):

```python
def _update_profile_from_feedback(paper_id: str, rating: str):
    pass
```

- [ ] **Step 4: Add feedback state management in js/state.js**

Add at the end of state.js:

```javascript
export let feedbackData = {};

export function setFeedbackData(data) {
    feedbackData = data;
}

export function getFeedbackForPaper(paperId) {
    return feedbackData[paperId] || {};
}
```

- [ ] **Step 5: Load feedback data on app init in js/app.js**

In the initialization section of app.js (where `fetchPapers` is called), add a parallel fetch for feedback data. Find the `fetchPapers()` call and add nearby:

```javascript
async function fetchFeedback() {
    try {
        const resp = await fetch('/api/feedback');
        if (resp.ok) {
            const data = await resp.json();
            setFeedbackData(data);
        }
    } catch (e) {
        console.error('Failed to load feedback:', e);
    }
}
```

Call `fetchFeedback()` alongside `fetchPapers()` during initialization.

- [ ] **Step 6: Add feedback UI to card footer in js/render.js**

Replace the current `card-actions` div in the card template. The like/dislike buttons stay, and a small expandable rating section appears on like:

```javascript
        const fb = getFeedbackForPaper(paper.id);
        const userRating = fb.rating || '';
        const userRel = fb.relevance || 0;
        const userNov = fb.novelty || 0;
        const hasFeedback = userRating || userRel || userNov;
        return `
            <div class="paper-card ${isRead ? 'is-read' : ''}" data-idx="${idx}" data-rec="${rec}">
                <div class="paper-header">
                    ${sourceBadge}${venueBadge}${ccfBadge}${accBadge}${aiBadge}${recBadge}${typeTag}
                    <div class="paper-categories">${categories}${codeBadge}</div>
                    <button class="bookmark-btn ${isBookmarked ? 'active' : ''}" data-bm-id="${escAttr(paper.id)}" title="${isBookmarked ? '取消收藏' : '收藏'}">${isBookmarked ? '★' : '☆'}</button>
                </div>
                <div class="paper-title">${title}</div>
                ${cardTldr}
                <div class="paper-footer">
                    <span class="paper-authors">${authors}</span>
                    <div class="card-actions">
                        <button class="card-vote-btn ${userRating === 'like' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-action="like" title="有用">&#9757;</button>
                        <button class="card-vote-btn ${userRating === 'dislike' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-action="dislike" title="没用">&#9759;</button>
                        <span class="paper-meta-date">${paper.published_date || ''} ${citeBadge}</span>
                    </div>
                </div>
                ${hasFeedback ? `<div class="card-feedback-detail" data-feedback-detail="${escAttr(paper.id)}">
                    <div class="feedback-slider-row"><span class="feedback-label">相关性</span><input type="range" min="1" max="5" value="${userRel || 3}" class="feedback-slider" data-slider-type="relevance" data-slider-id="${escAttr(paper.id)}"><span class="feedback-val">${userRel || '-'}</span></div>
                    <div class="feedback-slider-row"><span class="feedback-label">新颖性</span><input type="range" min="1" max="5" value="${userNov || 3}" class="feedback-slider" data-slider-type="novelty" data-slider-id="${escAttr(paper.id)}"><span class="feedback-val">${userNov || '-'}</span></div>
                </div>` : ''}
            </div>`;
```

Add the import at the top of render.js:

```javascript
import { filteredPapers, allPapers, activeFilters, sortOrder, currentPage, PAGE_SIZE,
    _bookmarks, _readPapers, escAttr, inferType, showToast, setCurrentPage,
    getFeedbackForPaper, feedbackData,
} from './state.js';
```

- [ ] **Step 7: Update feedback event handlers in js/app.js**

Replace the existing feedback button delegation. Find the `data-feedback-rating` handler and replace with:

```javascript
// Feedback: like/dislike buttons (delegation from card)
document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-feedback-action]');
    if (!btn) return;
    e.stopPropagation();
    const paperId = btn.dataset.feedbackId;
    const action = btn.dataset.feedbackAction;
    const current = feedbackData[paperId] || {};
    const newRating = current.rating === action ? '' : action;

    fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            paper_id: paperId,
            rating: newRating,
            relevance: current.relevance || null,
            novelty: current.novelty || null,
        }),
    }).then(r => r.ok ? fetchFeedback() : null).then(() => renderPapers());
});

// Feedback: sliders (delegation)
document.addEventListener('change', (e) => {
    if (!e.target.classList.contains('feedback-slider')) return;
    const paperId = e.target.dataset.sliderId;
    const type = e.target.dataset.sliderType;
    const value = parseInt(e.target.value);
    const current = feedbackData[paperId] || {};

    fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            paper_id: paperId,
            rating: current.rating || '',
            relevance: type === 'relevance' ? value : (current.relevance || null),
            novelty: type === 'novelty' ? value : (current.novelty || null),
        }),
    }).then(r => r.ok ? fetchFeedback() : null).then(() => {
        const valSpan = e.target.nextElementSibling;
        if (valSpan) valSpan.textContent = value;
    });
});
```

Also update imports in app.js:

```javascript
import { setFeedbackData, feedbackData } from './state.js';
```

And ensure `fetchFeedback` and `renderPapers` are accessible in the event handler scope.

- [ ] **Step 8: Update feedback UI in modal (js/modal.js)**

Replace the existing feedback buttons in the detail modal. In the `openPaperDetail` function, replace the two feedback buttons:

```javascript
            const fb = getFeedbackForPaper(paper.id);
            const userRating = fb.rating || '';
            const userRel = fb.relevance || 0;
            const userNov = fb.novelty || 0;
            const hasFeedback = userRating || userRel || userNov;
            ...
            <button class="follow-btn ${userRating === 'like' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-action="like" style="border-color:#22c55e;color:#22c55e">${userRating === 'like' ? '★ 有用' : '有用'}</button>
            <button class="follow-btn ${userRating === 'dislike' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-action="dislike" style="border-color:#ef4444;color:#ef4444">${userRating === 'dislike' ? '★ 没用' : '没用'}</button>
            <div class="modal-feedback-sliders" style="margin-top:12px;display:${hasFeedback ? 'block' : 'none'}">
                <div class="feedback-slider-row"><span class="feedback-label">相关性</span><input type="range" min="1" max="5" value="${userRel || 3}" class="feedback-slider" data-slider-type="relevance" data-slider-id="${escAttr(paper.id)}"><span class="feedback-val">${userRel || '-'}</span></div>
                <div class="feedback-slider-row"><span class="feedback-label">新颖性</span><input type="range" min="1" max="5" value="${userNov || 3}" class="feedback-slider" data-slider-type="novelty" data-slider-id="${escAttr(paper.id)}"><span class="feedback-val">${userNov || '-'}</span></div>
            </div>
```

Add import:

```javascript
import { markRead, escAttr, showToast, setAllPapers, getFeedbackForPaper } from './state.js';
```

- [ ] **Step 9: Add feedback slider styles in css/styles.css**

Append to the end of styles.css:

```css
/* Feedback rating sliders */
.card-feedback-detail {
    margin-top: 6px;
    padding: 8px 10px;
    background: var(--accent-bg);
    border-radius: 6px;
}
.feedback-slider-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 4px 0;
}
.feedback-label {
    font-size: 0.75rem;
    color: var(--text-secondary);
    min-width: 40px;
}
.feedback-slider {
    flex: 1;
    accent-color: var(--accent);
    height: 4px;
    cursor: pointer;
}
.feedback-val {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--accent-light);
    min-width: 16px;
    text-align: center;
}
.modal-feedback-sliders {
    padding: 8px 0;
}
.modal-feedback-sliders .feedback-slider-row {
    margin: 6px 0;
}
```

- [ ] **Step 10: Verify feedback flow end-to-end**

1. Start the server: `python daemon.py`
2. Open browser to `localhost:8080`
3. Click the like button on a paper card — should see button highlight
4. Verify the slider row appears after clicking like
5. Adjust sliders, check they persist on page reload
6. Check DB: `sqlite3 data/papers.db "SELECT * FROM feedback;"`

- [ ] **Step 11: Commit**

```bash
git add db.py api.py js/render.js js/modal.js js/app.js js/state.js css/styles.css
git commit -m "feat: 3-dimension feedback system with like/dislike + relevance + novelty ratings"
```

---

### Task 4: L1 Knowledge Card Pipeline Activation

**Problem:** `knowledge_cards` table is empty (0 rows). The extraction code exists (`ai/knowledge_extractor.py`), the API endpoints exist (`GET /api/knowledge-cards`, `POST /api/trigger/knowledge-extract`), and `_insert_knowledge_card()` is called during `append_paper()`. But the pipeline has never been triggered for the existing 872 papers. The retro-extract function `_retro_knowledge_extract()` in `api.py:321-350` queries papers with AI results but no cards — but it's never been called.

**Root causes to verify:**
1. The `_retro_knowledge_extract` trigger endpoint exists but has never been invoked
2. The `extract_knowledge_card()` function requires AI-enhanced papers (tldr/method fields) — need to check how many papers have AI data
3. The `knowledge_extractor.py` uses `ChatOpenAI(model="deepseek-v4-flash")` — need to verify model is reachable

**Files:**
- Verify: `ai/knowledge_extractor.py` (extraction logic)
- Verify: `api.py:315-350` (trigger endpoint + retro-extract)
- Modify: `paper_store.py:144-151` (ensure card insertion works with queue_write)
- Modify: `jobs.py` (add knowledge extraction to post-crawl pipeline)

- [ ] **Step 1: Check how many papers have AI data (prerequisite for knowledge extraction)**

```bash
sqlite3 data/papers.db "SELECT COUNT(*) FROM ai_results WHERE tldr IS NOT NULL AND tldr != '';"
sqlite3 data/papers.db "SELECT COUNT(*) FROM ai_results WHERE recommendation NOT IN ('skip', 'ignore');"
```

Expected: should show papers eligible for knowledge extraction. If count is 0, need to run retro-enhance first.

- [ ] **Step 2: Verify the trigger endpoint is registered**

Check that `api.py` has the `/api/trigger/knowledge-extract` route and it calls `_retro_knowledge_extract`. The endpoint already exists at line 315-318. Also verify the duplicate route at line 170-173 doesn't conflict.

If both routes exist for the same path, remove the duplicate at line 170-173:

In `api.py`, the `trigger_job` function at line 169 handles `"knowledge-extract"` as a special case. Verify it doesn't duplicate the dedicated endpoint at line 315. If both exist, remove the special case from `trigger_job` and keep only the dedicated endpoint.

- [ ] **Step 3: Test knowledge extraction manually with a single paper**

```bash
# Start the server
python daemon.py &

# Trigger knowledge extraction
curl -X POST http://localhost:8080/api/trigger/knowledge-extract
```

Monitor logs for errors. Common issues:
- `MODEL_NAME` env var not set → defaults to `deepseek-v4-flash`
- API key not configured → check `.env` file
- LangChain template variable parsing → already fixed with `{{"queries"}}`

- [ ] **Step 4: Verify cards were created**

```bash
sqlite3 data/papers.db "SELECT COUNT(*) FROM knowledge_cards;"
sqlite3 data/papers.db "SELECT paper_id, problem, method_extracted FROM knowledge_cards LIMIT 5;"
```

Expected: cards with non-empty problem/method_extracted/result_extracted fields.

- [ ] **Step 5: Verify _insert_knowledge_card uses DB default for extracted_at**

The `CARD_COLS` list does not include `extracted_at`; the schema has `DEFAULT (datetime('now'))`. Verify the insert works:

```bash
# After running Step 3 trigger, check timestamps
sqlite3 data/papers.db "SELECT paper_id, extracted_at FROM knowledge_cards LIMIT 3;"
```

Expected: `extracted_at` populated with current timestamp.

- [ ] **Step 6: Add knowledge extraction to post-crawl pipeline in jobs.py**

In `jobs.py`, add knowledge extraction after retro-enhance in the `_run_and_reschedule` method. Find the section after `run_retro_enhance()`:

```python
        if job_name == "arxiv":
            try:
                run_retro_enhance()
            except Exception as e:
                logger.error(f"Retro-enhance after arxiv error: {e}")
            try:
                from api import _retro_knowledge_extract
                _retro_knowledge_extract()
            except Exception as e:
                logger.error(f"Knowledge extract after arxiv error: {e}")
            try:
                run_digest_job()
            except Exception as e:
                logger.error(f"Digest after arxiv error: {e}")
```

This ensures knowledge cards are extracted for newly enhanced papers after each arxiv crawl cycle.

- [ ] **Step 7: Verify frontend knowledge card display**

1. Open a paper detail modal that has a knowledge card
2. Verify the "知识卡片" section appears with Problem/Method/Result/Keywords fields
3. Check browser console for errors

The frontend code in `js/modal.js:80-96` already handles card display — it calls `fetchKnowledgeCard(paper.id)` and renders the result.

- [ ] **Step 8: Commit**

```bash
git add jobs.py paper_store.py api.py
git commit -m "feat: activate L1 knowledge card extraction pipeline with post-crawl trigger"
```
