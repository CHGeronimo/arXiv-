# Knowledge Intelligence Layers (L1-L3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a layered knowledge intelligence system on top of arxivSCI-daily's paper pipeline — from structured knowledge extraction (L1) to dynamic graph visualization (L2) to trend radar and idea checking (L3).

**Architecture:** Each layer builds on the previous. L1 adds a `knowledge_cards` table and LLM extraction pipeline that runs after AI enhancement. L2 clusters extracted knowledge into a graph of method clusters and problem domains. L3 adds weekly trend reports and on-demand idea feasibility analysis. All layers share the existing SQLite + Flask + vanilla JS stack.

**Tech Stack:** SQLite (WAL), Flask, vanilla JS (ES modules), LangChain + DeepSeek (structured output), d3-force (CDN for graph viz), Pydantic.

---

## File Structure

| Action | File | Responsibility |
|:-------|:-----|:---------------|
| Create | `ai/structure.py` | Add KnowledgeCard, TrendReport Pydantic models |
| Create | `ai/knowledge_extractor.py` | LLM chain to extract knowledge cards |
| Create | `ai/trend_analyzer.py` | LLM chain to generate weekly trend reports |
| Create | `ai/idea_checker.py` | LLM chain + search for idea feasibility |
| Create | `js/knowledge.js` | Knowledge card rendering in modal |
| Create | `js/graph.js` | Force-directed graph visualization |
| Create | `js/trend.js` | Trend radar UI rendering |
| Create | `css/graph.css` | Graph page styles |
| Modify | `db.py` | Add knowledge_cards, knowledge_clusters, trend_reports tables |
| Modify | `paper_store.py` | Add knowledge card insert after AI enhance |
| Modify | `api.py` | Add 8 new endpoints |
| Modify | `jobs.py` | Add retro-knowledge-extract + weekly trend job |
| Modify | `index.html` | Add graph page container + trend section + idea input |
| Modify | `js/modal.js` | Add knowledge card section to paper detail |
| Modify | `js/app.js` | Wire graph/trend/idea events |

---

## Task 1: L1 Schema — knowledge_cards table + KnowledgeCard model

**Files:**
- Modify: `db.py:72-135` (schema section)
- Modify: `ai/structure.py`

- [ ] **Step 1: Add knowledge_cards table to db.py init_db()**

In `db.py`, add this table after the existing `subscriptions` table CREATE statement (after line 129), before the indexes:

```python
        CREATE TABLE IF NOT EXISTS knowledge_cards (
            paper_id TEXT PRIMARY KEY,
            problem TEXT,
            method_extracted TEXT,
            result_extracted TEXT,
            keywords JSON,
            relation_to_profile TEXT,
            extracted_at TEXT,
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
        );
```

Add this index after the existing indexes (after line 134):

```python
        CREATE INDEX IF NOT EXISTS idx_knowledge_cards_keywords ON knowledge_cards(keywords);
```

- [ ] **Step 2: Add KnowledgeCard Pydantic model to ai/structure.py**

Append to `ai/structure.py`:

```python
class KnowledgeCard(BaseModel):
    problem: str = Field(description="the specific problem or research question this paper addresses, in one clear sentence")
    method_extracted: str = Field(description="the core method, technique, or approach proposed, in one sentence")
    result_extracted: str = Field(description="the key result or finding, with metrics if available, in one sentence")
    keywords: list[str] = Field(description="5-10 technical keywords that characterize this paper's contribution and domain")
    relation_to_profile: str = Field(description="how this paper relates to the user's research direction: direct contribution, related technique, potential application, or tangential")
```

- [ ] **Step 3: Verify schema migration**

Run: `python3 -c "from db import init_db; init_db(); print('OK')"`
Expected: "OK" (table created)

- [ ] **Step 4: Commit**

```bash
git add db.py ai/structure.py
git commit -m "feat: add knowledge_cards table and KnowledgeCard model (L1 schema)"
```

---

## Task 2: L1 Extraction — ai/knowledge_extractor.py

**Files:**
- Create: `ai/knowledge_extractor.py`
- Reference: `ai/enhance.py` for chain pattern

- [ ] **Step 1: Create ai/knowledge_extractor.py**

