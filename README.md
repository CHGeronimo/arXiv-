# arxivSCI-daily

多源学术论文订阅守护进程，集成 AI 深度筛选。支持 arXiv、Crossref 期刊、DBLP 会议、OpenAlex 搜索、S2 Author 五大数据源，AI 自动生成中文解读、质量评分和推荐等级，前端提供侧边栏筛选、4 套主题和 CCF 分级展示。

## Quick Start

```bash
pip install -r requirements.txt
cp ai/.env.example ai/.env  # 配置 GLM API key（https://open.bigmodel.cn）
python3 daemon.py --port 8080
# http://localhost:8080
```

首次启动自动迁移已有 JSONL 数据到 SQLite，无需手动操作。

## 系统架构

```
arXiv (02:00, 串联分析链) ──┐
Crossref (02:30) ──┤── BaseCrawlerJob.run()
DBLP (03:00)    ──┤      ↓
OpenAlex (03:30)─┤   crawl_iter() → append_paper(enhance=True)
S2 Author (04:00)─┘      ↓
                   quick_filter → enhance_single() → GLM
                        ↓
                  data/papers.db (SQLite WAL)
                        ↓
                 run_digest_job() → digests/YYYY-MM-DD.md
```

自动任务每天凌晨 2 点起、每 30 分钟错峰一个（`NIGHT_START`/`STAGGER_MINUTES` 可调，`RUN_ON_START=1` 启动即跑一轮）；UI/API 手动触发不受时间限制。所有 OpenAlex 请求经共享节流客户端（全局最小间隔 + 429 退避，`OPENALEX_EMAIL` 进 polite pool）。

## 数据源

| 源 | 爬虫 | 调度 | 说明 |
|:---|:-----|:-----|:-----|
| arXiv | `crawler/arxiv_crawler.py` | 每日 02:00 | 按 category 订阅，后续串联增强/知识卡片/全文分析/digest |
| Crossref | `crawler/crossref_crawler.py` | 每日 02:30 | 期刊订阅（Nature 等），仅保留 research |
| DBLP | `crawler/dblp_crawler.py` | 每日 03:00 | 55 个 CCF 会议（AI/数据/图形/理论/SE/网络/安全/体系/HCI） |
| OpenAlex | `crawler/openalex_crawler.py` | 每日 03:30 | LLM扩展关键词+语义搜索，替代S2 |
| Author | `crawler/author_crawler.py` | 每日 04:00 | S2 Author API + ORCID 辅助查找 |

## 存储层

SQLite 数据库（`data/papers.db`），WAL 模式支持并发读写。

```sql
papers        — 论文元数据（id, source, title, summary, authors, ...）
ai_results    — AI 增强结果（tldr, motivation, method, result, ...）
feedback      — 用户反馈（useful/not_useful）
digests       — 每日综述 Markdown
subscriptions — 订阅配置
```

关键设计：
- **写队列**：后台线程批量写入（每50条或100ms刷盘），避免阻塞爬虫
- **自动迁移**：启动时检测 JSONL 数据自动导入 SQLite
- **索引**：papers(source), papers(published_date), ai_results(recommendation), ai_results(relevance_score)

## Paper 模型

```
id, source, title, summary, authors, categories, doi, published_date,
url, pdf, publisher, journal_title, issn, comment, article_type,
venue, acceptance, citation_count, version,
AI: { tldr, motivation, method, result, conclusion,
      summary_zh, title_zh, relevance_score, quality_score, recommendation }
```

## 前端功能

| 功能 | 说明 |
|:-----|:-----|
| 侧边栏筛选 | 可收起侧边栏，分组折叠式（来源/会议/期刊/领域/推荐/收藏）+ 搜索 + 日期 + 7 种排序 |
| 卡片三级层次 | 标题（加粗）→ TLDR（始终可见）→ 元信息（作者/日期/引用），点击查看完整 AI 解读 |
| 详情弹窗 | AI 解读（TLDR+Motivation+Method+Result+Conclusion）+ 中文摘要 + Abstract + BibTeX |
| 订阅管理 | 6-tab：arXiv 分类 / CCF 期刊 / CCF 会议 / 作者 / 搜索 / 通知(预留) |
| 作者订阅 | S2 Author API 搜索 + ORCID 辅助查找，卡片/详情中作者名可点击快速订阅 |
| 4 套主题 | 深色（默认）/ 浅色极简 / 学术白底 / 暖色暗黑，纯 CSS 变量一键切换 |
| CCF 分级 | 第七版完整目录，130+ 会议 80+ 期刊，A/B/C 彩色标签 + 筛选 |
| 键盘快捷键 | j/k 翻页, f 收藏, / 搜索, ? 帮助 |
| 侧边栏触发 | header 按钮点击 + 左边缘 hover 自动展开 |

## AI 关键词扩展

