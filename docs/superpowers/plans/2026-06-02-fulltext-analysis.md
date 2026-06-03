# Full-Text Analysis Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full-text analysis for high-quality papers: fetch arXiv HTML via ar5iv.org, extract structured content, run deep LLM analysis (method implementation + experimental design + limitations).

**Architecture:** Two-stage pipeline: (1) fetch HTML and extract clean text sections, (2) run deep LLM analysis on extracted content. Only triggered for `must-read` + `recommended` papers. Results stored in new `fulltext_analysis` table alongside existing `ai_results`.

**Tech Stack:** Python 3.12, httpx (HTML fetch), BeautifulSoup (HTML parsing), LangChain (LLM analysis), SQLite

**Trigger scope:** ~100 papers (68 must-read + 32 recommended) out of 872 total. Only arXiv-source papers have HTML available via ar5iv; other sources skip fulltext.

---

## File Structure

| File | Role | Task |
|:-----|:-----|:-----|
| `ai/fulltext_fetcher.py` | HTML fetch + text extraction from ar5iv | T1 (new) |
| `ai/fulltext_analyzer.py` | Deep LLM analysis of full text | T2 (new) |
| `ai/structure.py` | Pydantic models | T2 (add FulltextAnalysis model) |
| `db.py` | Schema + write queue | T2 (add fulltext_analysis table) |
| `api.py` | REST endpoints | T3 (trigger + query endpoints) |
| `jobs.py` | Post-crawl pipeline | T3 (add fulltext to post-crawl) |
| `js/modal.js` | Detail modal | T3 (show fulltext analysis) |

---

### Task 1: arXiv HTML Fetcher + Text Extractor

**Problem:** Need to download and parse arXiv paper HTML from ar5iv.org, extracting clean section text (Introduction, Method, Experiments, Conclusion, Limitations) suitable for LLM analysis.

**Files:**
- Create: `ai/fulltext_fetcher.py`

- [ ] **Step 1: Create fulltext_fetcher.py with HTML fetch function**

```python
"""Fetch and extract full text from arXiv papers via ar5iv.org."""
from __future__ import annotations

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

AR5IV_BASE = "https://ar5iv.org/html/"
AR5IV_LATEX_BASE = "https://ar5iv.org/abs/"


def fetch_arxiv_html(arxiv_id: str, timeout: int = 30) -> Optional[str]:
    """Fetch HTML content of an arXiv paper from ar5iv.org.

    Returns raw HTML string, or None on failure.
    """
    url = f"{AR5IV_BASE}{arxiv_id}"
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
        logger.warning(f"ar5iv returned {resp.status_code} for {arxiv_id}")
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch ar5iv HTML for {arxiv_id}: {e}")
        return None
```

- [ ] **Step 2: Add section extraction function**

Append to `ai/fulltext_fetcher.py`:

```python
# Section name patterns for extraction
_SECTION_PATTERNS = [
    (r"\bintroduction\b", "introduction"),
    (r"\bmethod(s|ology)?\b", "method"),
    (r"\bapproach\b", "method"),
    (r"\bexperiment(s|al)?\b", "experiments"),
    (r"\bevaluation\b", "experiments"),
    (r"\bresult(s)?\b", "experiments"),
    (r"\bconclusion(s)?\b", "conclusion"),
    (r"\bdiscussion\b", "conclusion"),
    (r"\blimitation(s)?\b", "limitations"),
    (r"\bfuture work\b", "limitations"),
]


def _classify_heading(text: str) -> Optional[str]:
    """Map a heading text to a section category."""
    lower = text.lower().strip()
    for pattern, category in _SECTION_PATTERNS:
        if re.search(pattern, lower):
            return category
    return None


def extract_sections(html: str) -> dict[str, str]:
    """Extract paper sections from ar5iv HTML.

    Returns dict mapping section names to their text content:
    {"introduction": "...", "method": "...", "experiments": "...",
     "conclusion": "...", "limitations": "..."}
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove style, script, and math elements (keep text)
    for tag in soup.find_all(["style", "script", "math", "svg"]):
        tag.decompose()

    sections: dict[str, list[str]] = {}
    current_section: Optional[str] = None
    current_text: list[str] = []

    # Walk through all elements in document order
    for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol"]):
        if element.name in ("h1", "h2", "h3", "h4"):
            # Save previous section
            if current_section and current_text:
                sections.setdefault(current_section, []).append(" ".join(current_text))
                current_text = []

            # Classify new heading
            heading_text = element.get_text(strip=True)
            current_section = _classify_heading(heading_text)
            continue

        if current_section is None:
            continue

        text = element.get_text(strip=True)
        if text and len(text) > 20:
            current_text.append(text)

    # Save last section
    if current_section and current_text:
        sections.setdefault(current_section, []).append(" ".join(current_text))

    # Merge lists into single strings, truncate to ~4000 chars per section
    result = {}
    for name, texts in sections.items():
        combined = " ".join(texts)
        if len(combined) > 4000:
            combined = combined[:4000]
        if combined:
            result[name] = combined

    return result
```

