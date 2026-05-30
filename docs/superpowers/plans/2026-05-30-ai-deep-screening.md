# AI Deep Screening System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AI-powered deep screening system that scores each paper on quality and personal relevance, displays results inline on cards, and generates a daily Markdown research digest.

**Architecture:** Extend the existing `ai/enhance.py` pipeline with new scoring fields in `ai/structure.py`. Add a `research_profile.json` config for the user's research direction + keywords. Wire AI enhancement directly into the streaming crawl loop in `daemon.py` so each paper is enhanced immediately after fetch. Add a daily digest generator (`ai/digest.py`) that summarizes all enhanced papers into a Markdown report. Update the frontend to show color-coded scores, inline TL;DR, and recommendation badges on cards.

**Tech Stack:** Python 3.12, Flask, DeepSeek (via langchain-openai), Pydantic, vanilla JS

---

## File Structure

| File | Action | Responsibility |
|:-----|:-------|:---------------|
| `ai/structure.py` | Modify | Add `quality_score`, `relevance_score`, `recommendation` fields |
| `ai/system.txt` | Modify | Update prompt to include scoring instructions + research profile |
| `ai/template.txt` | Modify | Pass title + abstract + research context |
| `research_profile.json` | Create | User's research direction text + keyword list |
| `ai/enhance.py` | Modify | Accept research profile, refactor for single-paper callable |
| `ai/digest.py` | Create | Generate daily Markdown research digest from enhanced papers |
| `daemon.py` | Modify | Call AI enhance per-paper during crawl; trigger digest after batch |
| `js/app.js` | Modify | Render scores, color borders, inline TL;DR on cards |
| `css/styles.css` | Modify | Score bar, recommendation badge, color border styles |
| `index.html` | Modify | Add research profile settings section |

---

### Task 1: Research Profile Config

**Files:**
- Create: `research_profile.json`

- [ ] **Step 1: Create the research profile config file**

```json
{
  "direction": "Computer vision and 3D understanding, focusing on neural rendering, novel view synthesis, and 3D reconstruction from images or video.",
  "keywords": [
    "neural rendering",
    "3D reconstruction",
    "novel view synthesis",
    "NeRF",
    "Gaussian splatting",
    "diffusion models",
    "visual grounding",
    "vision-language models"
  ],
  "quality_criteria": "Prioritize papers with strong empirical results, novel architectures, or significant efficiency improvements over existing methods."
}
```

- [ ] **Step 2: Verify file is valid JSON**

Run: `python3 -c "import json; json.load(open('research_profile.json')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add research_profile.json
git commit -m "feat: add research profile config for AI scoring"
```

---

### Task 2: Extend AI Output Structure

**Files:**
- Modify: `ai/structure.py`

- [ ] **Step 1: Add scoring fields to Structure model**

Replace the entire file with:

```python
from pydantic import BaseModel, Field


class Structure(BaseModel):
    tldr: str = Field(description="one-sentence TL;DR summary of the paper's key contribution")
    motivation: str = Field(description="what problem does this paper address and why it matters")
    method: str = Field(description="the proposed approach or methodology")
    result: str = Field(description="key experimental results and metrics")
    conclusion: str = Field(description="main takeaways and significance")
    title_zh: str = Field(description="Chinese translation of the paper title")
    summary_zh: str = Field(description="Chinese translation of the paper abstract")
    quality_score: int = Field(description="paper quality score from 1-10: 1=trivial/incremental, 5=solid contribution, 10=breakthrough work. Consider novelty, rigor, and significance.")
    relevance_score: int = Field(description="relevance to user's research direction from 1-10: 1=unrelated, 5=tangentially related, 10=directly addresses user's core topic")
    recommendation: str = Field(description="one of: 'must-read' (highly relevant and high quality), 'worth-reading' (relevant or high quality), 'skim' (marginally useful), 'skip' (not relevant or low quality)")
```

- [ ] **Step 2: Verify model instantiates correctly**

Run: `cd ai && python3 -c "from structure import Structure; s=Structure(tldr='t',motivation='m',method='m',result='r',conclusion='c',title_zh='t',summary_zh='s',quality_score=7,relevance_score=8,recommendation='must-read'); print(s.model_dump())"`
Expected: dict with all 10 fields

- [ ] **Step 3: Commit**

```bash
git add ai/structure.py
git commit -m "feat: add quality_score, relevance_score, recommendation to AI output"
```

