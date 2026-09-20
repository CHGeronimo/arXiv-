<div align="center">

# 📡 arXiv Daily Dispatch

**arxivSCI-daily · Personalized Research Intelligence Daemon**

<img src="docs/social-preview.png" alt="arXiv Daily Dispatch" width="640"/>

[![中文](https://img.shields.io/badge/README-中文-red)](README.md)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Web-Flask-000000?logo=flask)
![SQLite](https://img.shields.io/badge/Storage-SQLite_WAL-003B57?logo=sqlite&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-GLM_·_DeepSeek_·_OpenAI--compatible-3859FF)
![Tests](https://img.shields.io/badge/tests-34/34-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

A self-hosted research literature intelligence station: six discovery sources
are crawled automatically every night (pipelined: papers stream into AI
analysis as they are fetched), a tiered LLM pipeline filters and deeply
annotates them in Chinese, your likes / dislikes / notes feed back into scoring
and retrieval, and a weekly/monthly trend radar plus knowledge graph show you
what is happening in your field — with the AI provider, per-task models,
schedules and listen address all configurable from the web UI.

</div>

---

## ✨ Highlights

### 🔎 Discovery — six sources, staggered nightly

- **arXiv** category subscriptions (auto backfill after ≥2-day downtime)
- **Crossref** journal subscriptions (research articles only)
- **DBLP** 55 CCF venues (rotated coverage)
- **OpenAlex** keyword search — an LLM two-stage expander turns your research
  direction into 40–90 queries (concept mining + abbreviation/subfield variants);
  liked topics are folded in, disliked ones excluded
- **Semantic Scholar** author tracking (name / ORCID)
- **Citation tracing** — follows citations in and out of "must-read ∪ liked"
  anchor papers, rotating anchors across days (free OpenAlex quota)

### 🧠 Tiered AI pipeline (cheap where possible, deep where it matters)

```
local rule pre-filter (zero tokens) → quick_filter (thinking off, seconds)
  → deep enhancement (thinking on: Chinese TLDR / motivation / method / result
    / conclusion, relevance × quality scores, 4-level recommendation reasons)
  → optional full-text deep reading (ar5iv fetch, budget-capped)
```

- **Per-task models**: 10 pipeline tasks (quick filter / keywords / topics /
  clustering / enhancement / fulltext / trend / digest / knowledge cards / idea
  check) can each pin its own model — flash for volume tasks, the strongest
  model for deep reading; empty = follow the default
- **Adaptive thinking flag**: the GLM-specific `thinking` parameter is only sent
  to bigmodel endpoints; DeepSeek and other OpenAI-compatible APIs skip it
- **Time-aware dynamic rate limiting + priority slot**: daytime concurrency 6 (measured)
  with jittered exponential backoff and SDK retries disabled; **automatically relaxed in
  the off-peak night window** (default 00:00–08:00: concurrency 9, halved interval —
  window and both tiers adjustable in the ⚙️ panel, effective live without restart);
  one slot is reserved for interactive single-shot jobs (digest / trend / idea) so they
  never queue behind a crawl storm

### 🔁 Feedback loop — it learns your direction

- Like / dislike / note on any paper; notes are automatically academicized and
  distilled into liked/disliked topics
- Topics are injected into scoring prompts and keyword mining; your recent
  notes enter the scoring context at highest priority
- Topic dedup is LLM-based with a safety guard (never wipes the topic list);
  a scoring×feedback confusion matrix is auditable

### 📊 Five frontend pages

| Page | Features |
|:-----|:-----|
| Daily papers | three-level cards, 4-level recommendation labels with reasons, morning-reading / must-read / starred presets, side-by-side compare, batch BibTeX export, ignored-papers review, code links |
| Knowledge graph | knowledge cards, d3 force clustering, L1/L2/L3 navigation |
| Trend radar | weekly/monthly Chinese reports (emerging methods / opportunities / field migration) + browsable archive |
| Idea workbench | submit an idea → AI retrieves prior work and analyzes differentiation |
| Daily digest | markdown briefing with GFM tables, a morning preset, and an in-page generate button (auto-loads when done) |

Also: grouped sidebar filters + search + 8 sort orders (including ⏱ ingested-time — newest arrivals on top), CCF catalog labels
(130+ venues / 80+ journals), 4 themes, keyboard shortcuts (`j`/`k`, `f`, `/`, `?`),
skeleton loading, and code-version observability (page vs disk).

### 🎛 Everything configurable in the web UI

| Section | What you can change | Takes effect |
|:-----|:-----|:-----|
| Schedule & rate limits | daily start hour (any 0-23), LLM night window / two concurrency tiers, task staggering, run-on-start, DBLP/S2 rotation, local pre-filter | immediately (scheduler replans) |
| 🔑 AI provider | GLM coding plan / GLM pay-as-you-go / DeepSeek / custom OpenAI-compatible endpoint; validated with a live test call before saving; per-provider key memory; stale per-task model overrides auto-cleared on switch | immediately, no restart |
| 🎛 Task models | default model + per-task overrides for 10 tasks (empty = follow default), with provider-aware suggestions | immediately, no restart |
| 🌐 Listen address | bind IP (127.0.0.1 / 0.0.0.0 / specific IPv4) and port, with a LAN security warning | on daemon restart (panel shows "⟳ pending restart") |

The top bar splits actions by responsibility, plus a global **⚡ job center** — a
persistent button showing the count of running jobs (pulsing), opening a panel with
per-job **progress bars + n/N + speed + ETA** and ✓ summaries; a 3px gradient bar at
the very top of the page reflects live crawl-batch progress (papers streaming in):

- **🔄 Crawl**: trigger any of the five sources individually (with status counts) or all at once, outside the night window
- **🤖 AI processing**: retro enhancement / knowledge-card extraction / graph re-clustering / full-text analysis / ♻️ re-run stale pipeline results (identified by PIPELINE_VERSION, resumable)
- **⚙️ System settings**: the four config sections above + the **🧪 system
self-test** — 34 lightweight smoke checks: one request per network source, a real
smoke run of **every LLM task** (quick filter / keywords / note academicization /
clustering / scoring / knowledge cards / fulltext / trend / digest / idea check),
API round-trips, data readiness, version stamp health, convergence config and stale counts,
plus SQLite / scheduler / code-version / frontend assets,
shown in a grouped ✓/⚠/✗ report, never a full crawl.

## 🚀 Quick Start

```bash
git clone https://github.com/CHGeronimo/arxivSCI-daily.git
cd arxivSCI-daily
pip install -r requirements.txt

cp backend/ai/.env.example backend/ai/.env
# edit backend/ai/.env with your GLM API key (free at https://open.bigmodel.cn)
# (or leave it and paste the key in the ⚙️ settings panel after startup)

python3 daemon.py --port 8080
# open http://localhost:8080
```

Personal runtime files (`research_profile.json`, `subscriptions.json`,
`data/papers.db`, `backend/ai/.env`) are auto-generated / gitignored — never committed.
Bind precedence: `--host/--port` CLI args > panel settings (`DAEMON_HOST/PORT` in
`.env`) > default 127.0.0.1:8080.

## 🔌 API (55 endpoints)

Full list in `backend/api.py` — papers (up to 50k lightweight), subscriptions &
profile, field-level feedback with note academicization, provider switching
(`llm-config`), per-task models (`llm-models`), masked key management
(`llm-key`), listen address (`bind`), manual triggers for every job,
jobs/stats observability, weekly/monthly trend radars, BibTeX export, digests.

## 🧪 Tests

```bash
for t in tests/test_*.py; do LOG_DIR=/tmp python3 "$t"; done
```

34 regression scripts, fully mocked (no API quota consumed). Ops scripts in
`scripts/`: discovery-quality audit, code-URL backfill, topic cleanup,
feedback-loop verification.

## 📁 Structure

```
daemon.py            # thin entry (python daemon.py unchanged)
backend/             # Python package: daemon/api/db/jobs/paper_store/ccf_map
                     #   + ai/ (LLM pipeline) + crawler/ (six sources)
web/                 # SPA: index.html + js/ + css/ (4 themes) + vendor/
scripts/  tests/  docs/
```

## 📄 License & Citation

MIT — see [LICENSE](LICENSE). If this helps your research, cite via the
"Cite this repository" button (powered by [CITATION.cff](CITATION.cff)).

## 🙏 Acknowledgments

The initial architecture (arXiv crawling + AI summaries + web display) was
inspired by [dw-dengwei/daily-arXiv-ai-enhanced](https://github.com/dw-dengwei/daily-arXiv-ai-enhanced).
The current version is a complete rebuild: Flask daemon + SQLite storage, six
discovery sources, citation tracing, the scoring/feedback loop, trend radar,
knowledge graph, full-text deep reading and full web-UI configurability are all
original implementations. See the [Chinese README](README.md) for full docs.