- [ ] **Step 3: Add high-level fetch_and_extract function**

Append to `ai/fulltext_fetcher.py`:

```python
def fetch_and_extract(arxiv_id: str) -> Optional[dict[str, str]]:
    """Fetch arXiv HTML and extract structured sections.

    Returns section dict or None if fetch/parse fails.
    """
    html = fetch_arxiv_html(arxiv_id)
    if html is None:
        return None
    sections = extract_sections(html)
    if not sections:
        logger.warning(f"No sections extracted for {arxiv_id}")
        return None
    logger.debug(f"Extracted {len(sections)} sections for {arxiv_id}: {list(sections.keys())}")
    return sections
```

- [ ] **Step 4: Test with a real arXiv paper**

```bash
cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python -c "
from ai.fulltext_fetcher import fetch_and_extract
result = fetch_and_extract('2401.00123')
if result:
    for k, v in result.items():
        print(f'{k}: {len(v)} chars')
else:
    print('Failed to fetch')
"
```

Expected: sections dict with method/experiments/etc keys, each with non-empty text.

- [ ] **Step 5: Commit**

```bash
git add ai/fulltext_fetcher.py
git commit -m "feat: arXiv HTML fetcher and section extractor via ar5iv.org"
```

---

### Task 2: Deep Full-Text Analysis + DB Storage

**Problem:** Need a deep LLM analysis that goes beyond abstract-level assessment. For must-read/recommended papers, analyze the full method implementation, experimental design, and limitations using extracted section text.

**Files:**
- Create: `ai/fulltext_analyzer.py`
- Modify: `ai/structure.py` (add FulltextAnalysis model)
- Modify: `db.py` (add fulltext_analysis table)

- [ ] **Step 1: Add FulltextAnalysis Pydantic model to ai/structure.py**

Append after the `TrendReport` class (ensure `ConfigDict` is already imported from pydantic — it was added in the KnowledgeCard fix):

```python
class FulltextAnalysis(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    method_implementation: str = Field(description="detailed description of how the method works: architecture, key algorithms, training procedure, design choices. 2-3 sentences", alias="MethodImplementation")
    experimental_design: str = Field(description="experimental setup: datasets, baselines, metrics, evaluation protocol, ablation studies. 2-3 sentences", alias="ExperimentalDesign")
    key_results_detail: str = Field(description="specific quantitative results: numbers, comparisons, state-of-the-art achievements. 2-3 sentences", alias="KeyResults")
    limitations: str = Field(description="stated or inferred limitations: assumptions, scalability issues, domain restrictions, negative results. 1-2 sentences", alias="Limitations")
    reproducibility: str = Field(description="reproducibility assessment: code available, hyperparameters specified, datasets accessible. 1 sentence", alias="Reproducibility")
    relevance_to_profile: str = Field(description="specific relevance to user's research: which techniques could transfer, what gaps this fills, potential collaborations. 1-2 sentences", alias="RelevanceToProfile")
```

- [ ] **Step 2: Add fulltext_analysis table to db.py**

In `db.py`, add the new table after the `knowledge_clusters` CREATE TABLE:

```python
        CREATE TABLE IF NOT EXISTS fulltext_analysis (
            paper_id TEXT PRIMARY KEY,
            method_implementation TEXT,
            experimental_design TEXT,
            key_results_detail TEXT,
            limitations TEXT,
            reproducibility TEXT,
            relevance_to_profile TEXT,
            analyzed_at TEXT,
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
        );
```

- [ ] **Step 3: Run ALTER TABLE on existing DB**

```bash
sqlite3 data/papers.db "CREATE TABLE IF NOT EXISTS fulltext_analysis (paper_id TEXT PRIMARY KEY, method_implementation TEXT, experimental_design TEXT, key_results_detail TEXT, limitations TEXT, reproducibility TEXT, relevance_to_profile TEXT, analyzed_at TEXT, FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE);"
```

- [ ] **Step 4: Create ai/fulltext_analyzer.py**

```python
"""Deep full-text analysis for high-quality papers."""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .structure import FulltextAnalysis
from .fulltext_fetcher import fetch_and_extract
from .enhance import load_research_profile

logger = logging.getLogger(__name__)

_FULLTEXT_PROMPT = """You are a research paper analyst performing deep analysis of a paper's full text.

## Researcher Profile
Direction: {research_direction}
Keywords: {keywords}

## Paper Title
{title}

## Abstract
{abstract}

## Full Text Sections
{sections_text}

Analyze this paper's full text in detail. Focus on:
1. **Method Implementation**: How exactly does the method work? Architecture, algorithms, training procedure.
2. **Experimental Design**: Datasets, baselines, metrics, ablation studies, evaluation protocol.
3. **Key Results**: Specific quantitative results, comparisons with baselines, state-of-the-art achievements.
4. **Limitations**: Stated or inferred limitations, assumptions, scalability issues, negative results.
5. **Reproducibility**: Is code available? Are hyperparameters specified? Are datasets accessible?
6. **Relevance to Profile**: Which techniques could transfer to the user's research? What gaps does this fill?

Respond with valid JSON using these exact keys: "method_implementation", "experimental_design", "key_results_detail", "limitations", "reproducibility", "relevance_to_profile"."""

_CHAIN = None


def _get_chain():
    global _CHAIN
    if _CHAIN is None:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        llm = ChatOpenAI(model=model_name).with_structured_output(FulltextAnalysis, method="json_mode")
        _CHAIN = ChatPromptTemplate.from_template(_FULLTEXT_PROMPT) | llm
    return _CHAIN


def analyze_fulltext(paper: dict, profile: dict | None = None) -> Optional[dict]:
    """Fetch full text and run deep analysis for a paper.

    Only works for arXiv papers (ar5iv HTML available).
    Returns analysis dict or None if fetch/analysis fails.
    """
    source = paper.get("source", "")
    arxiv_id = paper.get("id", "")

    if source != "arxiv":
        logger.debug(f"Skipping fulltext for non-arXiv paper {arxiv_id} (source={source})")
        return None

    sections = fetch_and_extract(arxiv_id)
    if not sections:
        logger.warning(f"No sections extracted for {arxiv_id}")
        return None

    # Format sections for prompt
    sections_text = ""
    for name, text in sections.items():
        sections_text += f"### {name.title()}\n{text}\n\n"

    # Truncate to ~8000 chars to control token cost
    if len(sections_text) > 8000:
        sections_text = sections_text[:8000]

    if profile is None:
        profile = load_research_profile()

    chain = _get_chain()

    try:
        result: FulltextAnalysis = chain.invoke({
            "title": paper.get("title", ""),
            "abstract": paper.get("summary", ""),
            "sections_text": sections_text,
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
        })
    except Exception as e:
        logger.error(f"Fulltext analysis failed for {arxiv_id}: {e}")
        return None

    return {
        "paper_id": arxiv_id,
        "method_implementation": result.method_implementation,
        "experimental_design": result.experimental_design,
        "key_results_detail": result.key_results_detail,
        "limitations": result.limitations,
        "reproducibility": result.reproducibility,
        "relevance_to_profile": result.relevance_to_profile,
    }
```

- [ ] **Step 5: Commit**

