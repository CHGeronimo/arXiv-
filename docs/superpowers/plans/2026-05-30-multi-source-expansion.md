# Multi-Source Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Science journal (Crossref), DBLP conference papers (CV/ML/NLP), and Semantic Scholar keyword search as data sources, with expanded Paper model and redesigned subscription UI.

**Architecture:** Three new crawlers following the existing `crawl_iter()` generator pattern, each mapping to the extended Paper model. New source values: `crossref` (existing, covers Science too), `dblp`, `semantic_scholar`. Subscription UI redesigned with three tabs: Journals / Conferences / Search. All new sources stream through `_append_paper(enhance=True)` for AI scoring.

**Tech Stack:** Python 3, httpx (HTTP), Flask (API), vanilla JS (frontend). DBLP API at `dblp.uni-trier.de`. S2 API at `api.semanticscholar.org`.

---

## File Structure

| File | Action | Responsibility |
|:-----|:-------|:---------------|
| `crawler/models.py` | Modify | Add `venue`, `acceptance`, `citation_count`, `version` fields to Paper |
| `crawler/dblp_crawler.py` | Create | DBLP API crawler, venue-based filtering |
| `crawler/s2_crawler.py` | Create | Semantic Scholar search API crawler |
| `crawler/subs_store.py` | Modify | Add conferences and search_keywords to Subscriptions |
| `daemon.py` | Modify | Add DBLP/S2 jobs, update scheduler, update trigger API |
| `subscriptions.json` | Modify | Add conferences and search_keywords sections |
| `js/subscriptions.js` | Modify | Redesign subscription UI with 3 tabs |
| `js/crossref-search.js` | Modify | Rename to `js/source-search.js`, add conference/search UI helpers |
| `js/app.js` | Modify | Display venue badge, acceptance badge, citation count on cards |
| `css/styles.css` | Modify | Styles for venue/acceptance badges |
| `index.html` | Modify | Update subscription modal HTML for 3-tab layout |

---

### Task 1: Extend Paper model with new fields

**Files:**
- Modify: `crawler/models.py`

- [ ] **Step 1: Add new fields to Paper dataclass**

Replace the current `Paper` dataclass with:

```python
@dataclass
class Paper:
    id: str
    source: str  # "arxiv", "crossref", "dblp", "semantic_scholar"
    title: str
    summary: str
    authors: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    doi: str = ""
    published_date: str = ""
    url: str = ""
    pdf: str = ""
    publisher: str = ""
    journal_title: Optional[str] = None
    issn: List[str] = field(default_factory=list)
    comment: Optional[str] = None
    article_type: str = ""
    venue: str = ""  # "Nature", "CVPR 2026", "NeurIPS 2026"
    acceptance: str = ""  # "oral", "spotlight", "poster", ""
    citation_count: int = 0
    version: str = ""
```

The `from_jsonl` classmethod already filters by `cls.__dataclass_fields__`, so old JSONL entries without these fields will default to empty/zero values.

- [ ] **Step 2: Verify backward compatibility**

Run: `python3 -c "from crawler.models import Paper; p = Paper.from_jsonl('{\"id\":\"x\",\"source\":\"arxiv\",\"title\":\"t\",\"summary\":\"s\"}'); print(p.venue, p.acceptance, p.citation_count, p.version)"`

Expected: ` 0 ` (empty strings and zero)

- [ ] **Step 3: Commit**

```bash
git add crawler/models.py
git commit -m "feat: add venue, acceptance, citation_count, version to Paper model"
```

---

### Task 2: Extend Subscriptions model for conferences and search

**Files:**
- Modify: `crawler/subs_store.py`

- [ ] **Step 1: Add Conference dataclass and update Subscriptions**

Add `Conference` dataclass and extend `Subscriptions`:

```python
@dataclass
class Conference:
    venue: str  # "CVPR", "NeurIPS", "ICML"
    last_updated: Optional[str] = None


@dataclass
class Subscriptions:
    arxiv_categories: List[str] = field(default_factory=lambda: ["cs.CV", "cs.CL"])
    crossref_journals: List[Journal] = field(default_factory=list)
    conferences: List[Conference] = field(default_factory=list)
    search_keywords: List[str] = field(default_factory=list)
```

Update `load()`:

```python
@classmethod
def load(cls, path: str = "subscriptions.json") -> Subscriptions:
    if not os.path.exists(path):
        return cls()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cats = data.get("arxiv", {}).get("categories", ["cs.CV", "cs.CL"])
    journals = [
        Journal(issn=j["issn"], name=j["name"], last_updated=j.get("lastUpdated"))
        for j in data.get("crossref", {}).get("journals", [])
    ]
    conferences = [
        Conference(venue=c["venue"], last_updated=c.get("lastUpdated"))
        for c in data.get("conferences", [])
    ]
    search_keywords = data.get("search", {}).get("keywords", [])
    return cls(
        arxiv_categories=cats,
        crossref_journals=journals,
        conferences=conferences,
        search_keywords=search_keywords,
    )
```

Update `save()` and `to_dict()` to include conferences and search_keywords in the same pattern as journals.

- [ ] **Step 2: Verify serialization round-trip**

Run: `python3 -c "from crawler.subs_store import Subscriptions; s = Subscriptions(); s.conferences = [Conference(venue='CVPR')]; s.save('/tmp/test_subs.json'); s2 = Subscriptions.load('/tmp/test_subs.json'); print(s2.conferences)"`

Expected: `[Conference(venue='CVPR', last_updated=None)]`

- [ ] **Step 3: Commit**

```bash
git add crawler/subs_store.py
git commit -m "feat: add Conference and search_keywords to Subscriptions model"
```

---

### Task 3: Create DBLP crawler

**Files:**
- Create: `crawler/dblp_crawler.py`

- [ ] **Step 1: Implement DBLP crawler**

```python
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Generator, List, Set

import httpx

from crawler.models import Paper
from crawler.subs_store import Conference

logger = logging.getLogger(__name__)

DBLP_BASE = "https://dblp.uni-trier.de/search/publ/api"

# Map short venue names to DBLP venue strings
VENUE_MAP = {
    "CVPR": "CVPR",
    "ICCV": "ICCV",
    "ECCV": "ECCV",
    "NeurIPS": "NeurIPS",
    "ICML": "ICML",
    "ICLR": "ICLR",
    "ACL": "ACL",
    "EMNLP": "EMNLP",
    "NAACL": "NAACL",
}


class DblpCrawler:
    def __init__(self, conferences: List[Conference], fetch_interval_hours: int = 24):
        self.conferences = conferences
        self.fetch_interval_hours = fetch_interval_hours

    def _needs_update(self, conf: Conference) -> bool:
        if conf.last_updated is None:
            return True
        try:
            last = datetime.fromisoformat(conf.last_updated.replace("Z", "+00:00"))
            diff = datetime.now(timezone.utc) - last
            return diff.total_seconds() >= self.fetch_interval_hours * 3600
        except Exception:
            return True

    def _fetch_recent(self, venue: str, year: int) -> List[dict]:
        query = f"venue:{venue} year:{year}"
        url = f"{DBLP_BASE}?q={query}&format=json&h=100"
        for attempt in range(3):
            try:
                resp = httpx.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                return data.get("result", {}).get("hits", {}).get("hit", [])
            except Exception as e:
                logger.warning(f"DBLP fetch attempt {attempt+1}/3 failed: {e}")
        return []

    def _parse_hit(self, hit: dict, venue: str) -> Paper | None:
        info = hit.get("info", {})
        title = info.get("title", "")
        if not title:
            return None

        # Authors
        authors_raw = info.get("authors", {}).get("author", [])
        if isinstance(authors_raw, dict):
            authors_raw = [authors_raw]
        authors = [a.get("text", "") for a in authors_raw]

        doi = info.get("doi", "")
        year = info.get("year", "")
        ee = info.get("ee", "")
        url_dblp = info.get("url", "")

        # Determine acceptance type from DBLP key (best-effort)
        acceptance = ""
        key = info.get("key", "").lower()
        if "oral" in key:
            acceptance = "oral"
        elif "spotlight" in key:
            acceptance = "spotlight"

        pub_date = f"{year}-01-01" if year else ""

        return Paper(
            id=doi or f"dblp-{hit.get('@id', '')}",
            source="dblp",
            title=title,
            summary="",
            authors=authors,
            categories=[],
            doi=doi,
            published_date=pub_date,
            url=ee or url_dblp,
            pdf="",
            publisher="",
            venue=f"{venue} {year}",
            acceptance=acceptance,
        )

    def crawl_iter(self) -> Generator[Paper, None, None]:
        seen_dois: Set[str] = set()
        current_year = datetime.now(timezone.utc).year

        for conf in self.conferences:
            if not self._needs_update(conf):
                logger.debug(f"Skipping {conf.venue}, recently updated")
                continue

            venue = VENUE_MAP.get(conf.venue, conf.venue)
            # Fetch current year and previous year
            for year in [current_year, current_year - 1]:
                hits = self._fetch_recent(venue, year)
                count = 0
                for hit in hits:
                    paper = self._parse_hit(hit, venue)
                    if paper and paper.doi not in seen_dois:
                        seen_dois.add(paper.doi)
                        yield paper
                        count += 1
                logger.info(f"DBLP {venue} {year}: {count} papers")

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
```

