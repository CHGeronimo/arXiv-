# 前端设计系统重建

> **目标**：重建 CSS 设计系统，统一 4 主题 token、组件视觉规范、交互状态和响应式布局
> **技术栈**：纯 HTML + CSS（无框架），CSS 变量 + @layer
> **范围**：4 个 CSS 文件新建 + 3 个旧文件合并删除 + index.html link 更新

---

## 1. 文件结构与 Token 体系

### 1.1 文件重组

```
css/
├── tokens.css          ← 新建：主题变量、间距、圆角、阴影
├── base.css            ← 新建：reset、typography、通用元素
├── components.css      ← 新建：卡片、badge、按钮、modal、sidebar、表单
├── utilities.css       ← 新建：辅助类（间距、flex、文本截断）
├── subscriptions.css   ← 保留：订阅面板专用（清理后 ~80 行）
├── sidebar.css         ← 删除（合并进 components.css）
├── styles.css          ← 删除（拆分到以上文件）
```

index.html 中 link 顺序：

```html
<link rel="stylesheet" href="css/tokens.css">
<link rel="stylesheet" href="css/base.css">
<link rel="stylesheet" href="css/components.css">
<link rel="stylesheet" href="css/utilities.css">
<link rel="stylesheet" href="css/subscriptions.css">
```

### 1.2 Token 体系（tokens.css）

跨主题共享 token：

```css
:root {
  /* 间距 scale（4px 基准） */
  --sp-1: 4px;  --sp-2: 8px;  --sp-3: 12px;
  --sp-4: 16px; --sp-5: 24px; --sp-6: 32px; --sp-8: 48px;

  /* 圆角 */
  --radius-sm: 4px; --radius-md: 8px;
  --radius-lg: 12px; --radius-full: 9999px;

  /* 阴影 */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.12);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.16);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.22);

  /* 过渡时长 */
  --transition-fast: 0.15s ease;
  --transition-base: 0.25s ease;
  --transition-slow: 0.4s ease;

  /* 字体 */
  --font-display: 'Space Grotesk', sans-serif;
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* 字号 */
  --text-xs: 0.7rem;   --text-sm: 0.8rem;   --text-base: 0.9rem;
  --text-md: 1rem;     --text-lg: 1.15rem;   --text-xl: 1.35rem;
  --text-2xl: 1.6rem;
}
```

### 1.3 主题 Token

#### Dark（默认）

```css
:root[data-theme="dark"] {
  --surface-0: #0f1419;  --surface-1: #161b22;
  --surface-2: #1c2333;  --surface-3: #222d3f;
  --text-0: #ecf0f6;     --text-1: #c9d1d9;
  --text-2: #8b949e;     --text-3: #6e7681;
  --accent-primary: #818cf8; --accent-muted: rgba(129,140,248,0.12);
  --accent-hover: #6366f1;
  --success: #34d399; --warning: #fbbf24; --danger: #f87171; --info: #60a5fa;
  --rec-must: #34d399; --rec-recommend: #60a5fa;
  --rec-reference: #a78bfa; --rec-ignore: #6b7280;
  --border: rgba(255,255,255,0.08); --border-hover: rgba(255,255,255,0.15);
  --source-arxiv: #b5393e; --source-crossref: #2e8b57;
  --source-dblp: #e8a317; --source-s2: #6b8dd6;
}
```

#### Light

```css
:root[data-theme="light"] {
  --surface-0: #f6f8fa;  --surface-1: #ffffff;
  --surface-2: #f0f2f5;  --surface-3: #e8ecf0;
  --text-0: #1f2937;     --text-1: #374151;
  --text-2: #6b7280;     --text-3: #9ca3af;
  --accent-primary: #4f46e5; --accent-muted: rgba(79,70,229,0.08);
  --accent-hover: #4338ca;
  --success: #059669; --warning: #d97706; --danger: #dc2626; --info: #2563eb;
  --rec-must: #059669; --rec-recommend: #2563eb;
  --rec-reference: #7c3aed; --rec-ignore: #9ca3af;
  --border: rgba(0,0,0,0.08); --border-hover: rgba(0,0,0,0.15);
  --source-arxiv: #b5393e; --source-crossref: #2e8b57;
  --source-dblp: #e8a317; --source-s2: #6b8dd6;
}
```

#### Academic

```css
:root[data-theme="academic"] {
  --surface-0: #faf8f5;  --surface-1: #ffffff;
  --surface-2: #f5f0eb;  --surface-3: #ece5dd;
  --text-0: #2c2416;     --text-1: #4a3f2f;
  --text-2: #7a6e5d;     --text-3: #a0947f;
  --accent-primary: #8b5e3c; --accent-muted: rgba(139,94,60,0.1);
  --accent-hover: #6d4a30;
  --success: #2e7d32; --warning: #e65100; --danger: #c62828; --info: #1565c0;
  --rec-must: #2e7d32; --rec-recommend: #1565c0;
  --rec-reference: #6a1b9a; --rec-ignore: #9e9e9e;
  --border: rgba(0,0,0,0.1); --border-hover: rgba(0,0,0,0.18);
  --source-arxiv: #b5393e; --source-crossref: #2e8b57;
  --source-dblp: #e8a317; --source-s2: #6b8dd6;
}
```