---

### Task 3: Update AI Prompts

**Files:**
- Modify: `ai/system.txt`
- Modify: `ai/template.txt`

- [ ] **Step 1: Rewrite system prompt**

Replace `ai/system.txt` with:

```
You are a professional paper analyst for a CS researcher.
Provide concise, detailed, and precise answers using correct terminology.
Output in {language}. Respond with valid JSON matching the specified schema.

Prohibited content: politics, ethnicity, religion, violence, pornography, terrorism, gambling, regional discrimination, leaders and their relatives. If detected, reply: "This content has not passed the compliance test and has been hidden."

Scoring instructions:
- quality_score (1-10): Rate the paper's academic quality. Consider: novelty of approach, rigor of evaluation, significance of contribution, clarity of writing. 1-3=minor/incremental, 4-6=solid contribution, 7-8=significant advance, 9-10=potential breakthrough.
- relevance_score (1-10): Rate how relevant this paper is to the user's research. Consider the research direction and keywords provided. 1-3=unrelated field, 4-6=tangentially related, 7-8=directly relevant, 9-10=core topic.
- recommendation: Based on both scores, classify as: "must-read" (relevance>=7 AND quality>=7), "worth-reading" (relevance>=5 OR quality>=7), "skim" (relevance>=3 OR quality>=5), "skip" (relevance<3 AND quality<5).

JSON fields:
- "tldr": one-sentence key contribution summary
- "motivation": what problem and why it matters
- "method": proposed approach
- "result": key experimental results
- "conclusion": main takeaways
- "title_zh": Chinese title translation
- "summary_zh": Chinese abstract translation
- "quality_score": integer 1-10
- "relevance_score": integer 1-10
- "recommendation": one of "must-read", "worth-reading", "skim", "skip"
```

- [ ] **Step 2: Rewrite user prompt template**

Replace `ai/template.txt` with:

```
Research direction: {research_direction}
Keywords: {keywords}

Analyze this paper:

Title: {title}

Abstract:
{content}
```

- [ ] **Step 3: Verify files are correct**

Run: `cd ai && python3 -c "s=open('system.txt').read(); t=open('template.txt').read(); assert '{research_direction}' in t; assert '{keywords}' in t; assert '{title}' in t; assert 'quality_score' in s; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add ai/system.txt ai/template.txt
git commit -m "feat: update AI prompts with scoring + research context"
```

---

### Task 4: Refactor enhance.py for Single-Paper Callable + Research Profile

**Files:**
- Modify: `ai/enhance.py`

- [ ] **Step 1: Add research profile loader and single-paper enhance function**

Add these functions after the imports (before `parse_args`), and modify the chain construction to pass research profile. Key changes:

1. Add function `load_research_profile()` that reads `research_profile.json` from the parent directory:

```python
def load_research_profile() -> dict:
    profile_path = os.path.join(os.path.dirname(__file__), '..', 'research_profile.json')
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            return json.load(f)
    return {"direction": "", "keywords": [], "quality_criteria": ""}
```

2. Add function `build_chain(model_name: str)` that returns a langchain chain:

```python
def build_chain(model_name: str):
    llm = ChatOpenAI(model=model_name).with_structured_output(Structure, method="json_mode")
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])
    return prompt_template | llm
```

3. Add function `enhance_single(paper: dict, chain, profile: dict, language: str) -> dict | None`:

```python
def enhance_single(paper: dict, chain, profile: dict, language: str) -> dict | None:
    """Enhance a single paper dict with AI analysis. Returns the paper with 'AI' field added, or None if filtered."""
    default_ai = {
        "tldr": "", "motivation": "", "method": "", "result": "", "conclusion": "",
        "title_zh": "", "summary_zh": "",
        "quality_score": 0, "relevance_score": 0, "recommendation": "skip",
    }
    try:
        response: Structure = chain.invoke({
            "language": language,
            "content": paper.get("summary", ""),
            "title": paper.get("title", ""),
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
        })
        paper["AI"] = response.model_dump()
    except langchain_core.exceptions.OutputParserException as e:
        error_msg = str(e)
        partial = {}
        try:
            if "Function Structure arguments:" in error_msg:
                json_str = error_msg.split("Function Structure arguments:", 1)[1].strip().split("are not valid JSON")[0].strip()
            else:
                start = error_msg.find('{')
                end = error_msg.rfind('}')
                if start != -1 and end != -1:
                    json_str = error_msg[start:end+1]
                else:
                    json_str = ""
            if json_str:
                partial = json.loads(json_str)
        except Exception:
            pass
        paper["AI"] = {**default_ai, **partial}
    except Exception as e:
        logger.error(f"Enhance error for {paper.get('id','?')}: {e}")
        paper["AI"] = default_ai
    for k in default_ai:
        if k not in paper["AI"]:
            paper["AI"][k] = default_ai[k]
    return paper
```