- [ ] **Step 2: Test DBLP crawler offline**

Run: `python3 -c "from crawler.dblp_crawler import DblpCrawler; from crawler.subs_store import Conference; c = DblpCrawler([Conference(venue='CVPR')]); papers = c.crawl(); print(f'Got {len(papers)} CVPR papers'); print(papers[0].title if papers else 'none')"`

Expected: ~100 CVPR papers with venue="CVPR 2026" or "CVPR 2025"

- [ ] **Step 3: Commit**

```bash
git add crawler/dblp_crawler.py
git commit -m "feat: add DBLP conference paper crawler"
```

---

### Task 4: Create Semantic Scholar crawler

**Files:**
- Create: `crawler/s2_crawler.py`

- [ ] **Step 1: Implement S2 search crawler**

```python
from __future__ import annotations

import logging
from typing import Generator, List

import httpx

from crawler.models import Paper

logger = logging.getLogger(__name__)

S2_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,abstract,authors,year,venue,citationCount,externalIds,publicationDate"


class S2Crawler:
    def __init__(self, keywords: List[str], max_per_keyword: int = 20):
        self.keywords = keywords
        self.max_per_keyword = max_per_keyword

    def _search(self, keyword: str) -> List[dict]:
        url = f"{S2_BASE}?query={keyword}&limit={self.max_per_keyword}&fields={S2_FIELDS}&year=2024-"
        for attempt in range(3):
            try:
                resp = httpx.get(url, timeout=30)
                if resp.status_code == 429:
                    logger.warning(f"S2 rate limited, skipping keyword '{keyword}'")
                    return []
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
            except Exception as e:
                logger.warning(f"S2 search attempt {attempt+1}/3 failed for '{keyword}': {e}")
        return []

    def _parse_paper(self, item: dict, keyword: str) -> Paper | None:
        title = item.get("title", "")
        if not title:
            return None

        abstract = item.get("abstract", "") or ""
        authors = [a.get("name", "") for a in (item.get("authors") or [])]
        ext_ids = item.get("externalIds") or {}
        doi = ext_ids.get("DOI", "")
        arxiv_id = ext_ids.get("ArXiv", "")
        s2_id = item.get("paperId", "")

        pub_date = item.get("publicationDate", "") or ""
        venue = item.get("venue", "") or ""
        citation_count = item.get("citationCount", 0) or 0

        url = f"https://www.semanticscholar.org/paper/{s2_id}" if s2_id else ""
        pdf = f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else ""

        return Paper(
            id=doi or s2_id or f"s2-{abs(hash(title))}",
            source="semantic_scholar",
            title=title,
            summary=abstract,
            authors=authors,
            doi=doi,
            published_date=pub_date,
            url=url,
            pdf=pdf,
            venue=venue,
            citation_count=citation_count,
        )

    def crawl_iter(self) -> Generator[Paper, None, None]:
        seen_ids: set[str] = set()
        for keyword in self.keywords:
            results = self._search(keyword)
            count = 0
            for item in results:
                paper = self._parse_paper(item, keyword)
                if paper and paper.id not in seen_ids:
                    seen_ids.add(paper.id)
                    yield paper
                    count += 1
            logger.info(f"S2 keyword '{keyword}': {count} papers")

    def crawl(self) -> List[Paper]:
        return list(self.crawl_iter())
```

- [ ] **Step 2: Test S2 crawler (may hit rate limit)**