#### Warm

```css
:root[data-theme="warm"] {
  --surface-0: #1a1510;  --surface-1: #231e17;
  --surface-2: #2d2620;  --surface-3: #3a322a;
  --text-0: #f5e6d3;     --text-1: #d4c4a8;
  --text-2: #a89880;     --text-3: #7a6e5d;
  --accent-primary: #e8a849; --accent-muted: rgba(232,168,73,0.12);
  --accent-hover: #d4952e;
  --success: #81c784; --warning: #ffb74d; --danger: #e57373; --info: #64b5f6;
  --rec-must: #81c784; --rec-recommend: #64b5f6;
  --rec-reference: #ce93d8; --rec-ignore: #8d6e63;
  --border: rgba(255,255,255,0.06); --border-hover: rgba(255,255,255,0.12);
  --source-arxiv: #ef5350; --source-crossref: #66bb6a;
  --source-dblp: #ffa726; --source-s2: #42a5f5;
}
```

---

## 2. 组件视觉规范

### 2.1 Paper Card

**布局结构**（从上到下）：

```
┌─ 左侧色带 (3px) ─────────────────────────────┐
│  [header] source-badge · ccf-badge · rec-badge │
│  [title]  论文标题 (var(--text-lg))            │
│  [tldr]   一句话总结 (var(--text-sm), --text-2)│
│  [footer] 作者 · 日期    [actions: ☆ 👍 👎]    │
└────────────────────────────────────────────────┘
```

| 属性 | 值 |
|------|-----|
| 背景 | var(--surface-1) |
| 边框 | 1px solid var(--border) |
| 圆角 | var(--radius-lg) |
| 内间距 | var(--sp-4) |
| 左侧色带 | must-read: var(--rec-must); recommended: var(--rec-recommend); reference: var(--rec-reference); ref-low: var(--rec-ignore); ignore: transparent |
| 色带宽度 | 3px，border-left |
| 行间距 | header→title: var(--sp-2); title→tldr: var(--sp-1); tldr→footer: var(--sp-3) |
| hover | box-shadow: var(--shadow-md); 左侧色带亮度 +20%; border-color: var(--border-hover) |
| is-read | opacity: 0.6; hover 时恢复 1.0 |
| transition | var(--transition-fast) |

### 2.2 Badge 系统

**基类** `.badge`：

| 属性 | 值 |
|------|-----|
| padding | 2px var(--sp-2) |
| font-size | var(--text-xs) |
| font-weight | 600 |
| border-radius | var(--radius-full) |
| line-height | 1.4 |
| letter-spacing | 0.02em |
| white-space | nowrap |

**变体**（通过背景色 + 文字色区分）：

| 变体 | 背景 | 文字 |
|------|------|------|
| .badge--must | var(--rec-must) + opacity 0.15 | var(--rec-must) |
| .badge--recommend | var(--rec-recommend) + opacity 0.15 | var(--rec-recommend) |
| .badge--reference | var(--rec-reference) + opacity 0.15 | var(--rec-reference) |
| .badge--ref-low | var(--rec-ignore) + opacity 0.1 | var(--text-3) |
| .badge--source | 各 source 色同上 | 各 source 色同上 |
| .badge--ccf | var(--accent-muted) | var(--accent-primary) |

**Badge 行布局**：`.card-badges { display: flex; gap: var(--sp-1); flex-wrap: wrap; align-items: center; }`

### 2.3 按钮系统

**层级**：

| 层级 | 背景 | 边框 | 文字 | 圆角 |
|------|------|------|------|------|
| .btn--primary | var(--accent-primary) | none | #fff | var(--radius-md) |
| .btn--secondary | transparent | 1px solid var(--border-hover) | var(--text-1) | var(--radius-md) |
| .btn--ghost | transparent | none | var(--text-2) | var(--radius-md) |
| .btn--icon | transparent | none | var(--text-2) | var(--radius-full) |

**通用**：padding: var(--sp-1) var(--sp-3); font-size: var(--text-sm); font-weight: 500; transition: var(--transition-fast); cursor: pointer;

**状态**：
- hover: primary→accent-hover; secondary→border-hover; ghost→text-1; icon→bg var(--surface-2)
- active: transform: scale(0.97)
- focus: outline: 2px solid var(--accent-primary); outline-offset: 2px
- disabled: opacity: 0.4; pointer-events: none

### 2.4 Modal

| 属性 | 值 |
|------|-----|
| backdrop | rgba(0,0,0,0.6) + backdrop-filter: blur(4px) |
| 背景 | var(--surface-3) |
| 圆角 | var(--radius-lg) |
| 最大宽度 | 720px (paper) / 560px (subscription) |
| 最大高度 | 85vh |
| 内间距 | var(--sp-5) |
| 关闭按钮 | 右上角 32px × 32px, .btn--icon |
| 滚动区 | overflow-y: auto; padding-right: var(--sp-2) |
| 入场动画 | opacity 0→1 + translateY(8px→0), var(--transition-base) |