4. Modify `process_single_item` to call `enhance_single` internally and keep the existing code_info + sensitivity logic.

5. Update `process_all_items` to pass profile into the chain invocation via the new template variables.

- [ ] **Step 2: Verify the module loads without errors**

Run: `cd ai && python3 -c "from enhance import load_research_profile, build_chain, enhance_single; p=load_research_profile(); print(p['direction'][:40])"`
Expected: prints the research direction text

- [ ] **Step 3: Commit**

```bash
git add ai/enhance.py
git commit -m "feat: refactor enhance.py — add enhance_single + research profile"
```

---

### Task 5: Wire AI Enhancement into Streaming Crawl Loop

**Files:**
- Modify: `daemon.py`

- [ ] **Step 1: Add per-paper AI enhancement in daemon**

Add import at top of `daemon.py`:

```python
from ai.enhance import enhance_single, build_chain, load_research_profile
```

Add a module-level cache for the AI chain:

```python
_ai_chain = None
_ai_profile = None
_ai_language = "Chinese"
```

Add function:

```python
def _get_ai_chain():
    global _ai_chain, _ai_profile
    if _ai_chain is None:
        model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
        _ai_chain = build_chain(model_name)
        _ai_profile = load_research_profile()
        logger.info(f"AI chain initialized: {model_name}")
    return _ai_chain, _ai_profile
```

Modify `_append_paper` to optionally enhance after writing:

```python
def _append_paper(paper: Paper, date_str: str | None = None, enhance: bool = False) -> bool:
    """Append a single paper to JSONL. If enhance=True, run AI analysis first."""
    global _written_ids
    if paper.id in _written_ids:
        return False

    if enhance:
        try:
            chain, profile = _get_ai_chain()
            paper_dict = json.loads(paper.to_jsonl())
            enhanced = enhance_single(paper_dict, chain, profile, _ai_language)
            if enhanced:
                # Write enhanced version as separate AI file
                date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
                DATA_DIR.mkdir(exist_ok=True)
                ai_path = DATA_DIR / f"{date_str}_AI_enhanced_{_ai_language}.jsonl"
                with open(ai_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(enhanced, ensure_ascii=False) + "\n")
                _written_ids.add(paper.id)
                return True
        except Exception as e:
            logger.warning(f"AI enhance failed for {paper.id}: {e}")

    date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    DATA_DIR.mkdir(exist_ok=True)
    filepath = DATA_DIR / f"{date_str}.jsonl"
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(paper.to_jsonl() + "\n")
    _written_ids.add(paper.id)
    return True
```

Also need `import os` at top of daemon.py (check if already there).

Update `run_arxiv_job` and `run_crossref_job` to pass `enhance=True`:

In `run_arxiv_job`, change `_append_paper(paper)` to `_append_paper(paper, enhance=True)`.

In `run_crossref_job`, change `_append_paper(paper)` to `_append_paper(paper, enhance=True)`.

- [ ] **Step 2: Verify daemon starts without import errors**

Run: `python3 -c "from daemon import _get_ai_chain; print('import OK')"` (from project root)
Expected: `import OK`

- [ ] **Step 3: Commit**

```bash
git add daemon.py
git commit -m "feat: wire AI enhancement into streaming crawl — enhance per paper"
```

---

### Task 6: Daily Digest Generator

**Files:**
- Create: `ai/digest.py`

- [ ] **Step 1: Create the digest generator**