Run: `python3 -c "from crawler.s2_crawler import S2Crawler; c = S2Crawler(['neural rendering'], max_per_keyword=3); papers = c.crawl(); print(f'Got {len(papers)} papers'); print(papers[0].title if papers else 'rate limited')"`

Expected: 3 papers or "rate limited" message

- [ ] **Step 3: Commit**

```bash
git add crawler/s2_crawler.py
git commit -m "feat: add Semantic Scholar keyword search crawler"
```

---

### Task 5: Wire new crawlers into daemon

**Files:**
- Modify: `daemon.py`

- [ ] **Step 1: Add imports for new crawlers**

Add after existing imports (line 19):

```python
from crawler.dblp_crawler import DblpCrawler
from crawler.s2_crawler import S2Crawler
```

- [ ] **Step 2: Add `run_dblp_job()` function**

Add after `run_crossref_job()` (after line 343):

```python
def run_dblp_job():
    logger.info("Starting DBLP crawl job")
    try:
        subs = _load_subs()
        if not subs.conferences:
            logger.info("No conferences subscribed, skipping DBLP")
            return
        crawler = DblpCrawler(conferences=subs.conferences)
        fetched, written = 0, 0
        fetched_venues: set[str] = set()
        for paper in crawler.crawl_iter():
            fetched += 1
            fetched_venues.add(paper.venue)
            if _append_paper(paper, enhance=True):
                written += 1
            if fetched % 20 == 0:
                logger.info(f"DBLP progress: {fetched} fetched, {written} written")
        if fetched_venues:
            now = datetime.now(timezone.utc).isoformat()
            for c in subs.conferences:
                if any(c.venue in v for v in fetched_venues):
                    c.last_updated = now
            _save_subs(subs)
        logger.info(f"DBLP job done: {fetched} fetched, {written} new written")
    except Exception as e:
        logger.error(f"DBLP job failed: {e}", exc_info=True)


def run_s2_job():
    logger.info("Starting S2 search job")
    try:
        subs = _load_subs()
        keywords = subs.search_keywords
        if not keywords:
            profile = load_research_profile()
            keywords = profile.get("keywords", [])
        if not keywords:
            logger.info("No search keywords, skipping S2")
            return
        crawler = S2Crawler(keywords=keywords, max_per_keyword=20)
        fetched, written = 0, 0
        for paper in crawler.crawl_iter():
            fetched += 1
            if _append_paper(paper, enhance=True):
                written += 1
            if fetched % 20 == 0:
                logger.info(f"S2 progress: {fetched} fetched, {written} written")
        logger.info(f"S2 job done: {fetched} fetched, {written} new written")
    except Exception as e:
        logger.error(f"S2 search job failed: {e}", exc_info=True)
```

- [ ] **Step 3: Update Scheduler to include new jobs**

In `Scheduler.start()` (line ~392), add after the crossref line:

```python
self._run_and_reschedule("dblp", interval_hours=24)
self._run_and_reschedule("s2", interval_hours=24)
```

In `_run_and_reschedule()` (line ~404), add cases:

```python
elif job_name == "dblp":
    run_dblp_job()
elif job_name == "s2":
    run_s2_job()
```

- [ ] **Step 4: Update trigger API to accept new job types**

In `trigger_job()` (line ~165), change the validation:

```python
if job not in ("arxiv", "crossref", "dblp", "s2"):
    return jsonify({"error": "unknown job"}), 400
```

And update the dispatch:

```python
job_funcs = {
    "arxiv": run_arxiv_job,
    "crossref": run_crossref_job,
    "dblp": run_dblp_job,
    "s2": run_s2_job,
}
threading.Thread(target=job_funcs[job], daemon=True).start()
```

- [ ] **Step 5: Verify daemon starts**

Run: `python3 daemon.py --port 8080 &` then `curl -s http://localhost:8080/api/stats | python3 -m json.tool` and kill the process.

Expected: JSON response with stats, no import errors.

- [ ] **Step 6: Commit**

```bash
git add daemon.py
git commit -m "feat: wire DBLP and S2 crawlers into daemon scheduler"
```

---

### Task 6: Redesign subscription UI for 3 tabs

**Files:**
- Modify: `index.html` — subscription modal section
- Modify: `js/subscriptions.js` — add conference/search tab logic
- Modify: `css/subscriptions.css` — add new tab styles