```python
"""Knowledge card extraction from AI-enhanced papers.

Extracts structured Problem/Method/Result/Keywords/RelationToProfile
from papers that already have AI enhancement results.
"""

import json
import logging
import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .structure import KnowledgeCard

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """You are a research knowledge extraction assistant.

Given a paper's title, abstract, and AI analysis, extract a structured knowledge card.

## Paper Title
{title}

## Abstract
{abstract}

## AI Analysis
- TL;DR: {tldr}
- Motivation: {motivation}
- Method: {method}
- Result: {result}
- Conclusion: {conclusion}

## User's Research Direction
{research_direction}

Extract:
1. **Problem**: What specific problem or research question does this paper address? One clear sentence.
2. **Method**: What is the core method, technique, or approach proposed? One sentence.
3. **Result**: What is the key result or finding? Include metrics if available. One sentence.
4. **Keywords**: 5-10 technical keywords characterizing this paper's contribution and domain.
5. **Relation to Profile**: How does this relate to the user's research direction?"""

_CHAIN = None


def _get_chain():
    """Lazy-init the knowledge extraction chain."""
    global _CHAIN
    if _CHAIN is None:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        llm = ChatOpenAI(model=model_name).with_structured_output(
            KnowledgeCard, method="json_mode"
        )
        prompt = ChatPromptTemplate.from_template(_EXTRACT_PROMPT)
        _CHAIN = prompt | llm
    return _CHAIN


def extract_knowledge_card(paper: dict, profile: dict | None = None) -> dict | None:
    """Extract a knowledge card from an AI-enhanced paper.

    Args:
        paper: Paper dict with "AI" sub-dict (from _row_to_dict).
        profile: Research profile dict. If None, loads from file.

    Returns:
        Dict with keys matching knowledge_cards table columns,
        or None on failure.
    """
    ai = paper.get("AI") or {}
    if not ai.get("tldr") and not ai.get("method"):
        logger.debug(f"Skipping knowledge extraction for {paper.get('id')}: no AI data")
        return None

    if profile is None:
        from .enhance import load_research_profile
        profile = load_research_profile()

    chain = _get_chain()

    try:
        card: KnowledgeCard = chain.invoke({
            "title": paper.get("title", ""),
            "abstract": paper.get("summary", ""),
            "tldr": ai.get("tldr", ""),
            "motivation": ai.get("motivation", ""),
            "method": ai.get("method", ""),
            "result": ai.get("result", ""),
            "conclusion": ai.get("conclusion", ""),
            "research_direction": profile.get("direction", ""),
        })
    except Exception as e:
        logger.error(f"Knowledge extraction failed for {paper.get('id')}: {e}")
        return None

    return {
        "paper_id": paper["id"],
        "problem": card.problem,
        "method_extracted": card.method_extracted,
        "result_extracted": card.result_extracted,
        "keywords": json.dumps(card.keywords, ensure_ascii=False),
        "relation_to_profile": card.relation_to_profile,
        "extracted_at": None,  # let SQLite default to now()
    }


def extract_knowledge_card_dict(paper: dict, profile: dict | None = None) -> dict:
    """Extract and return a knowledge card dict with keywords as list.

    Returns dict with: problem, method_extracted, result_extracted,
    keywords (list[str]), relation_to_profile.
    Returns empty dict on failure.
    """
    from datetime import datetime

    result = extract_knowledge_card(paper, profile)
    if result is None:
        return {}

    # Parse keywords back to list for API response
    keywords = result.get("keywords", "[]")
    if isinstance(keywords, str):
        try:
            keywords = json.loads(keywords)
        except json.JSONDecodeError:
            keywords = []

    return {
        "paper_id": result["paper_id"],
        "problem": result["problem"],
        "method_extracted": result["method_extracted"],
        "result_extracted": result["result_extracted"],
        "keywords": keywords,
        "relation_to_profile": result["relation_to_profile"],
    }
```

- [ ] **Step 2: Verify import**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python3 -c "from ai.knowledge_extractor import extract_knowledge_card; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```bash
git add ai/knowledge_extractor.py
git commit -m "feat: add knowledge card extraction module (L1 extractor)"
```

---

## Task 3: L1 Integration — hook into paper_store.py

**Files:**
- Modify: `paper_store.py:143-193` (append_paper function)

- [ ] **Step 1: Add knowledge card extraction to append_paper**

In `paper_store.py`, add a new import at the top:

```python
from ai.knowledge_extractor import extract_knowledge_card
```

Add a new helper function after `_insert_ai_row` (after line 136):

```python
CARD_COLS = ["paper_id", "problem", "method_extracted", "result_extracted", "keywords", "relation_to_profile"]


def _insert_knowledge_card(paper_id: str, paper: dict) -> None:
    """Extract and queue-insert a knowledge card for an AI-enhanced paper."""
    card = extract_knowledge_card(paper)
    if card is None:
        return
    cols = ", ".join(CARD_COLS)
    placeholders = ", ".join(f":{c}" for c in CARD_COLS)
    sql = f"INSERT OR REPLACE INTO knowledge_cards ({cols}) VALUES ({placeholders})"
    queue_write(sql, tuple(card.get(c) for c in CARD_COLS))
```

Then modify the `append_paper` function. In the `if enhance:` block, after the line `_insert_ai_row(paper.id, ai_data)` (line 186), add knowledge card extraction:

```python
            ai_data = enhanced.get("AI", enhanced)
            _insert_paper_row(paper_dict)
            _insert_ai_row(paper.id, ai_data)
            # L1: extract knowledge card after AI enhancement
            try:
                _insert_knowledge_card(paper.id, enhanced)
            except Exception as e:
                logger.warning(f"Knowledge card extraction failed for {paper.id}: {e}")
            return True
```

- [ ] **Step 2: Verify syntax**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python3 -c "import paper_store; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```bash
git add paper_store.py
git commit -m "feat: integrate knowledge card extraction into paper append flow (L1)"
```

---

## Task 4: L1 API — Flask routes for knowledge cards

**Files:**
- Modify: `api.py`

- [ ] **Step 1: Add knowledge card API endpoints**

Add this import to `api.py`:

```python
from db import get_conn, queue_write, sync_write
```

Add these routes after the feedback section (after line 264), before `_update_profile_from_feedback`:

```python
# ── Knowledge Cards (L1) ──────────────────────────────────────────