```bash
git add ai/fulltext_analyzer.py ai/structure.py db.py
git commit -m "feat: deep fulltext analysis with method/experiments/limitations extraction"
```

---

### Task 3: API Integration + Post-Crawl Pipeline + Frontend Display

**Problem:** Need to integrate fulltext analysis into the existing pipeline: trigger endpoint for retro-analysis, automatic trigger after arxiv crawl, and frontend display in detail modal.

**Files:**
- Modify: `api.py` (add trigger + query endpoints)
- Modify: `paper_store.py` (add fulltext analysis to append_paper flow)
- Modify: `jobs.py` (add fulltext analysis to post-crawl)
- Modify: `js/modal.js` (show fulltext analysis section)
- Modify: `js/api.js` (add fetchFulltextAnalysis function)

- [ ] **Step 1: Add fulltext_analysis_cols to paper_store.py**

In `paper_store.py`, add a column definition list after `CARD_COLS`:

```python
FULLTEXT_COLS = [
    "paper_id", "method_implementation", "experimental_design",
    "key_results_detail", "limitations", "reproducibility",
    "relevance_to_profile",
]
```

Then add an insert function:

```python
def _insert_fulltext_analysis(paper_id: str, analysis: dict) -> None:
    cols = ", ".join(FULLTEXT_COLS + ["analyzed_at"])
    placeholders = ", ".join(f":{c}" for c in FULLTEXT_COLS) + ", datetime('now')"
    sql = f"INSERT OR REPLACE INTO fulltext_analysis ({cols}) VALUES ({placeholders})"
    queue_write(sql, tuple(analysis.get(c) for c in FULLTEXT_COLS))
```

- [ ] **Step 2: Add fulltext analysis trigger to append_paper in paper_store.py**

In `paper_store.py`, modify the `append_paper` function. After the knowledge card insertion block (after `_insert_knowledge_card`), add fulltext analysis for must-read/recommended papers:

```python
                try:
                    _insert_knowledge_card(paper_id, enhanced)
                except Exception as e:
                    logger.warning(f"Knowledge card failed for {paper.id}: {e}")
                # Fulltext analysis for must-read/recommended papers
                if ai_data.get("recommendation") in ("must-read", "recommended"):
                    try:
                        from ai.fulltext_analyzer import analyze_fulltext
                        ft_result = analyze_fulltext(paper_dict, profile)
                        if ft_result:
                            _insert_fulltext_analysis(paper.id, ft_result)
                            logger.debug(f"Fulltext analysis done for {paper.id}")
                    except Exception as e:
                        logger.warning(f"Fulltext analysis failed for {paper.id}: {e}")
```

- [ ] **Step 3: Add retro fulltext analysis trigger in api.py**

In `api.py`, add a trigger endpoint after the knowledge-extract trigger:

```python
@app.route("/api/trigger/fulltext-analyze", methods=["POST"])
def trigger_fulltext_analyze():
    """Retro-analyze must-read/recommended papers that lack fulltext analysis."""
    threading.Thread(target=_retro_fulltext_analyze, daemon=True).start()
    return jsonify({"status": "triggered", "job": "fulltext-analyze"})


def _retro_fulltext_analyze():
    from ai.fulltext_analyzer import analyze_fulltext
    from ai.enhance import load_research_profile

    conn = get_conn()
    profile = load_research_profile()
    rows = conn.execute("""
        SELECT a.paper_id, a.tldr, a.motivation, a.method, a.result, a.conclusion,
               p.title, p.summary, p.source, p.id
        FROM ai_results a JOIN papers p ON a.paper_id = p.id
        LEFT JOIN fulltext_analysis ft ON a.paper_id = ft.paper_id
        WHERE ft.paper_id IS NULL AND a.recommendation IN ('must-read', 'recommended')
              AND p.source = 'arxiv'
    """).fetchall()

    logger = logging.getLogger("fulltext-analyze")
    logger.info(f"Retro fulltext analysis: {len(rows)} papers to process")

    analyzed = 0
    for i, row in enumerate(rows):
        paper = {
            "id": row["id"], "source": row["source"],
            "title": row["title"], "summary": row["summary"],
            "AI": {"tldr": row["tldr"], "motivation": row["motivation"],
                   "method": row["method"], "result": row["result"], "conclusion": row["conclusion"]},
        }
        result = analyze_fulltext(paper, profile)
        if result:
            queue_write(
                "INSERT OR REPLACE INTO fulltext_analysis (paper_id, method_implementation, experimental_design, key_results_detail, limitations, reproducibility, relevance_to_profile, analyzed_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (result["paper_id"], result["method_implementation"], result["experimental_design"],
                 result["key_results_detail"], result["limitations"], result["reproducibility"],
                 result["relevance_to_profile"]),
            )
            analyzed += 1
        if (i + 1) % 10 == 0:
            logger.info(f"Processed {i + 1}/{len(rows)} ({analyzed} analyzed)")

    logger.info(f"Retro fulltext analysis complete: {analyzed}/{len(rows)}")
```