- [ ] **Step 1: Update subscription modal HTML in index.html**

Replace the subscription modal content (the `<div class="subscription-panel">` section) with three tabs:

```html
<div id="subscription-modal" class="subscription-modal" onclick="if(event.target===this)closeSubscriptionModal()">
    <div class="subscription-panel">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
            <h2>订阅管理</h2>
            <button onclick="closeSubscriptionModal()" style="background:none;border:none;font-size:1.5rem;cursor:pointer">&times;</button>
        </div>
        <div class="sub-tabs">
            <div class="sub-tab active" onclick="switchSubTab('journals', this)">期刊</div>
            <div class="sub-tab" onclick="switchSubTab('conferences', this)">会议</div>
            <div class="sub-tab" onclick="switchSubTab('search', this)">搜索</div>
        </div>

        <div id="sub-tab-journals">
            <input id="journal-search-input" type="text" placeholder="搜索期刊名称..." oninput="handleJournalSearch()" style="width:100%;padding:8px;margin-bottom:8px;box-sizing:border-box">
            <div id="journal-search-results"></div>
            <hr style="margin:16px 0">
            <h3>已订阅期刊</h3>
            <div id="crossref-journals-list"></div>
        </div>

        <div id="sub-tab-conferences" style="display:none">
            <p>选择关注的顶级会议：</p>
            <div id="conference-chips"></div>
        </div>

        <div id="sub-tab-search" style="display:none">
            <p>关键词搜索来源 Semantic Scholar（复用研究方向关键词或自定义）</p>
            <div style="margin:8px 0">
                <label><input type="checkbox" id="use-profile-keywords" checked onchange="toggleCustomKeywords()"> 使用研究方向关键词</label>
            </div>
            <textarea id="custom-keywords" rows="3" style="width:100%;padding:8px;border-radius:6px;border:1px solid var(--border-color);background:var(--bg-primary);color:var(--text-primary);font-size:0.85rem;display:none;resize:vertical" placeholder="输入关键词，每行一个..."></textarea>
            <button onclick="saveSearchKeywords()" class="follow-btn" style="margin-top:8px">保存搜索关键词</button>
        </div>
    </div>
</div>
```

Keep the arXiv categories tab but hide it under a separate section. The existing arXiv tab should be the 4th tab or integrated into the header area — but since the user specifically asked for "期刊/会议/搜索三 tab", keep the arXiv categories chip section as-is in the header or add as a 4th tab. For now, add it as a sub-section below the three main tabs.

- [ ] **Step 2: Update subscriptions.js**

Add conference constants and rendering functions:

```javascript
const CONFERENCES = [
    { venue: "CVPR", label: "CVPR", group: "CV" },
    { venue: "ICCV", label: "ICCV", group: "CV" },
    { venue: "ECCV", label: "ECCV", group: "CV" },
    { venue: "NeurIPS", label: "NeurIPS", group: "ML" },
    { venue: "ICML", label: "ICML", group: "ML" },
    { venue: "ICLR", label: "ICLR", group: "ML" },
    { venue: "ACL", label: "ACL", group: "NLP" },
    { venue: "EMNLP", label: "EMNLP", group: "NLP" },
];

function renderConferenceChips() {
    const container = document.getElementById('conference-chips');
    if (!container) return;
    const selected = new Set((subscriptions.conferences || []).map(c => c.venue));
    let html = '';
    let currentGroup = '';
    for (const conf of CONFERENCES) {
        if (conf.group !== currentGroup) {
            if (currentGroup) html += '<div style="height:8px"></div>';
            html += `<div style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:4px">${conf.group}</div>`;
            currentGroup = conf.group;
        }
        const sel = selected.has(conf.venue);
        html += `<label class="sub-chip ${sel ? 'selected' : ''}" style="display:inline-block;margin:2px 4px">
            <input type="checkbox" ${sel ? 'checked' : ''} onchange="toggleConference('${conf.venue}', this.checked)">
            ${conf.label}
        </label>`;
    }
    container.innerHTML = html;
}

function toggleConference(venue, checked) {
    if (!subscriptions.conferences) subscriptions.conferences = [];
    if (checked) {
        if (!subscriptions.conferences.some(c => c.venue === venue)) {
            subscriptions.conferences.push({ venue, lastUpdated: null });
        }
    } else {
        subscriptions.conferences = subscriptions.conferences.filter(c => c.venue !== venue);
    }
    saveSubscriptions(subscriptions);
    renderConferenceChips();
}

