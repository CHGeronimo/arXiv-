# AI 筛选精度 + 性能优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提升 AI 筛选精度（减少 skip 率，增加推荐区分度）+ 性能优化（增量缓存、并发、两步架构）

**Architecture:** 1) Prompt 重写注入完整研究方向+反馈样本 2) 两步筛选：快筛分类→精选深度分析 3) 增量缓存避免重复增强 4) 并发提升 5) 前端反馈闭环

**Tech Stack:** Python (langchain, pydantic), Flask, vanilla JS, DeepSeek API

---

## 当前痛点数据

```
Recommendation: skip 71.9% / skim 21.1% / worth-reading 7.0% / must-read 0%
Quality score: min=0, max=8, avg=6.4
Relevance score: min=0, max=6, avg=1.5  (10分制，均分只有1.5)
Sources: arxiv 575, dblp 85, crossref 27
Enhancement: max_workers=1, 串行处理
```

## 关键文件

| 文件 | 行数 | 职责 |
|:-----|:-----|:-----|
| `ai/system.txt` | 23 | AI system prompt（评分规则） |
| `ai/template.txt` | 10 | AI human prompt（注入变量） |
| `ai/structure.py` | 15 | Pydantic 输出结构定义 |
| `ai/enhance.py` | 425 | 增强主逻辑（enhance_single, build_chain, CLI） |
| `daemon.py` | 671 | Flask API + Scheduler（_append_paper, _get_ai_chain） |
| `js/app.js` | 738 | 前端主逻辑（渲染、筛选、详情） |
| `research_profile.json` | 14 | 研究方向配置 |

---

### Task 1: 重写 AI Prompt — 注入完整研究方向 + 调整评分阈值

**Files:**
- Modify: `ai/system.txt`
- Modify: `ai/template.txt`
- Modify: `ai/structure.py`

**当前问题：**
- system.txt 评分规则太泛（relevance>=5 就是 worth-reading）
- template.txt 只注入 direction 和 keywords，没用 quality_criteria
- research_profile 的 direction 是"研究雷达和体征感知、博弈论以及多智能体"但 keywords 是"neural rendering, 3D reconstruction"——两者不一致，AI 被混淆

- [ ] **Step 1: 重写 system.txt**

```
You are a professional paper analyst for a CS PhD researcher.
Provide concise, detailed, and precise answers using correct terminology.
Output in {language}. Respond with valid JSON matching the specified schema.

Prohibited content: politics, ethnicity, religion, violence, pornography, terrorism, gambling, regional discrimination. If detected, set recommendation to "skip" and leave other fields as default.

## Scoring Calibration

You MUST produce a well-distributed scoring curve. Follow these rules strictly:

### quality_score (1-10): Paper's academic quality independent of relevance
- 1-2: Trivial or poorly executed
- 3-4: Incremental contribution, limited novelty
- 5-6: Solid work with reasonable evaluation
- 7-8: Significant advance with strong experimental support
- 9-10: Potentially field-changing breakthrough

### relevance_score (1-10): How relevant to the user's SPECIFIC research
- 1-2: Different field entirely
- 3-4: Adjacent field, could have some methodological cross-pollination
- 5-6: Shares techniques or applications with user's research
- 7-8: Directly addresses a problem in the user's research area
- 9-10: Core paper the user would likely cite

### recommendation: Combined judgment with adjusted thresholds
- "must-read": relevance_score >= 8 AND quality_score >= 7 (about 3-5%)
- "worth-reading": relevance_score >= 6 AND quality_score >= 5 (about 15-25%)
- "skim": relevance_score >= 4 OR quality_score >= 6 (about 30-40%)
- "skip": relevance_score < 4 AND quality_score < 6 (about 30-40%)

IMPORTANT: You must actively differentiate papers. If a paper is only tangentially related, score it honestly low on relevance. Do NOT default to high scores.

JSON fields:
- "tldr": one-sentence key contribution (max 200 chars)
- "motivation": what problem and why it matters (2-3 sentences)
- "method": proposed approach (2-3 sentences)
- "result": key experimental results with metrics (2-3 sentences)
- "conclusion": main takeaways and limitations (1-2 sentences)
- "title_zh": Chinese title translation
- "summary_zh": Chinese abstract translation (preserve technical terms in English)
- "quality_score": integer 1-10
- "relevance_score": integer 1-10
- "recommendation": one of "must-read", "worth-reading", "skim", "skip"
- "skip_reason": only when recommendation is "skip", one sentence explaining why (empty string otherwise)
```