- [ ] **Step 4: Add fulltext query endpoint in api.py**

```python
@app.route("/api/paper/<paper_id>/fulltext", methods=["GET"])
def get_paper_fulltext(paper_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM fulltext_analysis WHERE paper_id = ?", (paper_id,)).fetchone()
    if row is None:
        return jsonify({"analysis": None})
    return jsonify({"analysis": dict(row)})
```

- [ ] **Step 5: Add fetchFulltextAnalysis to js/api.js**

In `js/api.js`, add a new function:

```javascript
export async function fetchFulltextAnalysis(paperId) {
    try {
        const resp = await fetch(`/api/paper/${paperId}/fulltext`);
        if (resp.ok) {
            const data = await resp.json();
            return data.analysis || null;
        }
    } catch (e) {
        console.error('Failed to fetch fulltext analysis:', e);
    }
    return null;
}
```

- [ ] **Step 6: Add fulltext analysis display in js/modal.js**

In `openPaperDetail`, after the knowledge card section (`<div id="knowledge-card-section"></div>`), add a fulltext analysis section:

```javascript
            <div id="fulltext-analysis-section"></div>
```

Then after the knowledge card fetch logic (after the `fetchKnowledgeCard` call block), add fulltext analysis fetch:

```javascript
    fetchFulltextAnalysis(paper.id).then(analysis => {
        if (!analysis) return;
        const el = document.getElementById('fulltext-analysis-section');
        if (!el) return;
        el.innerHTML = `
            <h3 style="margin-top:16px">正文深度分析</h3>
            <div style="margin:8px 0;padding:12px;background:var(--accent-bg);border-radius:8px">
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">方法实现</span><p style="margin:4px 0;font-size:0.88rem">${analysis.method_implementation || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">实验设计</span><p style="margin:4px 0;font-size:0.88rem">${analysis.experimental_design || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">关键结果</span><p style="margin:4px 0;font-size:0.88rem">${analysis.key_results_detail || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">局限性</span><p style="margin:4px 0;font-size:0.88rem">${analysis.limitations || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">可复现性</span><p style="margin:4px 0;font-size:0.88rem">${analysis.reproducibility || 'N/A'}</p></div>
                ${analysis.relevance_to_profile ? `<div><span style="color:var(--accent-light);font-weight:600">与研究方向的关系</span><p style="margin:4px 0;font-size:0.85rem;color:var(--text-secondary)">${analysis.relevance_to_profile}</p></div>` : ''}
            </div>`;
    });
```

Add `fetchFulltextAnalysis` to the import from api.js.

- [ ] **Step 7: Add fulltext analysis to post-crawl pipeline in jobs.py**

In `jobs.py`, modify the `_run_and_reschedule` method. After the knowledge extract block, add fulltext analysis:

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
                from api import _retro_fulltext_analyze
                _retro_fulltext_analyze()
            except Exception as e:
                logger.error(f"Fulltext analyze after arxiv error: {e}")
            try:
                run_digest_job()
            except Exception as e:
                logger.error(f"Digest after arxiv error: {e}")
```

- [ ] **Step 8: Commit**

```bash
git add api.py paper_store.py jobs.py js/modal.js js/api.js
git commit -m "feat: fulltext analysis API, pipeline integration, and frontend display"
```