function toggleCustomKeywords() {
    const useProfile = document.getElementById('use-profile-keywords').checked;
    document.getElementById('custom-keywords').style.display = useProfile ? 'none' : 'block';
}

async function saveSearchKeywords() {
    const useProfile = document.getElementById('use-profile-keywords').checked;
    if (useProfile) {
        subscriptions.search = { keywords: [], useProfile: true };
    } else {
        const text = document.getElementById('custom-keywords').value;
        const keywords = text.split('\n').map(k => k.trim()).filter(k => k);
        subscriptions.search = { keywords, useProfile: false };
    }
    await saveSubscriptions(subscriptions);
    fetch('/api/trigger/s2', { method: 'POST' }).catch(() => {});
}
```

Update `switchSubTab()` to handle three tabs:

```javascript
function switchSubTab(tab, el) {
    document.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    ['journals', 'conferences', 'search'].forEach(t => {
        const el = document.getElementById(`sub-tab-${t}`);
        if (el) el.style.display = t === tab ? 'block' : 'none';
    });
}
```

Update `renderSubscriptionUI()`:

```javascript
function renderSubscriptionUI() {
    renderArxivCategories();
    renderCrossrefJournals();
    renderConferenceChips();
}
```

- [ ] **Step 3: Verify subscription UI loads**

Open `http://localhost:8080`, click the gear icon. Should see three tabs: 期刊/会议/搜索. Clicking between them should show the correct content.

- [ ] **Step 4: Commit**

```bash
git add index.html js/subscriptions.js css/subscriptions.css
git commit -m "feat: redesign subscription UI with journals/conferences/search tabs"
```

---

### Task 7: Display venue, acceptance, and citation count on cards

**Files:**
- Modify: `js/app.js`
- Modify: `css/styles.css`

- [ ] **Step 1: Update card rendering in `renderPapers()`**

In the card template (inside the `pagePapers.map` callback), replace the `sourceBadge` logic:

After the existing `const sourceBadge = ...` line, add venue badge logic:

```javascript
const sourceBadge = paper.source === 'crossref'
    ? `<span class="source-badge crossref">${paper.journal_title || 'Journal'}</span>`
    : paper.source === 'dblp'
    ? `<span class="source-badge dblp">DBLP</span>`
    : paper.source === 'semantic_scholar'
    ? `<span class="source-badge s2">S2</span>`
    : `<span class="source-badge arxiv">arXiv</span>`;
```

After the sourceBadge, add venue and acceptance badges:

```javascript
const venueBadge = paper.venue ? `<span class="venue-badge">${paper.venue}</span>` : '';
const accBadge = paper.acceptance ? `<span class="acc-badge ${paper.acceptance}">${paper.acceptance}</span>` : '';
const citeBadge = paper.citation_count ? `<span class="cite-badge">&#9733; ${paper.citation_count}</span>` : '';
```

Update the card header to include new badges:

```javascript
<div class="paper-header">
    ${sourceBadge}${venueBadge}${accBadge}${aiBadge}${recBadge}${typeTag}
    <div class="paper-categories">${categories}${codeBadge}</div>
</div>
```

Add citation count to the meta line:

```javascript
<div class="paper-meta">
    <span>${paper.published_date || ''}</span>
    <span>${citeBadge || (paper.publisher || '')}</span>