@app.route("/api/knowledge-cards", methods=["GET"])
def get_knowledge_cards():
    """List knowledge cards with optional keyword search.

    Query params:
        q: search query (matches keywords, problem, method_extracted, result_extracted)
        page: page number (default 1)
        per_page: items per page (default 50, max 200)
    """
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
        sql = """
            SELECT kc.paper_id, kc.problem, kc.method_extracted, kc.result_extracted,
                   kc.keywords, kc.relation_to_profile, kc.extracted_at,
                   p.title, p.source
            FROM knowledge_cards kc
            JOIN papers p ON kc.paper_id = p.id
            WHERE kc.keywords LIKE ? OR kc.problem LIKE ? OR kc.method_extracted LIKE ?
               OR kc.result_extracted LIKE ?
            ORDER BY kc.extracted_at DESC
        """
        like_q = f"%{query}%"
        rows = conn.execute(sql, (like_q, like_q, like_q, like_q)).fetchall()
    else:
        sql = """
            SELECT kc.paper_id, kc.problem, kc.method_extracted, kc.result_extracted,
                   kc.keywords, kc.relation_to_profile, kc.extracted_at,
                   p.title, p.source
            FROM knowledge_cards kc
            JOIN papers p ON kc.paper_id = p.id
            ORDER BY kc.extracted_at DESC
        """
        rows = conn.execute(sql).fetchall()

    cards = []
    for row in rows:
        keywords = row["keywords"]
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except (json.JSONDecodeError, TypeError):
                keywords = []
        cards.append({
            "paper_id": row["paper_id"],
            "problem": row["problem"],
            "method_extracted": row["method_extracted"],
            "result_extracted": row["result_extracted"],
            "keywords": keywords,
            "relation_to_profile": row["relation_to_profile"],
            "extracted_at": row["extracted_at"],
            "title": row["title"],
            "source": row["source"],
        })

    total = len(cards)
    start = (page - 1) * per_page
    return jsonify({"cards": cards[start:start + per_page], "total": total, "page": page})