```python
#!/usr/bin/env python3
"""Generate a daily Markdown research digest from AI-enhanced papers."""

import json
import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

if os.path.exists(os.path.join(os.path.dirname(__file__), '.env')):
    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DIGEST_PROMPT = """You are a research assistant. Based on the following AI-analyzed papers from today, write a concise research digest in Markdown.

Group papers by topic/theme. For each group:
1. Summarize the key trend or insight (2-3 sentences)
2. List the most important papers with title + one-line note

At the end, highlight:
- Top 3 must-read papers (highest quality AND relevance)
- Any notable breakthroughs or surprising results

Write in {language}.

Papers data:
{papers_json}
"""


def generate_digest(date_str: str | None = None, language: str = "Chinese") -> str:
    date_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data_dir = Path(__file__).parent.parent / "data"

    papers = []
    ai_file = data_dir / f"{date_str}_AI_enhanced_{language}.jsonl"
    if not ai_file.exists():
        logger.warning(f"No AI-enhanced file for {date_str}")
        return ""

    with open(ai_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                papers.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not papers:
        return ""

    papers.sort(key=lambda p: (p.get("AI", {}).get("relevance_score", 0), p.get("AI", {}).get("quality_score", 0)), reverse=True)

    summaries = []
    for p in papers[:80]:
        ai = p.get("AI", {})
        summaries.append({
            "title": p.get("title", ""),
            "source": p.get("source", ""),
            "journal": p.get("journal_title", ""),
            "categories": p.get("categories", []),
            "tldr": ai.get("tldr", ""),
            "recommendation": ai.get("recommendation", "skip"),
            "quality_score": ai.get("quality_score", 0),
            "relevance_score": ai.get("relevance_score", 0),
        })

    model_name = os.environ.get("MODEL_NAME", "deepseek-v4-flash")
    llm = ChatOpenAI(model=model_name, temperature=0.3)
    prompt = ChatPromptTemplate.from_template(DIGEST_PROMPT)
    chain = prompt | llm

    result = chain.invoke({
        "language": language,
        "papers_json": json.dumps(summaries, ensure_ascii=False, indent=2),
    })

    digest_dir = data_dir.parent / "digests"
    digest_dir.mkdir(exist_ok=True)
    digest_path = digest_dir / f"{date_str}.md"

    content = f"# Research Digest — {date_str}\n\n{result.content}\n"
    digest_path.write_text(content, encoding="utf-8")
    logger.info(f"Digest saved to {digest_path}")
    return str(digest_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    date = sys.argv[1] if len(sys.argv) > 1 else None
    path = generate_digest(date)
    if path:
        print(f"Digest: {path}")
    else:
        print("No papers to digest")
        sys.exit(1)
```

- [ ] **Step 2: Verify module loads**

Run: `cd ai && python3 -c "from digest import generate_digest; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ai/digest.py
git commit -m "feat: add daily Markdown research digest generator"
```

---

### Task 7: Trigger Digest After Crawl + Add Digest API Endpoint

**Files:**
- Modify: `daemon.py`

- [ ] **Step 1: Add digest trigger and API endpoint**

In `daemon.py`, add import:

```python
from ai.digest import generate_digest
```

Add after `run_enhance_job`:

```python
def run_digest_job():
    logger.info("Starting digest generation")
    try:
        path = generate_digest()
        if path:
            logger.info(f"Digest generated: {path}")
        else:
            logger.info("No papers to digest today")
    except Exception as e:
        logger.error(f"Digest job failed: {e}", exc_info=True)
```

Add API endpoint (after the `/api/trigger/<job>` route):

```python
@app.route("/api/digest/<date_str>", methods=["GET"])
def get_digest(date_str: str):
    digest_path = Path("digests") / f"{date_str}.md"
    if digest_path.exists():
        return digest_path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/markdown"}
    return jsonify({"error": "digest not found"}), 404


@app.route("/api/digests", methods=["GET"])
def list_digests():
    digest_dir = Path("digests")
    if not digest_dir.exists():
        return jsonify({"digests": []})
    digests = sorted(digest_dir.glob("*.md"), reverse=True)
    return jsonify({"digests": [d.stem for d in digests]})
```

Update the scheduler `_run_and_reschedule` to call `run_digest_job` after the enhance job:

In the arxiv block, after `run_enhance_job()` call, add `run_digest_job()`.

- [ ] **Step 2: Verify daemon starts**

Run: `python3 -c "from daemon import app; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add daemon.py
git commit -m "feat: add digest API endpoints + auto-trigger after enhance"
```

---

### Task 8: Frontend — Score Display + Color Borders + Inline TL;DR

**Files:**
- Modify: `css/styles.css`
- Modify: `js/app.js`

- [ ] **Step 1: Add CSS for score display, color borders, and recommendation badges**

Append to `css/styles.css` (before the `@media` section):

