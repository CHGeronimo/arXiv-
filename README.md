# arxivSCI-daily

Dual-source academic paper subscription daemon: arXiv + Crossref journals.

## Quick Start

```bash
pip install -r requirements.txt
cp ai/.env.example ai/.env  # Configure DeepSeek API key
python3 daemon.py --port 8080
```

Open http://localhost:8080

## Architecture

```
daemon.py (Flask API + Scheduler)
├─ arXiv crawler: every 3h, httpx + python-arxiv SDK
├─ Crossref crawler: every 24h, httpx
├─ AI enhancement: DeepSeek via langchain
└─ Web UI: vanilla JS, dark theme
```

## Features

- **Dual source**: arXiv categories + Crossref journal ISSN subscription
- **Streaming crawl**: papers available via API as soon as each is fetched
- **AI enhancement**: TL;DR, motivation, method, result, conclusion (Chinese)
- **Search**: keyword filter across title, abstract, authors
- **Auto-refresh**: frontend polls every 15s
- **Responsive**: mobile-friendly layout

## API

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/subscriptions` | GET | Read subscriptions |
| `/api/subscriptions` | PUT | Update subscriptions |
| `/api/papers` | GET | List papers (`?source=arxiv&page=1&per_page=50`) |
| `/api/stats` | GET | Paper counts by source |

## Configuration

`subscriptions.json`:

```json
{
  "arxiv": { "categories": ["cs.CV", "cs.CL"] },
  "crossref": { "journals": [{"issn": "0028-0836", "name": "Nature"}] }
}
```

`ai/.env`:

```
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-v4-flash
```