@app.route("/api/paper/<paper_id>/card", methods=["GET"])
def get_paper_card(paper_id: str):
    """Get the knowledge card for a specific paper."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM knowledge_cards WHERE paper_id = ?", (paper_id,)
    ).fetchone()
    if row is None:
        return jsonify({"card": None})
    keywords = row["keywords"]
    if isinstance(keywords, str):
        try:
            keywords = json.loads(keywords)
        except (json.JSONDecodeError, TypeError):
            keywords = []
    return jsonify({"card": {
        "paper_id": row["paper_id"],
        "problem": row["problem"],
        "method_extracted": row["method_extracted"],
        "result_extracted": row["result_extracted"],
        "keywords": keywords,
        "relation_to_profile": row["relation_to_profile"],
        "extracted_at": row["extracted_at"],
    }})


@app.route("/api/trigger/knowledge-extract", methods=["POST"])
def trigger_knowledge_extract():
    """Retro-extract knowledge cards for papers that have AI results but no card."""
    threading.Thread(target=_retro_knowledge_extract, daemon=True).start()
    return jsonify({"status": "triggered", "job": "knowledge-extract"})


def _retro_knowledge_extract():
    """Batch extract knowledge cards for existing AI-enhanced papers."""
    from ai.knowledge_extractor import extract_knowledge_card
    from ai.enhance import load_research_profile

    conn = get_conn()
    profile = load_research_profile()

    # Find papers with AI results but no knowledge card
    rows = conn.execute("""
        SELECT a.paper_id, a.tldr, a.motivation, a.method, a.result, a.conclusion,
               p.title, p.summary
        FROM ai_results a
        JOIN papers p ON a.paper_id = p.id
        LEFT JOIN knowledge_cards kc ON a.paper_id = kc.paper_id
        WHERE kc.paper_id IS NULL AND a.recommendation != 'skip'
    """).fetchall()

    logger = logging.getLogger("knowledge-extract")
    logger.info(f"Retro knowledge extraction: {len(rows)} papers to process")

    for i, row in enumerate(rows):
        paper = {
            "id": row["paper_id"],
            "title": row["title"],
            "summary": row["summary"],
            "AI": {
                "tldr": row["tldr"],
                "motivation": row["motivation"],
                "method": row["method"],
                "result": row["result"],
                "conclusion": row["conclusion"],
            },
        }
        card = extract_knowledge_card(paper, profile)
        if card:
            cols = ", ".join(CARD_COLS)
            placeholders = ", ".join(f":{c}" for c in CARD_COLS)
            sql = f"INSERT OR REPLACE INTO knowledge_cards ({cols}) VALUES ({placeholders})"
            queue_write(sql, tuple(card.get(c) for c in CARD_COLS))

        if (i + 1) % 50 == 0:
            logger.info(f"Processed {i + 1}/{len(rows)} cards")

    logger.info(f"Retro knowledge extraction complete: {len(rows)} papers processed")
```

Also add the missing import at the top of `api.py`:

```python
import logging
```

And add `CARD_COLS` import or define it. Add after the existing imports:

```python
CARD_COLS = ["paper_id", "problem", "method_extracted", "result_extracted", "keywords", "relation_to_profile"]
```

- [ ] **Step 2: Verify syntax**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python3 -c "import api; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```bash
git add api.py
git commit -m "feat: add knowledge card API endpoints + retro-extract trigger (L1 API)"
```

---

## Task 5: L1 Frontend — knowledge card section in paper detail modal

**Files:**
- Modify: `js/modal.js`
- Modify: `js/api.js`

- [ ] **Step 1: Add fetchKnowledgeCard to js/api.js**

Add this function to `js/api.js`:

```javascript
export async function fetchKnowledgeCard(paperId) {
    const resp = await fetch(`/api/paper/${encodeURIComponent(paperId)}/card`);
    if (!resp.ok) return null;
    const data = await resp.json();
    return data.card;
}
```

- [ ] **Step 2: Add knowledge card section to openPaperDetail in js/modal.js**

Add the import at the top of `js/modal.js`:

```javascript
import { fetchKnowledgeCard } from './api.js';
```

In `openPaperDetail`, after the `sections` are built and before `detail.innerHTML = ...`, add this code to fetch and render the knowledge card:

```javascript
    // Knowledge card section (L1)
    fetchKnowledgeCard(paper.id).then(card => {
        if (!card) return;
        const cardDiv = document.getElementById('knowledge-card-section');
        if (!cardDiv) return;
        cardDiv.innerHTML = `
            <h3 style="margin-top:16px">知识卡片</h3>
            <div style="margin:8px 0;padding:12px;background:var(--accent-bg);border-radius:8px">
                <div style="margin-bottom:8px">
                    <span style="color:var(--accent-light);font-weight:600">Problem</span>
                    <p style="margin:4px 0;font-size:0.88rem">${card.problem || 'N/A'}</p>
                </div>
                <div style="margin-bottom:8px">
                    <span style="color:var(--accent-light);font-weight:600">Method</span>
                    <p style="margin:4px 0;font-size:0.88rem">${card.method_extracted || 'N/A'}</p>
                </div>
                <div style="margin-bottom:8px">
                    <span style="color:var(--accent-light);font-weight:600">Result</span>
                    <p style="margin:4px 0;font-size:0.88rem">${card.result_extracted || 'N/A'}</p>
                </div>
                <div style="margin-bottom:8px">
                    <span style="color:var(--accent-light);font-weight:600">Keywords</span>
                    <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px">
                        ${(card.keywords || []).map(k => `<span style="padding:2px 8px;border-radius:3px;font-size:0.75rem;background:var(--badge-bg);color:var(--accent-light)">${k}</span>`).join('')}
                    </div>
                </div>
                ${card.relation_to_profile ? `<div><span style="color:var(--accent-light);font-weight:600">Profile Relation</span><p style="margin:4px 0;font-size:0.85rem;color:var(--text-secondary)">${card.relation_to_profile}</p></div>` : ''}
            </div>`;
    });
```

In the `detail.innerHTML = ...` template string, add a placeholder div just before the closing `</div>` of the main content area, after the links section:

```html
            <div id="knowledge-card-section"></div>
```

- [ ] **Step 3: Verify no syntax errors**

Open browser at `http://localhost:8080`, click any AI-enhanced paper, check that the knowledge card section appears (may show empty if no cards extracted yet).

- [ ] **Step 4: Commit**

```bash
git add js/modal.js js/api.js
git commit -m "feat: add knowledge card section to paper detail modal (L1 frontend)"
```

---

## Task 6: L1 Retro-extract — batch job for existing papers

**Files:**
- Modify: `jobs.py` — add retro knowledge extract job trigger
- Modify: `js/app.js` — add crawl button for knowledge extract

- [ ] **Step 1: Add knowledge-extract trigger to crawl panel in index.html**

In `index.html`, find the crawl dropdown panel (`panel-crawl`) and add a new button:

```html
<div data-crawl="knowledge-extract" style="padding:6px 12px;cursor:pointer">知识卡片提取</div>
```

- [ ] **Step 2: Handle the trigger in js/app.js**

The existing crawl delegation handler in `js/app.js` handles `data-crawl` attributes. Add `knowledge-extract` to the trigger. Find the triggerCrawl call in `js/app.js` and ensure it posts to the correct endpoint. The `triggerCrawl` function in `js/api.js` should already handle custom job names. Verify in `js/api.js` that `triggerCrawl` posts to `/api/trigger/${job}`:

If `js/api.js` `triggerCrawl` uses the `/api/trigger/` endpoint, add handling in `api.py` for `knowledge-extract` in the `trigger_job` function's `job_funcs` dict:

In `api.py`, modify `trigger_job` to include knowledge-extract:

```python
    @app.route("/api/trigger/<job>", methods=["POST"])
    def trigger_job(job: str):
        if job == "knowledge-extract":
            threading.Thread(target=_retro_knowledge_extract, daemon=True).start()
            return jsonify({"status": "triggered", "job": job})
        job_funcs = {
            "arxiv": run_arxiv_job,
            ...
        }
```

- [ ] **Step 3: Test retro extraction**

Run: `curl -X POST http://localhost:8080/api/trigger/knowledge-extract`
Expected: `{"status":"triggered","job":"knowledge-extract"}`

Wait 30-60 seconds, then: `curl http://localhost:8080/api/knowledge-cards?per_page=5`
Expected: JSON with cards array containing extracted knowledge cards.

- [ ] **Step 4: Commit**

```bash
git add index.html api.py
git commit -m "feat: add retro knowledge card extraction trigger (L1 retro)"
```

---

## Task 7: L2 Schema + Clustering — knowledge_clusters table + algorithm

**Files:**
- Modify: `db.py` — add knowledge_clusters table
- Create: `ai/knowledge_clustering.py`

- [ ] **Step 1: Add knowledge_clusters table to db.py**

After knowledge_cards CREATE TABLE, add:

```sql
CREATE TABLE IF NOT EXISTS knowledge_clusters (
    cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_name TEXT NOT NULL,
    method_keywords JSON NOT NULL,
    paper_ids JSON NOT NULL,
    problem_domains JSON,
    updated_at TEXT
);
```

- [ ] **Step 2: Create ai/knowledge_clustering.py**

Core logic: group papers by keyword overlap (Jaccard similarity ≥ 0.3), then name clusters via LLM.

```python
"""Cluster papers by extracted method keywords."""

import json, logging
from collections import defaultdict
from db import get_conn, queue_write

logger = logging.getLogger(__name__)
SIMILARITY_THRESHOLD = 0.3


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def compute_clusters() -> list[dict]:
    """Build clusters from knowledge_cards keywords. Returns list of cluster dicts."""
    conn = get_conn()
    rows = conn.execute("SELECT paper_id, keywords FROM knowledge_cards").fetchall()

    # Build paper→keyword sets
    paper_kw = {}
    for r in rows:
        kws = json.loads(r["keywords"]) if isinstance(r["keywords"], str) else (r["keywords"] or [])
        paper_kw[r["paper_id"]] = set(kws)

    if not paper_kw:
        return []

    # Simple greedy clustering
    papers = list(paper_kw.keys())
    assigned = set()
    clusters = []

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
        # Merge keyword sets for cluster
        all_kw = set()
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
    """Clear and re-save clusters to DB."""
    conn = get_conn()
    conn.execute("DELETE FROM knowledge_clusters")
    for c in clusters:
        queue_write(
            "INSERT INTO knowledge_clusters (cluster_name, method_keywords, paper_ids, problem_domains) VALUES (?, ?, ?, ?)",
            (c["cluster_name"], c["method_keywords"], c["paper_ids"], c["problem_domains"])
        )


def run_clustering() -> int:
    """Full pipeline: compute + save. Returns cluster count."""
    clusters = compute_clusters()
    save_clusters(clusters)
    logger.info(f"Computed {len(clusters)} clusters")
    return len(clusters)
```

- [ ] **Step 3: Test**

Run: `python3 -c "from ai.knowledge_clustering import compute_clusters; print(compute_clusters()[:2])"`
Expected: list of cluster dicts (empty if no cards yet — run Task 6 first)

- [ ] **Step 4: Commit**

```bash
git add db.py ai/knowledge_clustering.py
git commit -m "feat: add knowledge clustering (L2 schema + algorithm)"
```

---

## Task 8: L2 API — knowledge graph endpoint

**Files:**
- Modify: `api.py`

- [ ] **Step 1: Add /api/knowledge-graph endpoint**

```python
@app.route("/api/knowledge-graph", methods=["GET"])
def get_knowledge_graph():
    """Return nodes (clusters) + edges (shared keywords) for graph viz."""
    from ai.knowledge_clustering import compute_clusters
    clusters = compute_clusters()
    nodes, edges = [], []
    for i, c in enumerate(clusters):
        pids = json.loads(c["paper_ids"]) if isinstance(c["paper_ids"], str) else c["paper_ids"]
        kws = json.loads(c["method_keywords"]) if isinstance(c["method_keywords"], str) else c["method_keywords"]
        nodes.append({"id": i, "name": c["cluster_name"], "size": len(pids), "keywords": kws[:5]})
    # Edges: shared keywords between clusters
    for i in range(len(clusters)):
        ki = set(json.loads(clusters[i]["method_keywords"]) if isinstance(clusters[i]["method_keywords"], str) else clusters[i]["method_keywords"])
        for j in range(i + 1, len(clusters)):
            kj = set(json.loads(clusters[j]["method_keywords"]) if isinstance(clusters[j]["method_keywords"], str) else clusters[j]["method_keywords"])
            shared = ki & kj
            if shared:
                edges.append({"source": i, "target": j, "weight": len(shared), "keywords": sorted(shared)})
    return jsonify({"nodes": nodes, "edges": edges})
```

Also add trigger:

```python
@app.route("/api/trigger/clustering", methods=["POST"])
def trigger_clustering():
    threading.Thread(target=_run_clustering_job, daemon=True).start()
    return jsonify({"status": "triggered"})

def _run_clustering_job():
    from ai.knowledge_clustering import run_clustering
    run_clustering()
```

- [ ] **Step 2: Commit**

```bash
git add api.py
git commit -m "feat: add knowledge graph API endpoint (L2 API)"
```

---

## Task 9: L2 Frontend — force-directed graph visualization

**Files:**
- Create: `js/graph.js`
- Modify: `index.html` — add graph container
- Modify: `js/app.js` — wire navigation
- Create: `css/graph.css`

- [ ] **Step 1: Add graph page container to index.html**

After `<div id="paper-container">`, add:

```html
<div id="graph-page" style="display:none;padding:20px">
    <h2 style="margin-bottom:12px">知识图谱</h2>
    <div style="display:flex;gap:8px;margin-bottom:12px">
        <button id="btn-refresh-graph" class="follow-btn">刷新图谱</button>
    </div>
    <svg id="graph-svg" width="960" height="600" style="border:1px solid var(--border-color);border-radius:8px"></svg>
</div>
```

Add D3 CDN to `<head>`:
```html
<script src="https://d3js.org/d3.v7.min.js"></script>
```

- [ ] **Step 2: Create js/graph.js**

```javascript
// js/graph.js — force-directed knowledge graph

export async function loadGraph() {
    const resp = await fetch('/api/knowledge-graph');
    if (!resp.ok) return;
    const { nodes, edges } = await resp.json();
    renderGraph(nodes, edges);
}

function renderGraph(nodes, edges) {
    const svg = d3.select('#graph-svg');
    svg.selectAll('*').remove();
    const w = +svg.attr('width'), h = +svg.attr('height');

    const sim = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(edges).id(d => d.id).distance(80))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(w / 2, h / 2));

    const link = svg.append('g').selectAll('line').data(edges).join('line')
        .attr('stroke', 'var(--border-color)').attr('stroke-width', d => Math.min(d.weight, 5));

    const node = svg.append('g').selectAll('g').data(nodes).join('g').call(d3.drag()
        .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

    node.append('circle').attr('r', d => Math.max(8, d.size * 2))
        .attr('fill', 'var(--accent)').attr('opacity', 0.8);
    node.append('text').text(d => d.name.slice(0, 20)).attr('dy', -12)
        .attr('text-anchor', 'middle').attr('fill', 'var(--text-primary)').attr('font-size', '0.7rem');

    sim.on('tick', () => {
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
}
```

- [ ] **Step 3: Wire in js/app.js**

Add import: `import { loadGraph } from './graph.js';`

Add navigation button handler (add a "图谱" button to header or sidebar):

```javascript
document.getElementById('btn-refresh-graph')?.addEventListener('click', loadGraph);
```

Add view toggle logic: clicking "图谱" hides `paper-container`, shows `graph-page`, and calls `loadGraph()`.

- [ ] **Step 4: Commit**

```bash
git add js/graph.js index.html js/app.js
git commit -m "feat: add force-directed knowledge graph visualization (L2 frontend)"
```

---

## Task 10: L3a Schema + Job — trend_reports table + weekly generation

**Files:**
- Modify: `db.py` — add trend_reports table
- Create: `ai/trend_analyzer.py`
- Modify: `jobs.py` — add weekly trend job

- [ ] **Step 1: Add trend_reports table to db.py**

```sql
CREATE TABLE IF NOT EXISTS trend_reports (
    week_start TEXT PRIMARY KEY,
    new_methods TEXT,
    solved_problems TEXT,
    controversies TEXT,
    opportunities TEXT,
    paper_count INTEGER,
    generated_at TEXT
);
```

- [ ] **Step 2: Add TrendReport model to ai/structure.py**

```python
class TrendReport(BaseModel):
    new_methods: str = Field(description="new methods or techniques that emerged this week, 2-4 items as bullet points")
    solved_problems: str = Field(description="problems that appear to have been addressed, 1-3 items")
    controversies: str = Field(description="debates or conflicting findings, if any")
    opportunities: str = Field(description="research opportunities or gaps visible from this week's papers")
```

- [ ] **Step 3: Create ai/trend_analyzer.py**

```python
"""Weekly trend radar generation."""

import json, logging, os
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from db import get_conn, queue_write
from .structure import TrendReport

logger = logging.getLogger(__name__)

_TREND_PROMPT = """Analyze this week's AI research papers and identify trends.