- [ ] **Step 2: 重写 template.txt**

```
## Researcher Profile
Direction: {research_direction}
Keywords: {keywords}
Quality Criteria: {quality_criteria}
Preferred Topics: {liked_topics}
Disliked Topics: {disliked_topics}

## Paper to Analyze
Title: {title}

Abstract:
{content}
```

- [ ] **Step 3: 更新 structure.py 添加 skip_reason 字段**

在 `Structure` 类中添加：
```python
skip_reason: str = Field(default="", description="when skip: one sentence why; otherwise empty string")
```

- [ ] **Step 4: 验证**

```bash
python3 -c "from ai.structure import Structure; print('OK')"
python3 -c "
from ai.enhance import build_chain
chain = build_chain('deepseek-v4-flash')
print('Chain built OK')
"
```

---

### Task 2: 增量增强缓存 — 避免重复处理已增强论文

**Files:**
- Modify: `daemon.py` (`_append_paper`, `_load_existing_ids`)

**当前问题：**
- `_append_paper` 中 enhance=True 时直接调用 enhance_single，没有检查该论文是否已在 AI_enhanced 文件中
- `run_retro_enhance` 用 `_written_ids` 检查，但这是内存中的 set，daemon 重启后丢失
- 应该从 AI_enhanced JSONL 文件构建已增强 ID set

- [ ] **Step 1: 添加 `_load_enhanced_ids()` 函数**

在 `daemon.py` 中 `_load_existing_ids()` 之后添加：

```python
def _load_enhanced_ids() -> set[str]:
    """Load IDs of papers that already have AI enhancement."""
    enhanced: set[str] = set()
    if not DATA_DIR.exists():
        return enhanced
    for f in DATA_DIR.glob("*_AI_enhanced_*.jsonl"):
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    data = json.loads(line.strip())
                    pid = data.get("id") or data.get("doi", "")
                    if pid:
                        enhanced.add(pid)
                except (json.JSONDecodeError, KeyError):
                    pass
    return enhanced
```

- [ ] **Step 2: 修改 `_append_paper` 使用增强缓存**

在 `_append_paper` 的 `if enhance:` 分支中，增加缓存检查：

```python
if enhance:
    # Skip if already enhanced
    if paper.id in _enhanced_ids:
        with _ids_lock:
            _written_ids.add(paper.id)
        return False
    try:
        chain, profile = _get_ai_chain()
        ...
```

- [ ] **Step 3: 添加全局 `_enhanced_ids` set 并在启动时加载**

```python
_enhanced_ids: set[str] = set()

# In main() or init, after DATA_DIR setup:
_enhanced_ids = _load_enhanced_ids()
logger.info(f"Loaded {len(_enhanced_ids)} already-enhanced paper IDs")
```

- [ ] **Step 4: 在增强成功后更新 `_enhanced_ids`**

在 `_append_paper` 和 `run_retro_enhance` 中，增强成功后：
```python
_enhanced_ids.add(paper.id)
```

---

### Task 3: 并发提升 — max_workers 可配置

**Files:**
- Modify: `daemon.py` (`_get_ai_chain` area, `_append_paper`)

**当前问题：**
- `_append_paper` 中 enhance_single 是同步调用，在爬取流中每次只处理一篇
- 各数据源 crawler 是生成器模式，每个 paper 逐个 yield
- 最有效的方式是在 `_append_paper` 层面不做并发（因为爬取是流式的），而是在 `run_retro_enhance` 中使用并发

- [ ] **Step 1: 添加 AI_MAX_WORKERS 环境变量**

在 daemon.py 全局区域添加：
```python
_ai_max_workers = int(os.environ.get("AI_MAX_WORKERS", "3"))
```

- [ ] **Step 2: 修改 `run_retro_enhance` 使用并发**

将 retro_enhance 从逐个处理改为批量+并发：