### 2.5 Sidebar

| 属性 | 值 |
|------|-----|
| 触发方式 | 点击按钮开关（保留 hover zone 触发区 width:48px 作为辅助） |
| 宽度 | 320px |
| 背景 | var(--surface-2) |
| 边框 | border-right: 1px solid var(--border) |
| filter-group 展开 | max-height: 0 → auto, transition: var(--transition-base) |
| 遮罩 | 无遮罩，sidebar 覆盖在卡片上方 |

### 2.6 表单元素

| 元素 | 背景 | 边框 | 圆角 | 内间距 |
|------|------|------|------|--------|
| input/textarea | var(--surface-0) | 1px solid var(--border) | var(--radius-md) | var(--sp-2) var(--sp-3) |
| select | var(--surface-0) | 1px solid var(--border) | var(--radius-md) | var(--sp-2) var(--sp-3) |
| checkbox | var(--surface-0) | 1px solid var(--border-hover) | var(--radius-sm) | - |
| focus 态 | - | 2px solid var(--accent-primary) | - | - |

---

## 3. 交互与微交互

### 3.1 状态补全

所有可交互元素必须有完整的 default / hover / active / focus-visible / disabled 五态。

### 3.2 过渡规则

| 场景 | 时长 | 曲线 |
|------|------|------|
| 颜色/背景/边框变化 | 0.15s | ease |
| 位移/缩放 | 0.25s | ease |
| Modal/sidebar 入场 | 0.25s | cubic-bezier(0.16, 1, 0.3, 1) |
| 大面积展开/收起 | 0.4s | ease |

### 3.3 骨架屏

卡片加载时显示骨架屏替代"加载中"文字：

```css
.skeleton {
  background: linear-gradient(90deg, var(--surface-2) 25%, var(--surface-3) 50%, var(--surface-2) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-md);
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

### 3.4 Toast 通知

从右上角弹出，3 秒自动消失：

```css
.toast {
  position: fixed; top: var(--sp-5); right: var(--sp-5);
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  box-shadow: var(--shadow-lg);
  animation: slideIn var(--transition-base);
}
.toast--success { border-left: 3px solid var(--success); background: var(--surface-3); }
.toast--error   { border-left: 3px solid var(--danger);  background: var(--surface-3); }
.toast--info    { border-left: 3px solid var(--info);    background: var(--surface-3); }
```

### 3.5 键盘导航

- 所有按钮/链接有 focus-visible 环：`outline: 2px solid var(--accent-primary); outline-offset: 2px`
- Tab 顺序：header 工具栏 → 卡片列表 → sidebar
- Escape 关闭 modal/sidebar

### 3.6 响应式断点

| 断点 | 布局变化 |
|------|----------|
| ≥1024px | 3 列卡片网格 + sidebar 覆盖 |
| 768-1023px | 2 列卡片网格 + sidebar 全屏覆盖 |
| <768px | 单列卡片 + sidebar 全屏覆盖 + 隐藏次要 badge |

---

## 4. 实施顺序与风险

### 4.1 实施顺序

1. **tokens.css** — 新建，4 主题完整 token 定义
2. **base.css** — 新建，从 styles.css 提取 reset + typography + 通用元素，改用 token 变量
3. **components.css** — 新建，从 styles.css + sidebar.css 提取所有组件样式，重写为 token 化
4. **utilities.css** — 新建，辅助类
5. **subscriptions.css** — 清理，改用 token 变量
6. **index.html** — 更新 link 标签，引入 Google Fonts（Space Grotesk + Inter）
7. **JS 文件** — 检查并同步修改依赖 CSS class 的代码（render.js 中的 badge class、modal.js 中的样式 class）
8. **删除** — sidebar.css、styles.css

### 4.2 JS 需同步修改的 class 映射

| 旧 class | 新 class | 文件 |
|----------|----------|------|
| .rec-badge.must-read | .badge.badge--must | render.js |
| .rec-badge.recommended | .badge.badge--recommend | render.js |
| .rec-badge.reference | .badge.badge--reference | render.js |
| .rec-badge.ref-low | .badge.badge--ref-low | render.js |
| .source-badge | .badge.badge--source | render.js |
| .ccf-badge | .badge.badge--ccf | render.js |
| .follow-btn | .btn--icon | modal.js, render.js |
| .card-vote-btn | .btn--icon | render.js |
| .sort-btn | .btn--secondary | filters.js |
| .sub-chip | .badge.badge--secondary | subscriptions.js |
| .gear-btn | .btn--icon | header 区域 |

### 4.3 回归测试要点

1. 4 个主题切换正常，无颜色错误
2. 卡片网格在不同断点下布局正确
3. 所有按钮/交互元素 hover/active/focus 状态正常
4. Modal 打开/关闭正常，内容显示完整
5. Sidebar 展开/收起正常
6. 订阅面板（CCF 期刊、快捷订阅、arXiv 分类）功能正常
7. 投票按钮、收藏按钮功能正常
8. 骨架屏在加载时显示
9. Toast 通知在右上角弹出
10. 键盘 Tab 导航流畅