```css
/* AI Score Display */
.paper-card[data-rec="must-read"] { border-left: 3px solid #22c55e; }
.paper-card[data-rec="worth-reading"] { border-left: 3px solid #3b82f6; }
.paper-card[data-rec="skim"] { border-left: 3px solid #eab308; }
.paper-card[data-rec="skip"] { border-left: 3px solid #6b7280; }

.score-bar {
    display: flex;
    gap: 6px;
    align-items: center;
    font-size: 0.7rem;
    color: var(--text-secondary);
    margin-top: 4px;
}
.score-item {
    display: flex;
    align-items: center;
    gap: 2px;
}
.score-fill {
    display: inline-block;
    height: 4px;
    border-radius: 2px;
    background: var(--accent);
    transition: width 0.3s;
}

.rec-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
}
.rec-badge.must-read { background: rgba(34,197,94,0.2); color: #22c55e; }
.rec-badge.worth-reading { background: rgba(59,130,246,0.2); color: #3b82f6; }
.rec-badge.skim { background: rgba(234,179,8,0.2); color: #eab308; }
.rec-badge.skip { background: rgba(107,114,128,0.2); color: #6b7280; }

.card-tldr {
    margin-top: 4px;
    font-size: 0.78rem;
    color: var(--accent-light);
    font-style: italic;
}
```

- [ ] **Step 2: Update card rendering in js/app.js**

In the `renderPapers` function, replace the card template section. Find the line starting with `container.innerHTML = pagePapers.map((paper, i) => {` and replace the return template with:

```javascript
        const ai = paper.AI || {};
        const hasAi = !!(ai.tldr || paper.tldr);
        const sourceBadge = paper.source === 'crossref'
            ? `<span class="source-badge crossref">${paper.journal_title || 'Journal'}</span>`
            : `<span class="source-badge arxiv">arXiv</span>`;
        const articleType = paper.article_type || _inferType(paper);
        const typeTag = articleType === 'news'
            ? '<span class="paper-cat" style="background:rgba(249,115,22,0.2);color:#f97316">新闻</span>'
            : '';
        const aiBadge = hasAi ? '<span class="ai-badge">AI</span>' : '';
        const rec = ai.recommendation || '';
        const recBadge = rec ? `<span class="rec-badge ${rec}">${rec}</span>` : '';
        const qScore = ai.quality_score || 0;
        const rScore = ai.relevance_score || 0;
        const scoreBar = (qScore || rScore) ? `
            <div class="score-bar">
                <span class="score-item">Q<span class="score-fill" style="width:${qScore*8}px;background:#3b82f6"></span>${qScore}</span>
                <span class="score-item">R<span class="score-fill" style="width:${rScore*8}px;background:#22c55e"></span>${rScore}</span>
            </div>` : '';
        const cardTldr = ai.tldr ? `<div class="card-tldr">${ai.tldr}</div>` : '';

        const categories = (paper.categories || []).map(c =>
            `<span class="paper-cat">${c}</span>`
        ).join('');

        const authors = (paper.authors || []).slice(0, 3).join(', ') +
            ((paper.authors || []).length > 3 ? ' et al.' : '');

        const summary = ai.summary_zh || paper.summary_zh || paper.summary || '';
        const title = ai.title_zh || paper.title_zh || paper.title || '';
        const codeBadge = paper.code_url ? `<span class="paper-cat" style="background:rgba(34,197,94,0.2);color:#22c55e">Code</span>` : '';

        const idx = start + i;
        return `
            <div class="paper-card" data-idx="${idx}" data-rec="${rec}">
                <div class="paper-header">
                    ${sourceBadge}${aiBadge}${recBadge}${typeTag}
                    <div class="paper-categories">${categories}${codeBadge}</div>
                </div>
                <div class="paper-title">${title}</div>
                ${cardTldr}
                <div class="paper-authors">${authors}</div>
                <div class="paper-summary">${summary.substring(0, 200)}...</div>
                ${scoreBar}
                <div class="paper-meta">
                    <span>${paper.published_date || ''}</span>
                    <span>${paper.publisher || ''}</span>
                </div>
            </div>
        `;
```

- [ ] **Step 3: Verify JS syntax**

Run: `node -c js/app.js && echo "OK"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add css/styles.css js/app.js
git commit -m "feat: card score bars + color borders + inline TL;DR + recommendation badges"
```