```python
def run_retro_enhance():
    logger.info("Starting retro-enhance for papers without AI data")
    try:
        chain, profile = _get_ai_chain()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ai_path = DATA_DIR / f"{today}_AI_enhanced_{_ai_language}.jsonl"

        # Collect unenhanced papers
        to_enhance = []
        for f in sorted(DATA_DIR.glob("*.jsonl")):
            if "_AI_" in f.name:
                continue
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        p = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    pid = p.get("id", "")
                    if pid in _enhanced_ids or pid in _written_ids:
                        continue
                    if not p.get("summary") and not p.get("title"):
                        continue
                    to_enhance.append(p)

        if not to_enhance:
            logger.info("No papers to retro-enhance")
            return

        logger.info(f"Retro-enhance: {len(to_enhance)} papers to process")

        enhanced_count = 0
        with ThreadPoolExecutor(max_workers=_ai_max_workers) as executor:
            futures = {
                executor.submit(enhance_single, p, chain, profile, _ai_language): p
                for p in to_enhance
            }
            for future in as_completed(futures):
                if _shutdown:
                    break
                p = futures[future]
                try:
                    result = future.result()
                    if result:
                        with open(ai_path, "a", encoding="utf-8") as af:
                            af.write(json.dumps(result, ensure_ascii=False) + "\n")
                        pid = p.get("id", "")
                        with _ids_lock:
                            _written_ids.add(pid)
                        _enhanced_ids.add(pid)
                        enhanced_count += 1
                except Exception as e:
                    logger.warning(f"Retro-enhance failed for {p.get('id','?')}: {e}")
                if enhanced_count % 10 == 0:
                    logger.info(f"Retro-enhance progress: {enhanced_count}/{len(to_enhance)}")

        logger.info(f"Retro-enhance done: {enhanced_count} papers enhanced")
    except Exception as e:
        logger.error(f"Retro-enhance job failed: {e}", exc_info=True)
```

需要在文件顶部添加 `from concurrent.futures import ThreadPoolExecutor, as_completed`。

- [ ] **Step 3: 验证**

```bash
python3 -c "from daemon import app; print('daemon import OK')"
```

---

### Task 4: 两步筛选架构 — 快筛 + 深度分析

**Files:**
- Create: `ai/quick_filter.py`
- Modify: `ai/structure.py` (添加 QuickFilter structure)
- Modify: `daemon.py` (修改 `_append_paper` 使用两步)

**设计：**
- 第一步：轻量模型（deepseek-chat）快速分类 → relevant / not-relevant
- 第二步：对 relevant 的论文做完整增强（deepseek-v4-flash）
- 这样 70% 的 skip 论文只需一次便宜的快筛调用

- [ ] **Step 1: 添加 QuickFilter structure**

在 `ai/structure.py` 中添加：

```python
class QuickFilter(BaseModel):
    is_relevant: bool = Field(description="whether this paper is relevant to the user's research direction and worth detailed analysis")
    relevance_reason: str = Field(description="one sentence explaining why relevant or not")
```

- [ ] **Step 2: 创建 `ai/quick_filter.py`**

```python
import os
import json
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .structure import QuickFilter

logger = logging.getLogger(__name__)

QUICK_SYSTEM = """You are a paper relevance classifier for a CS PhD researcher.
Given the paper title and abstract, and the researcher's profile, classify if this paper is relevant enough for detailed analysis.

IMPORTANT: Be generous — classify as relevant if there is ANY chance the paper relates to the researcher's work.
Only mark as not-relevant if the paper is clearly in a completely different field.

Respond with valid JSON: {"is_relevant": bool, "relevance_reason": "one sentence"}
"""

QUICK_TEMPLATE = """Research Direction: {research_direction}
Keywords: {keywords}

Paper Title: {title}

Abstract:
{content}"""


def build_quick_filter(model_name: str | None = None):
    model = model_name or os.environ.get("QUICK_FILTER_MODEL", "deepseek-chat")
    llm = ChatOpenAI(model=model).with_structured_output(QuickFilter, method="json_mode")
    prompt = ChatPromptTemplate.from_messages([
        ("system", QUICK_SYSTEM),
        ("human", QUICK_TEMPLATE),
    ])
    return prompt | llm


def quick_filter_paper(paper: dict, chain, profile: dict) -> bool:
    """Return True if paper should get full enhancement."""
    try:
        result: QuickFilter = chain.invoke({
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
            "title": paper.get("title", ""),
            "content": paper.get("summary", "")[:1000],  # truncate for speed
        })
        return result.is_relevant
    except Exception as e:
        logger.warning(f"Quick filter failed for {paper.get('id','?')}: {e}, defaulting to relevant")
        return True  # default to analyzing on failure
```

