# arxivSCI-daily

多源学术论文订阅守护进程，集成 AI 深度筛选。支持 arXiv、Crossref 期刊、DBLP 会议、Semantic Scholar 四大数据源，AI 自动生成中文解读、质量评分和推荐等级，前端提供多维筛选和 CCF 分级展示。

## Quick Start

```bash
pip install -r requirements.txt
cp ai/.env.example ai/.env  # 配置 DeepSeek API key
python3 daemon.py --port 8080
# http://localhost:8080
```

## 系统架构

```
arXiv (3h) ──┐
Crossref (24h) ──┤── crawl_iter() ──→ _append_paper(enhance=True)
DBLP (24h)    ──┤                      ↓
S2 Search (24h)─┘                  enhance_single() → DeepSeek
                                      ↓
                               data/YYYY-MM-DD_AI_enhanced_Chinese.jsonl
                                      ↓
                               run_digest_job() → digests/YYYY-MM-DD.md
```

## 数据源

| 源 | 爬虫 | 调度 | 说明 |
|:---|:-----|:-----|:-----|
| arXiv | `crawler/arxiv_crawler.py` | 3h | 按 category 订阅 |
| Crossref | `crawler/crossref_crawler.py` | 24h | 期刊订阅（Nature 等），仅保留 research |
| DBLP | `crawler/dblp_crawler.py` | 24h | 55 个 CCF 会议（AI/数据/图形/理论/SE/网络/安全/体系/HCI） |
| S2 | `crawler/s2_crawler.py` | 24h | 关键词搜索，复用 research_profile.json |

## Paper 模型

```
id, source, title, summary, authors, categories, doi, published_date,
url, pdf, publisher, journal_title, issn, comment, article_type,
venue, acceptance, citation_count, version,
AI: { tldr, motivation, method, result, conclusion,
      zh_summary, relevance_score, quality_score, recommendation }
```

## 前端功能

| 功能 | 说明 |
|:-----|:-----|
| 筛选栏 | 6 下拉（来源/期刊/会议/领域/类型/收藏）+ 日期 + 7种排序 |
| 卡片 | source + venue + acceptance + rec + AI badge + Q/R 评分条 + TL;DR + 收藏 + 已读 |
| 详情弹窗 | AI 解读 + 中文摘要 + 英文 Abstract + BibTeX 一键复制 |
| 订阅管理 | 5-tab：arXiv 分类 / CCF 期刊 / CCF 会议 / S2 搜索 / 通知(预留) |
| CCF 分级 | 第七版完整目录，130+ 会议 80+ 期刊，A/B/C 彩色标签 + 筛选 |
| 排序 | 日期升降、AI 相关性/质量/引用、推荐优先、按来源分组 |
| 研究方向 | direction + keywords + quality_criteria |
| 键盘快捷键 | j/k 翻页, f 收藏, / 搜索, ? 帮助 |
| 主题切换 | 深色/亮色，跟随系统偏好，localStorage 记忆 |

## API 端点

| 端点 | 方法 | 说明 |
|:-----|:-----|:-----|
| `/api/papers` | GET | 论文列表，DOI+ID 双维度去重 |
| `/api/subscriptions` | GET/PUT | 订阅管理 |
| `/api/profile` | GET/PUT | 研究方向配置 |
| `/api/digest/<date>` | GET | 每日综述 Markdown |
| `/api/digests` | GET | 可用综述日期列表 |
| `/api/trigger/<job>` | POST | 手动触发（arxiv/crossref/dblp/s2） |
| `/api/trigger/enhance` | POST | 批量补 AI 增强 |
| `/api/export/bibtex` | POST | BibTeX 导出 |
| `/api/jobs` | GET | 后台任务状态 |
| `/api/stats` | GET | 统计信息 |

## 配置

```bash
ai/.env                    # DeepSeek API key
research_profile.json      # 研究方向 + 关键词
subscriptions.json         # 订阅配置（期刊/会议/搜索关键词）
```

## 项目结构

```
├── daemon.py              # Flask API + Scheduler
├── crawler/
│   ├── arxiv_crawler.py   # arXiv category 订阅
│   ├── crossref_crawler.py # Crossref 期刊订阅
│   ├── dblp_crawler.py    # DBLP 会议爬取 (55 venues)
│   ├── s2_crawler.py      # Semantic Scholar 关键词搜索
│   ├── enhance.py         # AI 增强 (DeepSeek)
│   ├── models.py          # Paper dataclass
│   └── subs_store.py      # 订阅持久化
├── ai/
│   └── .env               # API key (gitignored)
├── js/
│   ├── app.js             # 主前端逻辑
│   ├── ccf-data.js        # CCF 第七版数据 (130+ 会议, 80+ 期刊)
│   ├── subscriptions.js   # 订阅管理 UI
│   └── crossref-search.js # 期刊搜索
├── css/
│   ├── styles.css         # 主题 + 组件样式
│   └── subscriptions.css  # 订阅面板样式
├── index.html             # SPA 入口
└── data/                  # 论文 JSONL (gitignored)
```

## 已知限制

- S2 API 无 key 时会 429 rate limit
- DBLP 论文摘要依赖 OpenAlex，部分论文可能无 DOI
- 通知 tab 为预留 UI，后端未实现
- 前端收藏/已读状态仅 localStorage

## 后续方向

- 通知系统（邮件/微信/Telegram）
- 收藏/已读后端持久化
- 论文笔记功能
- S2 API key 集成
- AI 增强并发控制
- 移动端手势支持