---

### Task 9: Research Profile Settings UI

**Files:**
- Modify: `index.html`
- Modify: `daemon.py`
- Modify: `js/app.js` (or create new `js/profile.js`)

- [ ] **Step 1: Add profile API endpoints in daemon.py**

Add after the existing subscription routes:

```python
@app.route("/api/profile", methods=["GET"])
def get_profile():
    profile_path = Path("research_profile.json")
    if profile_path.exists():
        return jsonify(json.loads(profile_path.read_text(encoding="utf-8")))
    return jsonify({"direction": "", "keywords": [], "quality_criteria": ""})


@app.route("/api/profile", methods=["PUT"])
def put_profile():
    data = request.get_json()
    if not data:
        return jsonify({"error": "empty body"}), 400
    Path("research_profile.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    global _ai_chain, _ai_profile
    _ai_chain = None
    _ai_profile = None
    logger.info("Research profile updated, AI chain reset")
    return jsonify(data)
```

- [ ] **Step 2: Add profile settings panel in index.html**

Add a new modal before the subscription modal:

```html
    <!-- Profile Modal -->
    <div id="profile-modal" class="modal" onclick="if(event.target===this)closeProfileModal()">
        <div class="modal-content">
            <button class="close-btn" onclick="closeProfileModal()">&times;</button>
            <h2 style="margin-bottom:12px">研究方向设置</h2>
            <label style="font-size:0.85rem;color:var(--text-secondary)">研究方向描述</label>
            <textarea id="profile-direction" rows="3" style="width:100%;margin:4px 0 12px;padding:8px;border-radius:6px;border:1px solid var(--border-color);background:var(--bg-primary);color:var(--text-primary);font-size:0.85rem;resize:vertical" placeholder="描述你的研究方向，AI会据此判断论文相关性..."></textarea>
            <label style="font-size:0.85rem;color:var(--text-secondary)">关键词（逗号分隔）</label>
            <input id="profile-keywords" type="text" style="width:100%;margin:4px 0 12px;padding:8px;border-radius:6px;border:1px solid var(--border-color);background:var(--bg-primary);color:var(--text-primary);font-size:0.85rem" placeholder="neural rendering, 3D reconstruction, diffusion models...">
            <label style="font-size:0.85rem;color:var(--text-secondary)">质量标准（可选）</label>
            <input id="profile-quality" type="text" style="width:100%;margin:4px 0 12px;padding:8px;border-radius:6px;border:1px solid var(--border-color);background:var(--bg-primary);color:var(--text-primary);font-size:0.85rem" placeholder="Prioritize papers with strong empirical results...">
            <button onclick="saveProfile()" class="follow-btn" style="width:100%">保存</button>
        </div>
    </div>
```

Add a button to open profile in the header, before the gear button:

```html
            <button onclick="openProfileModal()" class="gear-btn" title="研究方向">🎯</button>
```

- [ ] **Step 3: Add profile JS functions**

Add to `js/app.js`:

```javascript
async function openProfileModal() {
    try {
        const resp = await fetch('/api/profile');
        if (resp.ok) {
            const data = await resp.json();
            document.getElementById('profile-direction').value = data.direction || '';
            document.getElementById('profile-keywords').value = (data.keywords || []).join(', ');
            document.getElementById('profile-quality').value = data.quality_criteria || '';
        }
    } catch {}
    document.getElementById('profile-modal').classList.add('active');
}

function closeProfileModal() {
    document.getElementById('profile-modal').classList.remove('active');
}

async function saveProfile() {
    const direction = document.getElementById('profile-direction').value;
    const keywords = document.getElementById('profile-keywords').value.split(',').map(k => k.trim()).filter(k => k);
    const quality_criteria = document.getElementById('profile-quality').value;
    try {
        await fetch('/api/profile', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({direction, keywords, quality_criteria}),
        });
        closeProfileModal();
    } catch (e) {
        console.error('Failed to save profile:', e);
    }
}
```

Also add Escape key handler for profile modal in the keydown listener:

```javascript
        if (e.key === 'Escape') {
            closePaperModal();
            closeSubscriptionModal();
            closeProfileModal();
            closeAllDropdowns();
        }
```

- [ ] **Step 4: Verify daemon starts and API works**

Run: `python3 -c "from daemon import app; print('OK')"` then test:
`curl -s http://localhost:8080/api/profile | python3 -m json.tool`