- [ ] **Step 3: 修改 `daemon.py` 集成两步架构**

添加全局快筛 chain：
```python
_quick_chain = None

def _get_quick_chain():
    global _quick_chain
    if _quick_chain is None:
        from ai.quick_filter import build_quick_filter
        _quick_chain = build_quick_filter()
        logger.info("Quick filter chain initialized")
    return _quick_chain
```

修改 `_append_paper`：
```python
if enhance:
    if paper.id in _enhanced_ids:
        ...
    # Step 1: Quick filter
    quick_chain = _get_quick_chain()
    chain, profile = _get_ai_chain()
    paper_dict = json.loads(paper.to_jsonl())
    if not quick_filter_paper(paper_dict, quick_chain, profile):
        # Not relevant — write to raw file only, mark as skip
        paper_dict["AI"] = {
            "tldr": "", "motivation": "", "method": "", "result": "", "conclusion": "",
            "title_zh": "", "summary_zh": "",
            "quality_score": 0, "relevance_score": 0, "recommendation": "skip",
            "skip_reason": "Filtered by quick relevance check",
        }
        ai_path = DATA_DIR / f"{date_str}_AI_enhanced_{_ai_language}.jsonl"
        with open(ai_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(paper_dict, ensure_ascii=False) + "\n")
        with _ids_lock:
            _written_ids.add(paper.id)
        _enhanced_ids.add(paper.id)
        return True
    # Step 2: Full enhancement for relevant papers
    try:
        enhanced = enhance_single(paper_dict, chain, profile, _ai_language)
        ...
```

- [ ] **Step 4: 添加 `QUICK_FILTER_MODEL` 到 ai/.env.example**

```
QUICK_FILTER_MODEL=deepseek-chat
```

---

### Task 5: 反馈闭环 — 前端"有用/没用"按钮

**Files:**
- Modify: `daemon.py` (添加反馈 API)
- Modify: `js/app.js` (添加反馈 UI)
- Modify: `research_profile.json` (添加 liked/disliked)

**设计：**
- 前端论文卡片添加 👍/👎 按钮
- 反馈存入 `feedback.json`（{paper_id: "useful"/"not_useful"}）
- `research_profile.json` 新增 `liked_topics` 和 `disliked_topics` 字段
- 反馈 API 接收 paper_id + rating，追加到 feedback.json
- 可选：定时从反馈数据中提取 topic pattern 更新 liked/disliked

- [ ] **Step 1: 添加反馈 API 端点**

在 `daemon.py` 中添加：

```python
FEEDBACK_FILE = BASE_DIR / "feedback.json"

@app.route("/api/feedback", methods=["POST"])
def save_feedback():
    data = request.json or {}
    paper_id = data.get("paper_id", "")
    rating = data.get("rating", "")  # "useful" or "not_useful"
    if not paper_id or rating not in ("useful", "not_useful"):
        return jsonify({"error": "invalid"}), 400

    feedback = {}
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, "r") as f:
            feedback = json.load(f)
    feedback[paper_id] = rating
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(feedback, f, indent=2, ensure_ascii=False)

    # Update liked/disliked topics in profile
    _update_profile_from_feedback(paper_id, rating)
    return jsonify({"status": "saved"})

@app.route("/api/feedback", methods=["GET"])
def get_feedback():
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, "r") as f:
            return jsonify(json.load(f))
    return jsonify({})
```

- [ ] **Step 2: 添加 `_update_profile_from_feedback` 函数**