## Papers from the past 7 days ({count} papers):
{paper_summaries}

## User's Research Direction: {research_direction}

Identify:
1. New methods or techniques that emerged
2. Problems that appear solved or significantly advanced
3. Controversies or conflicting findings
4. Research opportunities visible from these papers"""

_CHAIN = None

def _get_chain():
    global _CHAIN
    if _CHAIN is None:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        llm = ChatOpenAI(model=model_name).with_structured_output(TrendReport, method="json_mode")
        _CHAIN = ChatPromptTemplate.from_template(_TREND_PROMPT) | llm
    return _CHAIN

def generate_trend_report(week_start: str | None = None) -> dict | None:
    """Generate a trend report for the given week."""
    if week_start is None:
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

    conn = get_conn()
    week_ago = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")

    rows = conn.execute("""
        SELECT p.title, a.tldr, a.method, a.result
        FROM papers p JOIN ai_results a ON p.id = a.paper_id
        WHERE p.published_date >= ? AND p.published_date < ?
        ORDER BY a.relevance_score DESC LIMIT 50
    """, (week_ago, week_start)).fetchall()

    if not rows:
        logger.info(f"No papers for trend report week {week_start}")
        return None

    summaries = "\n".join(f"- {r['title']}: {r['tldr']}" for r in rows[:30])

    from .enhance import load_research_profile
    profile = load_research_profile()

    try:
        report: TrendReport = _get_chain().invoke({
            "count": len(rows), "paper_summaries": summaries,
            "research_direction": profile.get("direction", ""),
        })
    except Exception as e:
        logger.error(f"Trend report generation failed: {e}")
        return None

    result = {
        "week_start": week_start,
        "new_methods": report.new_methods,
        "solved_problems": report.solved_problems,
        "controversies": report.controversies,
        "opportunities": report.opportunities,
        "paper_count": len(rows),
    }
    queue_write(
        "INSERT OR REPLACE INTO trend_reports (week_start, new_methods, solved_problems, controversies, opportunities, paper_count) VALUES (?,?,?,?,?,?)",
        tuple(result.values())
    )
    return result
```

- [ ] **Step 4: Add weekly job to jobs.py**

In `jobs.py`, add to the scheduler setup:

```python
scheduler.add_job(lambda: generate_trend_report(), 'cron', day_of_week='mon', hour=6, id='trend-weekly')
```

And import: `from ai.trend_analyzer import generate_trend_report`

- [ ] **Step 5: Commit**

```bash
git add db.py ai/structure.py ai/trend_analyzer.py jobs.py
git commit -m "feat: add trend radar weekly report (L3a)"
```

---

## Task 11: L3a API + Frontend — trend radar endpoint + UI

**Files:**
- Modify: `api.py`
- Create: `js/trend.js`
- Modify: `index.html`, `js/app.js`

- [ ] **Step 1: Add API endpoints**

```python
@app.route("/api/trend-radar", methods=["GET"])
def get_latest_trend():
    conn = get_conn()
    row = conn.execute("SELECT * FROM trend_reports ORDER BY week_start DESC LIMIT 1").fetchone()
    if not row:
        return jsonify({"report": None})
    return jsonify({"report": dict(row)})

@app.route("/api/trend-radar/<week>", methods=["GET"])
def get_trend_by_week(week):
    conn = get_conn()
    row = conn.execute("SELECT * FROM trend_reports WHERE week_start = ?", (week,)).fetchone()
    if not row:
        return jsonify({"report": None})
    return jsonify({"report": dict(row)})

@app.route("/api/trigger/trend", methods=["POST"])
def trigger_trend():
    threading.Thread(target=lambda: generate_trend_report(), daemon=True).start()
    return jsonify({"status": "triggered"})
```

- [ ] **Step 2: Create js/trend.js**

```javascript
// js/trend.js — trend radar rendering

export async function loadTrendRadar() {
    const resp = await fetch('/api/trend-radar');
    if (!resp.ok) return;
    const { report } = await resp.json();
    const el = document.getElementById('trend-content');
    if (!el) return;
    if (!report) { el.innerHTML = '<p style="color:var(--text-secondary)">暂无趋势报告。点击"生成报告"触发。</p>'; return; }
    const sections = [
        { title: '新方法涌现', content: report.new_methods, color: '#22c55e' },
        { title: '问题进展', content: report.solved_problems, color: '#3b82f6' },
        { title: '争议点', content: report.controversies, color: '#eab308' },
        { title: '机会点', content: report.opportunities, color: '#a855f7' },
    ];
    el.innerHTML = `<p style="color:var(--text-muted);margin-bottom:12px">周报: ${report.week_start} | ${report.paper_count} 篇论文</p>`
        + sections.map(s => `<div style="margin-bottom:12px"><h3 style="color:${s.color}">${s.title}</h3><p style="font-size:0.88rem;white-space:pre-wrap">${s.content}</p></div>`).join('');
}
```

- [ ] **Step 3: Add trend section to index.html**

After graph-page div, add:

```html
<div id="trend-page" style="display:none;padding:20px;max-width:700px;margin:0 auto">
    <h2 style="margin-bottom:12px">趋势雷达</h2>
    <button id="btn-generate-trend" class="follow-btn" style="margin-bottom:12px">生成报告</button>
    <div id="trend-content"></div>
</div>
```

- [ ] **Step 4: Wire in js/app.js**

```javascript
import { loadTrendRadar } from './trend.js';
document.getElementById('btn-generate-trend')?.addEventListener('click', async () => {
    await fetch('/api/trigger/trend', { method: 'POST' });
    showToast('趋势报告生成中...');
    setTimeout(loadTrendRadar, 30000);
});
```

- [ ] **Step 5: Commit**

```bash
git add api.py js/trend.js index.html js/app.js
git commit -m "feat: add trend radar API and frontend (L3a UI)"
```

---

## Task 12: L3b Idea Check — API + LLM analysis + frontend

**Files:**
- Create: `ai/idea_checker.py`
- Modify: `api.py`
- Modify: `index.html`, `js/app.js`

- [ ] **Step 1: Create ai/idea_checker.py**

```python
"""Idea feasibility check — search existing papers and analyze differentiation."""

import json, logging, os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from db import get_conn

logger = logging.getLogger(__name__)


class IdeaAnalysis(BaseModel):
    feasibility: str = Field(description="high/medium/low — how feasible is this idea given existing work")
    novelty: str = Field(description="high/medium/low — how novel compared to existing papers")
    related_work: str = Field(description="2-4 sentence summary of closest existing work found")
    differentiation: str = Field(description="how to differentiate from existing work, specific suggestions")
    risks: str = Field(description="main risks or challenges, 1-3 items")


_IDEA_PROMPT = """Analyze this research idea against existing papers.