OpenAlex 搜索前，LLM 两阶段扩展关键词（目标 40-90 条查询）：
1. **方向挖掘**：穷举（中文）研究方向描述中的每个研究概念——问题设定/方法论/理论工具/机制/评估性质/应用域，译为标准英文检索术语；liked 主题纳入挖掘，disliked 主题排除
2. **查询扩展**：为种子+概念生成变体——缩写/全称（NeRF ↔ neural radiance fields）、子方向（diffusion models → score-based generative models）、新式表述（MARL → LLM-based multi-agent coordination）
- 缓存：direction/种子/反馈不变时复用上次结果；LLM 失败时回退到种子关键词

## API 端点

| 端点 | 方法 | 说明 |
|:-----|:-----|:-----|
| `/api/papers` | GET | 论文列表，SQLite 索引查询 |
| `/api/subscriptions` | GET/PUT | 订阅管理（期刊/会议/作者/搜索关键词） |
| `/api/profile` | GET/PUT | 研究方向配置（PUT 合并保存，保留 liked/disliked 等反馈字段） |
| `/api/extract-keywords` | POST | 从研究方向 LLM 两阶段提取搜索关键词（direction 必填） |
| `/api/author/search` | GET | S2 Author 搜索（query=姓名或ORCID） |
| `/api/trigger/<job>` | POST | 手动触发（arxiv/crossref/dblp/s2/author） |
| `/api/trigger/enhance` | POST | 批量补 AI 增强 |
| `/api/export/bibtex` | POST | BibTeX 导出 |
| `/api/feedback` | POST/GET | 论文反馈（写入 SQLite feedback 表） |
| `/api/digest/<date>` | GET | 每日综述 Markdown |
| `/api/digests` | GET | 可用综述日期列表 |
| `/api/jobs` | GET | 后台任务状态 |
| `/api/stats` | GET | 统计信息（SQLite 聚合查询） |

## 配置

```bash
ai/.env                    # GLM API key + base URL + 模型名
research_profile.json      # 研究方向 + 关键词（LLM 自动扩展）
subscriptions.json         # 订阅配置（期刊/会议/作者/搜索关键词）
data/papers.db             # SQLite 数据库（自动创建+迁移）
```

## 项目结构

```
├── daemon.py              # 入口：argparse + app factory + scheduler
├── api.py                 # Flask 路由（12个端点）
├── db.py                  # SQLite 连接池 + 写队列 + schema
├── jobs.py                # BaseCrawlerJob + Scheduler
├── paper_store.py         # SQLite CRUD 层
├── migrate_jsonl.py       # JSONL→SQLite 自动迁移
├── crawler/
│   ├── arxiv_crawler.py   # arXiv category 订阅
│   ├── crossref_crawler.py # Crossref 期刊订阅
│   ├── dblp_crawler.py    # DBLP 会议爬取 (55 venues)
│   ├── openalex_crawler.py # OpenAlex 语义搜索（替代S2）
│   ├── author_crawler.py  # S2 Author API + ORCID 辅助查找
│   ├── enhance.py         # AI 增强 (GLM)
│   ├── models.py          # Paper dataclass
│   └── subs_store.py      # 订阅持久化（含 Author dataclass）
├── ai/
│   ├── .env               # API key (gitignored)
│   ├── enhance.py         # 统一 AI 增强入口
│   ├── keyword_expander.py # LLM 关键词扩展
│   ├── quick_filter.py    # 快速相关性预筛
│   ├── structure.py       # LangChain 输出结构
│   ├── digest.py          # 每日综述生成
│   ├── system.txt         # AI 系统提示
│   └── template.txt       # AI 用户提示模板
├── js/
│   ├── app.js             # 入口 + 事件绑定 (ES module)
│   ├── state.js           # 共享状态 + 主题 + 侧边栏状态
│   ├── api.js             # API 调用封装
│   ├── filters.js         # 侧边栏筛选/排序逻辑
│   ├── render.js          # 论文卡片渲染 + 分页
│   ├── modal.js           # 论文详情/个人资料模态框
│   ├── subscriptions.js   # 订阅管理 UI（含作者搜索）
│   ├── ccf-data.js        # CCF 第七版数据
│   └── crossref-search.js # 期刊搜索
├── css/
│   ├── styles.css         # 4套主题变量 + 组件样式
│   ├── sidebar.css        # 侧边栏筛选面板样式
│   └── subscriptions.css  # 订阅面板样式
├── index.html             # SPA 入口
└── data/                  # SQLite DB (gitignored)
```

## 已知限制

- S2 Author API 无 key 时会 429 rate limit（仅影响作者订阅功能）
- DBLP 论文摘要依赖 OpenAlex，部分论文可能无 DOI
- 通知 tab 为预留 UI，后端未实现
- ES module (app.js) 与普通 script (subscriptions.js) 通过 window. 桥接

## 测试

```bash
tests/*.py  # 9 个回归测试：路由黑名单/LLM故障不误杀/本地预筛/聚类回退/
            # 收藏后端化+digest窗口/关键词扩展/提取端点/调度器/OpenAlex节流
```

## 后续方向

- 通知系统（邮件/微信/Telegram）
- 收藏/已读后端持久化（SQLite feedback 表已就绪）
- 论文笔记功能
- subscriptions.json 迁移到 SQLite subscriptions 表
- 移动端手势支持