```python
def _update_profile_from_feedback(paper_id: str, rating: str):
    """Update liked/disliked topics based on feedback."""
    profile_path = BASE_DIR / "research_profile.json"
    if not profile_path.exists():
        return
    with open(profile_path, "r") as f:
        profile = json.load(f)

    # Find paper to extract topics
    paper = None
    for f in DATA_DIR.glob("*_AI_enhanced_*.jsonl"):
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    p = json.loads(line.strip())
                    if p.get("id") == paper_id:
                        paper = p
                        break
                except json.JSONDecodeError:
                    pass
        if paper:
            break

    if not paper:
        return

    # Extract key terms from title
    title = paper.get("title", "")
    categories = paper.get("categories", [])

    if rating == "useful":
        liked = profile.get("liked_topics", [])
        if title not in liked:
            liked.append(title)
        profile["liked_topics"] = liked[-20:]  # keep last 20
    else:
        disliked = profile.get("disliked_topics", [])
        if title not in disliked:
            disliked.append(title)
        profile["disliked_topics"] = disliked[-20:]

    # Reset AI chain to pick up updated profile
    global _ai_chain, _ai_profile
    _ai_chain = None
    _ai_profile = None

    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
```

- [ ] **Step 3: 修改 enhance_single 注入 liked/disliked topics**

在 `ai/enhance.py` 的 `enhance_single` 中：

```python
response: Structure = chain.invoke({
    "language": language,
    "content": paper.get("summary", ""),
    "title": paper.get("title", ""),
    "research_direction": profile.get("direction", ""),
    "keywords": ", ".join(profile.get("keywords", [])),
    "quality_criteria": profile.get("quality_criteria", ""),
    "liked_topics": "\n".join(profile.get("liked_topics", [])[-5:]),
    "disliked_topics": "\n".join(profile.get("disliked_topics", [])[-5:]),
})
```

- [ ] **Step 4: 前端添加反馈按钮**

在 `js/app.js` 的卡片渲染中，在 bookmark 按钮旁添加：

```html
<button class="feedback-btn" data-feedback-id="${id}" data-feedback-rating="useful" title="有用">👍</button>
<button class="feedback-btn" data-feedback-id="${id}" data-feedback-rating="not_useful" title="没用">👎</button>
```

事件委托处理：
```javascript
document.getElementById('paper-container').addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-feedback-id]');
    if (!btn) return;
    const id = btn.dataset.feedbackId;
    const rating = btn.dataset.feedbackRating;
    try {
        await fetch('/api/feedback', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({paper_id: id, rating})
        });
        btn.classList.add('voted');
        showToast(rating === 'useful' ? '已标记为有用' : '已标记为没用');
    } catch {}
});
```

- [ ] **Step 5: 添加 feedback 按钮样式**

在 `css/styles.css` 中：
```css
.feedback-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 0.8rem;
    opacity: 0.5;
    padding: 2px 4px;
    transition: opacity 0.2s;
}
.feedback-btn:hover { opacity: 1; }
.feedback-btn.voted { opacity: 1; }
.feedback-btn.voted[data-feedback-rating="useful"] { color: #38a169; }
.feedback-btn.voted[data-feedback-rating="not_useful"] { color: #e53e3e; }
```

- [ ] **Step 6: 初始化 research_profile.json**

更新 research_profile.json 添加新字段：
```json
{
  "direction": "研究雷达和体征感知、博弈论以及多智能体",
  "keywords": [...],
  "quality_criteria": "...",
  "liked_topics": [],
  "disliked_topics": []
}
```

---

### Task 6: 提交 + HANDOFF 更新

- [ ] **Step 1: 更新 HANDOFF.md**

- [ ] **Step 2: Commit**

```bash
git add ai/system.txt ai/template.txt ai/structure.py ai/quick_filter.py daemon.py js/app.js css/styles.css research_profile.json
git commit -m "feat: AI 筛选精度+性能优化 — prompt重写+两步架构+增量缓存+反馈闭环"
```

---

## 预期效果

| 指标 | 当前 | 优化后目标 |
|:-----|:-----|:-----------|
| skip 率 | 71.9% | 30-40% |
| must-read 率 | 0% | 3-5% |
| worth-reading 率 | 7% | 15-25% |
| relevance 均分 | 1.5/10 | 4-5/10 |
| 增强速度 | 串行 1 worker | 3 workers + 增量跳过 |
| 新论文增强 | 全量深度分析 | 70% 快筛跳过，30% 深度分析 |