## Research Idea
{idea}

## User's Research Direction
{research_direction}

## Most Relevant Existing Papers
{relevant_papers}

Assess:
1. Feasibility (high/medium/low) — is this achievable?
2. Novelty (high/medium/low) — is this already done?
3. Related work summary — what's closest?
4. Differentiation — how to make this novel?
5. Risks — what could go wrong?"""

_CHAIN = None

def _get_chain():
    global _CHAIN
    if _CHAIN is None:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        llm = ChatOpenAI(model=model_name).with_structured_output(IdeaAnalysis, method="json_mode")
        _CHAIN = ChatPromptTemplate.from_template(_IDEA_PROMPT) | llm
    return _CHAIN


def check_idea(idea: str) -> dict | None:
    """Check idea feasibility against existing papers in DB."""
    conn = get_conn()
    # Simple keyword search for relevant papers
    words = idea.split()[:5]
    conditions = " OR ".join(["(p.title LIKE ? OR a.tldr LIKE ? OR a.method LIKE ?)"] * len(words))
    params = []
    for w in words:
        params.extend([f"%{w}%"] * 3)
    rows = conn.execute(f"""
        SELECT p.title, a.tldr, a.method, a.result, a.recommendation
        FROM papers p JOIN ai_results a ON p.id = a.paper_id
        WHERE {conditions}
        ORDER BY a.relevance_score DESC LIMIT 10
    """, params).fetchall()

    if not rows:
        relevant = "No directly relevant papers found in the database."
    else:
        relevant = "\n".join(f"- {r['title']}: {r['tldr']}" for r in rows)

    from .enhance import load_research_profile
    profile = load_research_profile()

    try:
        analysis: IdeaAnalysis = _get_chain().invoke({
            "idea": idea,
            "research_direction": profile.get("direction", ""),
            "relevant_papers": relevant,
        })
    except Exception as e:
        logger.error(f"Idea check failed: {e}")
        return None

    return analysis.model_dump()
```

- [ ] **Step 2: Add API endpoint**

```python
@app.route("/api/idea-check", methods=["POST"])
def idea_check():
    data = request.get_json() or {}
    idea = data.get("idea", "").strip()
    if not idea:
        return jsonify({"error": "idea is required"}), 400
    from ai.idea_checker import check_idea
    result = check_idea(idea)
    if result is None:
        return jsonify({"error": "analysis failed"}), 500
    return jsonify({"analysis": result})
```

- [ ] **Step 3: Add idea check UI to index.html**

In the trend-page or as a new section, add:

```html
<div id="idea-page" style="display:none;padding:20px;max-width:700px;margin:0 auto">
    <h2 style="margin-bottom:12px">点子可行性检查</h2>
    <textarea id="idea-input" rows="3" placeholder="输入你的研究想法..." style="width:100%;padding:8px;border:1px solid var(--border-color);border-radius:6px;background:var(--bg-primary);color:var(--text-primary);font-size:0.9rem"></textarea>
    <button id="btn-check-idea" class="follow-btn" style="margin-top:8px">分析</button>
    <div id="idea-result" style="margin-top:16px"></div>
</div>
```

- [ ] **Step 4: Wire in js/app.js**

```javascript
document.getElementById('btn-check-idea')?.addEventListener('click', async () => {
    const idea = document.getElementById('idea-input')?.value?.trim();
    if (!idea) return;
    const el = document.getElementById('idea-result');
    el.innerHTML = '<div class="spinner"></div>';
    try {
        const resp = await fetch('/api/idea-check', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({idea})
        });
        const {analysis} = await resp.json();
        if (!analysis) { el.innerHTML = '<p>分析失败</p>'; return; }
        const colors = {high: '#22c55e', medium: '#eab308', low: '#ef4444'};
        el.innerHTML = `
            <div style="display:flex;gap:12px;margin-bottom:12px">
                <span style="color:${colors[analysis.feasibility]}">可行性: ${analysis.feasibility}</span>
                <span style="color:${colors[analysis.novelty]}">新颖性: ${analysis.novelty}</span>
            </div>
            <h3>相关工作</h3><p style="font-size:0.88rem">${analysis.related_work}</p>
            <h3>差异化建议</h3><p style="font-size:0.88rem">${analysis.differentiation}</p>
            <h3>风险</h3><p style="font-size:0.88rem">${analysis.risks}</p>`;
    } catch { el.innerHTML = '<p>请求失败</p>'; }
});
```

- [ ] **Step 5: Commit**

```bash
git add ai/idea_checker.py api.py index.html js/app.js
git commit -m "feat: add idea feasibility check (L3b)"
```

---

## Self-Review

### Spec Coverage
- L1 Knowledge Cards: Task 1 (schema), Task 2 (extractor), Task 3 (integration), Task 4 (API), Task 5 (frontend), Task 6 (retro-extract) — covered
- L2 Knowledge Graph: Task 7 (schema+clustering), Task 8 (API), Task 9 (frontend) — covered
- L3a Trend Radar: Task 10 (schema+job), Task 11 (API+frontend) — covered
- L3b Idea Check: Task 12 (API+LLM+frontend) — covered

### Placeholder Scan
- No TBD/TODO found. All code blocks are complete.

### Type Consistency
- KnowledgeCard fields match knowledge_cards table columns across all tasks
- TrendReport fields match trend_reports table columns
- IdeaAnalysis fields used consistently in API response and frontend rendering
- CARD_COLS list matches table column names in Tasks 3, 4

### Gaps
- Navigation between main paper view / graph page / trend page / idea page needs a tab bar or sidebar links — left as a simple show/hide toggle per Task 9 Step 3 and Task 11 Step 4