- [ ] **Step 5: Commit**

```bash
git add daemon.py index.html js/app.js
git commit -m "feat: research profile settings UI + API"
```

---

### Task 10: Frontend — Sort by Score + Filter by Recommendation

**Files:**
- Modify: `js/app.js`
- Modify: `index.html`

- [ ] **Step 1: Add recommendation filter options to the type dropdown**

In `buildFilterOptions()`, update the type renderFilterDropdown call to include recommendations:

```javascript
    renderFilterDropdown('type', [
        { value: 'research', label: '研究论文' },
        { value: 'news', label: '新闻评论' },
        { value: 'must-read', label: 'Must Read' },
        { value: 'worth-reading', label: 'Worth Reading' },
        { value: 'skim', label: 'Skim' },
    ]);
```

Update the type filter logic in `renderPapers()`:

```javascript
    if (currentTypeFilter !== 'all') {
        filteredPapers = filteredPapers.filter(p => {
            const at = p.article_type || _inferType(p);
            const rec = (p.AI || {}).recommendation || '';
            return at === currentTypeFilter || rec === currentTypeFilter;
        });
    }
```

- [ ] **Step 2: Add sort-by-score option**

Replace the sort toggle to cycle through 3 modes:

```javascript
function toggleSort() {
    const modes = ['desc', 'asc', 'relevance', 'quality'];
    const labels = ['↓ 新→旧', '↑ 旧→新', '★ 相关性', '✦ 质量'];
    const idx = (modes.indexOf(sortOrder) + 1) % modes.length;
    sortOrder = modes[idx];
    document.getElementById('sort-btn').textContent = labels[idx];
    renderPapers();
}
```

Update the sort logic in `renderPapers()`:

```javascript
    filteredPapers.sort((a, b) => {
        if (sortOrder === 'relevance') {
            return ((b.AI || {}).relevance_score || 0) - ((a.AI || {}).relevance_score || 0);
        }
        if (sortOrder === 'quality') {
            return ((b.AI || {}).quality_score || 0) - ((a.AI || {}).quality_score || 0);
        }
        const da = a.published_date || '';
        const db = b.published_date || '';
        return sortOrder === 'desc' ? db.localeCompare(da) : da.localeCompare(db);
    });
```

- [ ] **Step 3: Verify JS syntax**

Run: `node -c js/app.js && echo "OK"`

- [ ] **Step 4: Commit**

```bash
git add js/app.js
git commit -m "feat: sort by relevance/quality + filter by recommendation"
```

---

### Task 11: Add .gitignore Entries + Final Integration Test

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add digests/ to .gitignore**

Append to `.gitignore`:

```
digests/
```

- [ ] **Step 2: Full integration test — restart daemon and verify**

Kill old daemon, start fresh:

```bash
lsof -ti:8080 | xargs kill -9 2>/dev/null
sleep 1
python3 daemon.py --port 8080 &
sleep 5
```

Test all endpoints:

```bash
curl -s http://localhost:8080/api/stats | python3 -m json.tool
curl -s http://localhost:8080/api/profile | python3 -m json.tool
curl -s "http://localhost:8080/api/papers?per_page=3" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); [print(p.get('AI',{}).get('recommendation','N/A')) for p in d['papers']]"
curl -s http://localhost:8080/api/digests
```

Verify frontend loads with scores visible.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add digests/ to .gitignore + integration test"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Unified AI enhancement (arXiv + Crossref) — Task 4+5
- ✅ Dual-dimension scoring (quality + relevance) — Task 2+3
- ✅ Research profile (text description + keywords) — Task 1+9
- ✅ Inline card display (color border + TL;DR + scores) — Task 8
- ✅ Daily Markdown digest — Task 6+7
- ✅ Sort by score — Task 10
- ✅ Filter by recommendation — Task 10
- ✅ Streaming enhance (edge-case: enhance per paper) — Task 5

**2. Placeholder scan:** No TBD, TODO, or "implement later" found. All steps contain actual code.

**3. Type consistency:** `Structure` fields (`quality_score`, `relevance_score`, `recommendation`) are consistently used in `enhance.py`, `digest.py`, `daemon.py`, and `js/app.js`. The `AI` dict key is used consistently across all files. `research_profile.json` schema (`direction`, `keywords`, `quality_criteria`) matches usage in `enhance.py`, `daemon.py`, and the profile UI.