</div>
```

- [ ] **Step 2: Add CSS styles for new badges**

```css
.source-badge.dblp { background: #0891b2; color: #fff; }
.source-badge.s2 { background: #059669; color: #fff; }

.venue-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
    background: rgba(8, 145, 178, 0.15);
    color: #0891b2;
}

.acc-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
}
.acc-badge.oral { background: rgba(34,197,94,0.2); color: #22c55e; }
.acc-badge.spotlight { background: rgba(234,179,8,0.2); color: #eab308; }
.acc-badge.poster { background: rgba(107,114,128,0.2); color: #9ca3af; }

.cite-badge {
    font-size: 0.75rem;
    color: var(--text-secondary);
}
```

- [ ] **Step 3: Verify cards render correctly**

Load the page and check that existing papers still display properly (no venue/acceptance = no extra badges). New DBLP/S2 papers will show the new badges when data flows in.

- [ ] **Step 4: Commit**

```bash
git add js/app.js css/styles.css
git commit -m "feat: display venue, acceptance, citation count badges on paper cards"
```

---

### Task 8: Update filter bar for new sources

**Files:**
- Modify: `js/app.js`

- [ ] **Step 1: Update source filter options**

In `buildFilterOptions()`, update the source dropdown:

```javascript
renderFilterDropdown('source', [
    { value: 'arxiv', label: 'arXiv' },
    { value: 'crossref', label: '期刊' },
    { value: 'dblp', label: 'DBLP 会议' },
    { value: 'semantic_scholar', label: 'S2 搜索' },
]);
```

Add a new venue filter after the journal filter:

```javascript
const venues = {};
for (const p of allPapers) {
    if (p.venue) venues[p.venue] = (venues[p.venue] || 0) + 1;
}
_filterCounts.venues = venues;

renderFilterDropdown('venue',
    Object.entries(venues).sort((a,b) => b[1]-a[1]).map(([v, c]) => ({ value: v, label: v, count: c }))
);
```

- [ ] **Step 2: Add venue filter to `activeFilters` and renderPapers**

Add `venue: new Set()` to the `activeFilters` object initialization (line 4).

Add venue filter dropdown HTML in `index.html` filter bar (after journal dropdown):

```html
<div class="filter-dropdown" id="dd-venue">
    <button class="filter-dropdown-btn" onclick="toggleDropdown('venue')">
        会议 <span class="badge" id="badge-venue" style="display:none">0</span> <span class="arrow">▼</span>
    </button>
    <div class="filter-dropdown-panel" id="panel-venue"></div>
</div>
```

Add venue filter logic in `renderPapers()`:

```javascript
const venueSet = activeFilters.venue;
if (venueSet.size > 0) {
    filteredPapers = filteredPapers.filter(p => venueSet.has(p.venue));
}
```

- [ ] **Step 3: Commit**

```bash
git add js/app.js index.html
git commit -m "feat: add DBLP/S2 source filter and venue filter to filter bar"
```

---

### Task 9: Update detail modal for venue and citation info

**Files:**
- Modify: `js/app.js`

- [ ] **Step 1: Add venue/citation to detail modal header**

In `openPaperDetail()`, after the sourceBadge line, add venue info:

```javascript
const venueInfo = paper.venue ? ` <span class="venue-badge">${paper.venue}</span>` : '';
const accInfo = paper.acceptance ? ` <span class="acc-badge ${paper.acceptance}">${paper.acceptance}</span>` : '';
const citeInfo = paper.citation_count ? ` <span class="cite-badge">&#9733; ${paper.citation_count} citations</span>` : '';
```

Update the header in the template:

```javascript
<div class="paper-header">${sourceBadge}${venueInfo}${accInfo}
    <span class="paper-cat">${paper.published_date || ''}</span>
</div>
```

Add citation info after the authors line:

```javascript
${citeInfo ? `<div style="margin-bottom:8px">${citeInfo}</div>` : ''}
```

- [ ] **Step 2: Commit**

```bash
git add js/app.js
git commit -m "feat: show venue, acceptance, citations in paper detail modal"
```

---

### Task 10: End-to-end integration test

**Files:**
- None (manual test)

- [ ] **Step 1: Start daemon**

```bash
python3 daemon.py --port 8080
```

- [ ] **Step 2: Subscribe to Science journal via UI**

Open `http://localhost:8080`, click gear, search "Science", follow.

- [ ] **Step 3: Subscribe to CVPR conference**

In subscription modal, Conferences tab, check CVPR.

- [ ] **Step 4: Trigger all jobs**

```bash
curl -X POST http://localhost:8080/api/trigger/crossref
curl -X POST http://localhost:8080/api/trigger/dblp
curl -X POST http://localhost:8080/api/trigger/s2
```

- [ ] **Step 5: Verify data on frontend**

Reload page. Check:
- Source filter shows all 4 source types with counts
- DBLP papers show venue badge ("CVPR 2025")
- S2 papers show citation count
- No duplicate papers (same DOI from different sources should not appear twice)
- Subscription modal shows 3 tabs with correct content

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "test: multi-source integration verified"
```
