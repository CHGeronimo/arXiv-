# Frontend UI Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the paper card visual hierarchy, add 4 switchable themes, and replace the top filter bar with a collapsible sidebar filter panel.

**Architecture:** Pure CSS variables for theming (no dependencies). Sidebar filter panel replaces the current top `filter-bar` with grouped collapsible sections. Card rendering moves AI detail fields (Motivation/Method/Result/Conclusion) into the detail modal, keeping only TLDR visible on cards. All changes are frontend-only — no backend modifications.

**Tech Stack:** Vanilla JS (ES modules), CSS custom properties, Flask serves static files.

---

## File Structure

| File | Action | Responsibility |
|:-----|:-------|:---------------|
| `css/styles.css` | Modify | Theme variables (4 themes), card styles, sidebar styles, layout |
| `css/sidebar.css` | Create | Sidebar filter panel styles (extracted from filter-bar) |
| `js/render.js` | Modify | Card template: 3-level hierarchy (title → TLDR → meta only) |
| `js/modal.js` | Modify | Detail modal: add Motivation/Method/Result/Conclusion sections |
| `js/filters.js` | Modify | Render filter groups into sidebar instead of dropdown panels |
| `js/app.js` | Modify | Theme switcher (4 themes), sidebar toggle, event binding |
| `js/state.js` | Modify | Add `currentTheme` state, `setSidebarOpen` mutator |
| `index.html` | Modify | Add sidebar container, theme picker, remove filter-bar, add sidebar.css link |

**Unchanged:** `js/api.js`, `js/subscriptions.js`, `js/ccf-data.js`, `js/crossref-search.js`, `css/subscriptions.css`, all backend Python files.

---

### Task 1: Theme System — 4 Themes via CSS Variables

**Files:**
- Modify: `css/styles.css:1-22` (replace existing `:root` and `:root[data-theme="light"]`)
- Modify: `js/state.js` (add `currentTheme` export)
- Modify: `js/app.js:14-26` (replace `_initTheme` and `toggleTheme`)

- [ ] **Step 1: Define 4 theme variable sets in `css/styles.css`**

Replace lines 1-22 of `css/styles.css` with:

```css
:root,
:root[data-theme="dark"] {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-card: #1c2333;
    --bg-card-hover: #222d3f;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --text-muted: #6e7681;
    --accent: #6e40c9;
    --accent-light: #a371f7;
    --accent-bg: rgba(110, 64, 201, 0.12);
    --border-color: #30363d;
    --border-hover: #484f58;
    --source-arxiv: #f97316;
    --source-crossref: #6e40c9;
    --sidebar-bg: #0d1117;
    --sidebar-border: #21262d;
    --badge-bg: rgba(110, 64, 201, 0.2);
}
:root[data-theme="light"] {
    --bg-primary: #ffffff;
    --bg-secondary: #f6f8fa;
    --bg-card: #ffffff;
    --bg-card-hover: #f3f4f6;
    --text-primary: #1f2937;
    --text-secondary: #6b7280;
    --text-muted: #9ca3af;
    --accent: #6e40c9;
    --accent-light: #8b5cf6;
    --accent-bg: rgba(110, 64, 201, 0.08);
    --border-color: #d1d5db;
    --border-hover: #9ca3af;
    --source-arxiv: #ea580c;
    --source-crossref: #7c3aed;
    --sidebar-bg: #f9fafb;
    --sidebar-border: #e5e7eb;
    --badge-bg: rgba(110, 64, 201, 0.1);
}
:root[data-theme="academic"] {
    --bg-primary: #ffffff;
    --bg-secondary: #fafafa;
    --bg-card: #ffffff;
    --bg-card-hover: #fefce8;
    --text-primary: #1a1a1a;
    --text-secondary: #555555;
    --text-muted: #888888;
    --accent: #1a5276;
    --accent-light: #2980b9;
    --accent-bg: rgba(26, 82, 118, 0.06);
    --border-color: #e0e0e0;
    --border-hover: #bdbdbd;
    --source-arxiv: #e67e22;
    --source-crossref: #1a5276;
    --sidebar-bg: #f5f5f5;
    --sidebar-border: #e0e0e0;
    --badge-bg: rgba(26, 82, 118, 0.08);
}
:root[data-theme="warm"] {
    --bg-primary: #1a1410;
    --bg-secondary: #231c15;
    --bg-card: #2a2118;
    --bg-card-hover: #352a1f;
    --text-primary: #f5e6d3;
    --text-secondary: #b8a08a;
    --text-muted: #7a6652;
    --accent: #d4915c;
    --accent-light: #e8a87c;
    --accent-bg: rgba(212, 145, 92, 0.12);
    --border-color: #3d3228;
    --border-hover: #5a4a3c;
    --source-arxiv: #e67e22;
    --source-crossref: #d4915c;
    --sidebar-bg: #1a1410;
    --sidebar-border: #2e2519;
    --badge-bg: rgba(212, 145, 92, 0.15);
}
```

- [ ] **Step 2: Update all hardcoded colors in `css/styles.css` to use variables**

In `css/styles.css`, search-and-replace these hardcoded values with CSS variable references:

| Old value | New value |
|:----------|:----------|
| `rgba(123, 47, 247, 0.2)` (paper-cat bg) | `var(--badge-bg)` |
| `rgba(123, 47, 247, 0.1)` (paper-tldr bg) | `var(--accent-bg)` |
| `3px solid var(--accent)` (paper-tldr border) | `3px solid var(--accent)` (already OK) |
| `rgba(123, 47, 247, 0.15)` (filter-dropdown-btn.has-active) | `var(--accent-bg)` |
| `rgba(123, 47, 247, 0.1)` (filter-option:hover) | `var(--accent-bg)` |
| `#a855f7` (ai-badge gradient) | `var(--accent-light)` |
| `#7b2ff7` (ai-badge gradient) | `var(--accent)` |

Specific edits:

```css
/* Line 143-145: .paper-cat */
.paper-cat {
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: 3px;
    background: var(--badge-bg);
    color: var(--accent-light);
}

/* Line 177-184: .paper-tldr → rename to .card-tldr (already exists at line 504, remove duplicate) */

/* Line 504-509: .card-tldr — update bg */
.card-tldr {
    margin-top: 4px;
    font-size: 0.78rem;
    color: var(--accent-light);
    font-style: italic;
}
```

Also update `.score-fill` hardcoded colors to use variables:
```css
.score-fill {
    /* Keep the width inline style from JS, but the base color is fine as-is for now */
}
```

- [ ] **Step 3: Add theme state to `js/state.js`**

Add after line 18 (`export const PAGE_SIZE = 40;`):

```js
export let currentTheme = localStorage.getItem('theme') || 'dark';

export function setCurrentTheme(t) {
    currentTheme = t;
    localStorage.setItem('theme', t);
    document.documentElement.setAttribute('data-theme', t);
}
```

- [ ] **Step 4: Replace theme logic in `js/app.js`**

Replace lines 14-26 of `js/app.js` with:

```js
import { setCurrentTheme, currentTheme } from './state.js';

const THEME_LABELS = { dark: '深色', light: '浅色', academic: '学术', warm: '暖色' };
const THEME_ICONS = { dark: '🌙', light: '☀️', academic: '📖', warm: '🔥' };

function _initTheme() {
    document.documentElement.setAttribute('data-theme', currentTheme);
    const btn = document.getElementById('btn-theme');
    if (btn) btn.textContent = THEME_ICONS[currentTheme] || '🌙';
}
function cycleTheme() {
    const themes = ['dark', 'light', 'academic', 'warm'];
    const idx = themes.indexOf(currentTheme);
    const next = themes[(idx + 1) % themes.length];
    setCurrentTheme(next);
    const btn = document.getElementById('btn-theme');
    if (btn) btn.textContent = THEME_ICONS[next] || '🌙';
    showToast(`主题：${THEME_LABELS[next]}`);
}
_initTheme();
```

In the DOMContentLoaded handler (line 80), change:
```js
// Old:
document.getElementById('btn-theme').addEventListener('click', toggleTheme);
// New:
document.getElementById('btn-theme').addEventListener('click', cycleTheme);
```

Also remove the old `toggleTheme` function (already replaced above).

- [ ] **Step 5: Update `index.html` theme button**

In `index.html` line 44, change the title attribute:
```html
<button id="btn-theme" class="gear-btn" title="切换主题（深色/浅色/学术/暖色）">🌙</button>
```

- [ ] **Step 6: Commit**

```bash
git add css/styles.css js/state.js js/app.js index.html
git commit -m "feat: 4套主题系统（深色/浅色/学术/暖色）纯CSS变量方案"
```

---

### Task 2: Sidebar Filter Panel — HTML Structure and CSS

**Files:**
- Create: `css/sidebar.css`
- Modify: `index.html` (remove filter-bar, add sidebar + sidebar.css link)

- [ ] **Step 1: Create `css/sidebar.css`**

```css
/* Sidebar filter panel */
.sidebar-toggle {
    position: fixed;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    z-index: 90;
    width: 28px;
    height: 48px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-left: none;
    border-radius: 0 6px 6px 0;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    font-size: 0.85rem;
    transition: background 0.2s, color 0.2s;
}
.sidebar-toggle:hover {
    background: var(--accent);
    color: #fff;
}
.sidebar-toggle.open {
    left: 280px;
}

.filter-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: 280px;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--sidebar-border);
    z-index: 85;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    overflow-y: auto;
    padding: 56px 0 16px;
}
.filter-sidebar.open {
    transform: translateX(0);
}
.filter-sidebar-header {
    padding: 8px 16px 4px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.filter-sidebar-header h3 {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--accent-light);
}
.filter-sidebar-header button {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 0.8rem;
}
.filter-sidebar-header button:hover {
    color: var(--accent);
}

/* Sidebar search */
.sidebar-search {
    padding: 4px 16px 8px;
}
.sidebar-search input {
    width: 100%;
    padding: 6px 10px;
    border-radius: 6px;
    border: 1px solid var(--border-color);
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 0.82rem;
    outline: none;
}
.sidebar-search input:focus {
    border-color: var(--accent);
}

/* Sidebar date filter */
.sidebar-date {
    padding: 4px 16px 8px;
}
.sidebar-date input {
    width: 100%;
    padding: 6px 10px;
    border-radius: 6px;
    border: 1px solid var(--border-color);
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 0.82rem;
    outline: none;
    cursor: pointer;
}
.sidebar-date input::-webkit-calendar-picker-indicator {
    filter: invert(0.7);
}

/* Filter group */
.filter-group {
    border-bottom: 1px solid var(--border-color);
}
.filter-group-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    cursor: pointer;
    color: var(--text-primary);
    font-size: 0.82rem;
    font-weight: 600;
    transition: color 0.15s;
}
.filter-group-header:hover {
    color: var(--accent-light);
}
.filter-group-header .group-count {
    font-size: 0.7rem;
    background: var(--accent);
    color: #fff;
    border-radius: 8px;
    padding: 1px 6px;
    min-width: 18px;
    text-align: center;
}
.filter-group-header .group-arrow {
    font-size: 0.6rem;
    color: var(--text-muted);
    transition: transform 0.15s;
}
.filter-group-header.expanded .group-arrow {
    transform: rotate(180deg);
}
.filter-group-body {
    display: none;
    padding: 4px 16px 10px;
}
.filter-group-body.expanded {
    display: block;
}
.filter-group-body label {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-size: 0.8rem;
    color: var(--text-primary);
    cursor: pointer;
}
.filter-group-body label:hover {
    color: var(--accent-light);
}
.filter-group-body input[type="checkbox"] {
    accent-color: var(--accent);
    width: 14px;
    height: 14px;
    cursor: pointer;
}
.filter-group-body .filter-count {
    margin-left: auto;
    font-size: 0.7rem;
    color: var(--text-muted);
}

/* Sort section in sidebar */
.sidebar-sort {
    padding: 4px 16px 10px;
    border-bottom: 1px solid var(--border-color);
}
.sidebar-sort label {
    display: block;
    padding: 4px 0;
    font-size: 0.8rem;
    color: var(--text-primary);
    cursor: pointer;
}
.sidebar-sort label:hover {
    color: var(--accent-light);
}
.sidebar-sort input[type="radio"] {
    accent-color: var(--accent);
    margin-right: 6px;
}
```

- [ ] **Step 2: Update `index.html` — remove filter-bar, add sidebar**

In `index.html`:

a) Add sidebar CSS link after line 8 (`<link rel="stylesheet" href="css/subscriptions.css">`):
```html
<link rel="stylesheet" href="css/sidebar.css">
```

b) Replace the entire `<div class="filter-bar">...</div>` (lines 49-87) with:
```html
<button id="sidebar-toggle" class="sidebar-toggle" title="筛选面板">☰</button>
<aside id="filter-sidebar" class="filter-sidebar">
    <div class="filter-sidebar-header">
        <h3>筛选</h3>
        <button id="sidebar-clear">清除全部</button>
    </div>
    <div class="sidebar-search">
        <input id="sidebar-search-input" type="text" placeholder="搜索... title: abstract: author:">
    </div>
    <div class="sidebar-date">
        <input id="sidebar-date-filter" type="date" title="按日期筛选">
    </div>
    <div class="sidebar-sort" id="sidebar-sort"></div>
    <div id="sidebar-filter-groups"></div>
</aside>
```

c) Remove the old `search-input` and `date-filter` from the header (lines 16-17):
```html
<!-- Remove these two lines from header-right: -->
<input id="search-input" type="text" placeholder="搜索... 支持 title: abstract: author:" class="search-bar">
<input id="date-filter" type="date" class="date-filter" title="按日期筛选">
```

d) Remove the sort dropdown from header (lines 18-29):
```html
<!-- Remove the entire dd-sort dropdown div -->
```

e) Update the `paper-count` span to remove its class (it stays in header):
```html
<span id="paper-count" class="paper-count"></span>
```

- [ ] **Step 3: Adjust `#paper-container` CSS for sidebar offset**

In `css/styles.css`, update the `#paper-container` rule to account for sidebar:

```css
#paper-container {
    margin: 0 auto;
    padding: 20px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 12px;
    transition: margin-left 0.25s ease;
}
#paper-container.sidebar-open {
    margin-left: 280px;
}
```

Also add a transition to `header`:
```css
header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border-color);
    background: var(--bg-secondary);
    position: sticky;
    top: 0;
    z-index: 100;
    transition: padding-left 0.25s ease;
}
header.sidebar-open {
    padding-left: 280px;
}
```

- [ ] **Step 4: Commit**

```bash
git add css/sidebar.css css/styles.css index.html
git commit -m "feat: 侧边栏筛选面板HTML结构和CSS"
```

---

### Task 3: Sidebar Filter Panel — JS Logic

**Files:**
- Modify: `js/filters.js` (render into sidebar groups instead of dropdowns)
- Modify: `js/app.js` (sidebar toggle, event binding, sort radio)
- Modify: `js/state.js` (add sidebarOpen state)

- [ ] **Step 1: Add sidebar state to `js/state.js`**

Add after the `currentTheme` exports:

```js
export let sidebarOpen = false;

export function setSidebarOpen(v) {
    sidebarOpen = v;
    const sidebar = document.getElementById('filter-sidebar');
    const toggle = document.getElementById('sidebar-toggle');
    const container = document.getElementById('paper-container');
    const header = document.querySelector('header');
    if (v) {
        sidebar?.classList.add('open');
        toggle?.classList.add('open');
        container?.classList.add('sidebar-open');
        header?.classList.add('sidebar-open');
    } else {
        sidebar?.classList.remove('open');
        toggle?.classList.remove('open');
        container?.classList.remove('sidebar-open');
        header?.classList.remove('sidebar-open');
    }
}
```

- [ ] **Step 2: Rewrite `buildFilterOptions()` in `js/filters.js`**

Replace the `buildFilterOptions()` function (lines 12-55) with sidebar group rendering:

```js
export function buildFilterOptions() {
    const journals = {};
    const categories = {};
    const venues = {};
    for (const p of allPapers) {
        if (p.source === 'crossref' && p.journal_title) {
            journals[p.journal_title] = (journals[p.journal_title] || 0) + 1;
        }
        for (const c of (p.categories || [])) {
            categories[c] = (categories[c] || 0) + 1;
        }
        if (p.venue) venues[p.venue] = (venues[p.venue] || 0) + 1;
    }
    _filterCounts = { journals, categories, venues };

    const groups = [
        { key: 'source', label: '来源', options: [
            { value: 'arxiv', label: 'arXiv' },
            { value: 'crossref', label: '期刊' },
            { value: 'dblp', label: 'DBLP 会议' },
            { value: 'semantic_scholar', label: 'S2 搜索' },
        ]},
        { key: 'venue', label: '会议', options:
            Object.entries(venues).sort((a, b) => b[1] - a[1]).map(([v, c]) => ({ value: v, label: v, count: c }))
        },
        { key: 'journal', label: '期刊', options:
            Object.entries(journals).sort((a, b) => b[1] - a[1]).map(([j, c]) => ({ value: j, label: j, count: c }))
        },
        { key: 'category', label: '领域', options:
            Object.entries(categories).sort((a, b) => b[1] - a[1]).map(([c, n]) => ({ value: c, label: c, count: n }))
        },
        { key: 'type', label: '推荐/类型', options: [
            { value: 'must-read', label: 'Must Read' },
            { value: 'worth-reading', label: 'Worth Reading' },
            { value: 'skim', label: 'Skim' },
            { value: 'unread', label: '未读' },
        ]},
        { key: 'bookmarked', label: '收藏', options: [
            { value: 'yes', label: '⭐ 已收藏' },
        ]},
    ];

    const container = document.getElementById('sidebar-filter-groups');
    if (!container) return;
    container.innerHTML = groups.map(g => {
        const activeCount = activeFilters[g.key]?.size || 0;
        return `
        <div class="filter-group" data-group="${g.key}">
            <div class="filter-group-header ${activeCount > 0 ? 'expanded' : ''}" data-group-toggle="${g.key}">
                <span>${g.label}${activeCount > 0 ? ` <span class="group-count">${activeCount}</span>` : ''}</span>
                <span class="group-arrow">▼</span>
            </div>
            <div class="filter-group-body ${activeCount > 0 ? 'expanded' : ''}" data-group-body="${g.key}">
                ${g.options.map(o => `
                    <label>
                        <input type="checkbox" ${activeFilters[g.key]?.has(o.value) ? 'checked' : ''}
                               data-filter-key="${escAttr(g.key)}" data-filter-value="${escAttr(o.value)}">
                        <span>${o.label}</span>
                        ${o.count != null ? `<span class="filter-count">${o.count}</span>` : ''}
                    </label>
                `).join('')}
            </div>
        </div>`;
    }).join('');

    renderSortOptions();
    updateFilterBadges();
}
```

Add `renderSortOptions` function:

```js
function renderSortOptions() {
    const container = document.getElementById('sidebar-sort');
    if (!container) return;
    const options = [
        { value: 'desc', label: '↓ 日期：新→旧' },
        { value: 'asc', label: '↑ 日期：旧→新' },
        { value: 'relevance', label: '★ 相关性' },
        { value: 'quality', label: '✦ AI 质量评分' },
        { value: 'citations', label: '✱ 引用数' },
        { value: 'rec', label: '✓ AI 推荐优先' },
        { value: 'source', label: '◉ 按来源分组' },
    ];
    container.innerHTML = '<div class="filter-group-header expanded" data-group-toggle="sort"><span>排序</span><span class="group-arrow">▼</span></div>' +
        '<div class="filter-group-body expanded" data-group-body="sort">' +
        options.map(o => `<label><input type="radio" name="sort" value="${o.value}" ${sortOrder === o.value ? 'checked' : ''}> ${o.label}</label>`).join('') +
        '</div>';
}
```

Remove the old `renderFilterDropdown()` function (lines 57-69) and the old `toggleDropdown()` function (lines 71-84). Keep `toggleFilter`, `updateFilterBadges`, `clearAllFilters`, `applyFiltersAndSort`, `closeAllDropdowns`.

Update `updateFilterBadges()` to work with sidebar:

```js
export function updateFilterBadges() {
    for (const name of Object.keys(activeFilters)) {
        const count = activeFilters[name].size;
        const header = document.querySelector(`[data-group-toggle="${name}"]`);
        if (!header) continue;
        let countEl = header.querySelector('.group-count');
        if (count > 0) {
            if (!countEl) {
                countEl = document.createElement('span');
                countEl.className = 'group-count';
                header.querySelector('span').appendChild(countEl);
            }
            countEl.textContent = count;
        } else if (countEl) {
            countEl.remove();
        }
    }
}
```

Update `clearAllFilters()` to also clear sidebar checkboxes:

```js
export function clearAllFilters() {
    for (const key of Object.keys(activeFilters)) activeFilters[key].clear();
    document.querySelectorAll('#sidebar-filter-groups input[type="checkbox"]').forEach(cb => cb.checked = false);
    const searchInput = document.getElementById('sidebar-search-input');
    const dateInput = document.getElementById('sidebar-date-filter');
    if (searchInput) searchInput.value = '';
    if (dateInput) dateInput.value = '';
    setCurrentPage(1);
}
```

Update `applyFiltersAndSort()` — the search query reads from `sidebar-search-input` instead of `search-input`, date from `sidebar-date-filter` instead of `date-filter`:

Replace lines 139-165 in the function:

```js
    const sq = document.getElementById('sidebar-search-input')?.value?.trim().toLowerCase() || '';
    if (sq) {
        const prefixFields = { 'title:': 'title', 'abstract:': 'summary', 'author:': 'authors' };
        const terms = sq.split(/\s+/);
        result = result.filter(p => {
            return terms.every(term => {
                for (const [prefix, field] of Object.entries(prefixFields)) {
                    if (term.startsWith(prefix)) {
                        const q = term.slice(prefix.length);
                        if (!q) return true;
                        if (field === 'authors') return (p.authors || []).some(a => a.toLowerCase().includes(q));
                        const val = ((p.AI || {})[field === 'summary' ? 'summary_zh' : 'title_zh'] || p[field] || '').toLowerCase();
                        return val.includes(q);
                    }
                }
                const allText = ((p.AI || {}).title_zh || p.title_zh || p.title || '') + ' ' +
                    ((p.AI || {}).summary_zh || p.summary_zh || p.summary || '') + ' ' +
                    (p.authors || []).join(' ');
                return allText.toLowerCase().includes(term);
            });
        });
    }

    const df = document.getElementById('sidebar-date-filter')?.value || '';
    if (df) {
        result = result.filter(p => (p.published_date || '').startsWith(df));
    }
```

Remove `closeAllDropdowns()` — no longer needed with sidebar (replace with no-op for compatibility):

```js
export function closeAllDropdowns() {
    // No-op: sidebar replaces dropdowns
}
```

- [ ] **Step 3: Update `js/app.js` event bindings**

In the `DOMContentLoaded` handler, replace the old filter-bar/dropdown/sort bindings with sidebar bindings.

Add these imports at the top of `app.js`:
```js
import { setSidebarOpen } from './state.js';
```

Replace the entire DOMContentLoaded callback contents (lines 61-176) with:

```js
document.addEventListener('DOMContentLoaded', () => {
    loadPapers();
    startAutoRefresh();
    window.addEventListener('beforeunload', () => { if (refreshTimer) clearInterval(refreshTimer); });

    // Sidebar toggle
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('filter-sidebar');
    sidebarToggle?.addEventListener('click', () => {
        const isOpen = sidebar.classList.contains('open');
        setSidebarOpen(!isOpen);
        sidebarToggle.textContent = isOpen ? '☰' : '✕';
    });

    // Sidebar filter group expand/collapse
    document.getElementById('sidebar-filter-groups')?.addEventListener('click', (e) => {
        const header = e.target.closest('[data-group-toggle]');
        if (!header) return;
        const key = header.dataset.groupToggle;
        if (key === 'sort') return; // sort handled separately
        const body = document.querySelector(`[data-group-body="${key}"]`);
        header.classList.toggle('expanded');
        body?.classList.toggle('expanded');
    });

    // Sidebar checkbox changes
    document.getElementById('sidebar-filter-groups')?.addEventListener('change', (e) => {
        const cb = e.target;
        if (cb.type === 'checkbox') {
            toggleFilter(cb.dataset.filterKey, cb.dataset.filterValue);
            renderPapers();
        }
    });

    // Sidebar sort
    document.getElementById('sidebar-sort')?.addEventListener('change', (e) => {
        if (e.target.type === 'radio' && e.target.name === 'sort') {
            setSortOrder(e.target.value);
            renderPapers();
        }
    });

    // Sidebar sort group toggle
    document.getElementById('sidebar-sort')?.addEventListener('click', (e) => {
        const header = e.target.closest('[data-group-toggle="sort"]');
        if (!header) return;
        const body = document.querySelector('[data-group-body="sort"]');
        header.classList.toggle('expanded');
        body?.classList.toggle('expanded');
    });

    // Sidebar search
    document.getElementById('sidebar-search-input')?.addEventListener('input', () => renderPapers());
    document.getElementById('sidebar-date-filter')?.addEventListener('change', () => renderPapers());

    // Sidebar clear
    document.getElementById('sidebar-clear')?.addEventListener('click', () => { clearAllFilters(); buildFilterOptions(); renderPapers(); });

    // Header buttons
    document.getElementById('btn-profile').addEventListener('click', openProfileModal);
    document.getElementById('btn-theme').addEventListener('click', cycleTheme);
    document.getElementById('btn-subs').addEventListener('click', () => window.openSubscriptionModal());

    // Crawl trigger
    document.getElementById('panel-crawl')?.addEventListener('click', (e) => {
        const item = e.target.closest('[data-crawl]');
        if (item) triggerCrawl(item.dataset.crawl, { loadPapers });
    });

    // Paper modal
    document.getElementById('close-paper-modal').addEventListener('click', closePaperModal);
    document.getElementById('paper-modal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) { closePaperModal(); return; }
        const bibtexBtn = e.target.closest('[data-export-bibtex]');
        if (bibtexBtn) {
            exportBibtex(bibtexBtn.dataset.exportBibtex)
                .then(text => navigator.clipboard.writeText(text).then(() => showToast('BibTeX 已复制到剪贴板')))
                .catch(() => showToast('导出失败'));
        }
    });

    // Profile modal
    document.getElementById('close-profile-modal').addEventListener('click', closeProfileModal);
    document.getElementById('profile-modal').addEventListener('click', (e) => { if (e.target === e.currentTarget) closeProfileModal(); });
    document.getElementById('btn-save-profile').addEventListener('click', saveProfile);

    // Subscription modal
    document.getElementById('close-subs-modal').addEventListener('click', () => window.closeSubscriptionModal());
    document.getElementById('subscription-modal').addEventListener('click', (e) => { if (e.target === e.currentTarget) window.closeSubscriptionModal(); });
    document.getElementById('btn-save-keywords')?.addEventListener('click', () => window.saveSearchKeywords?.());
    document.getElementById('sub-tabs-container')?.addEventListener('click', (e) => {
        const tab = e.target.closest('[data-tab]');
        if (tab) window.switchSubTab(tab.dataset.tab, tab);
    });
    document.getElementById('journal-search-input')?.addEventListener('input', () => window.handleJournalSearch?.());
    document.getElementById('use-profile-keywords')?.addEventListener('change', () => window.toggleCustomKeywords?.());

    // Paper container delegation
    document.getElementById('paper-container').addEventListener('click', async (e) => {
        const bmBtn = e.target.closest('.bookmark-btn');
        if (bmBtn) { e.stopPropagation(); toggleBookmark(bmBtn.dataset.bmId); renderPapers(); return; }
        const fbBtn = e.target.closest('[data-feedback-id]');
        if (fbBtn) {
            e.stopPropagation();
            try {
                await saveFeedback(fbBtn.dataset.feedbackId, fbBtn.dataset.feedbackRating);
                fbBtn.classList.add('voted');
                showToast(fbBtn.dataset.feedbackRating === 'useful' ? '已标记为有用' : '已标记为没用');
            } catch {}
            return;
        }
        const authorLink = e.target.closest('.author-link');
        if (authorLink) {
            e.stopPropagation();
            const name = authorLink.dataset.authorName;
            if (name && confirm(`关注作者 "${name}" 的最新论文？`)) quickFollowAuthor(name);
            return;
        }
        const card = e.target.closest('.paper-card[data-idx]');
        if (card) {
            const idx = parseInt(card.dataset.idx);
            const { filteredPapers: fp } = await import('./state.js');
            if (fp[idx]) openPaperDetail(fp[idx]);
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', async (e) => {
        const active = document.activeElement;
        const typing = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA');
        if (e.key === 'Escape') { closePaperModal(); window.closeSubscriptionModal?.(); closeProfileModal(); return; }
        if (typing) return;
        if (e.key === 'j') changePage(1);
        else if (e.key === 'k') changePage(-1);
        else if (e.key === 'f') {
            const { filteredPapers: fp, currentPage: cp, toggleBookmark: tb } = await import('./state.js');
            const first = fp[cp - 1];
            if (first) { tb(first.id); renderPapers(); }
        }
        else if (e.key === '/') { e.preventDefault(); document.getElementById('sidebar-search-input')?.focus(); }
        else if (e.key === '?') { showToast('j/k 翻页 | f 收藏首篇 | / 搜索 | Esc 关闭', 3000); }
    });
});
```

- [ ] **Step 4: Update `updatePaperCount()` in `js/render.js`**

In `render.js` line 109, change the search input ID:

```js
export function updatePaperCount() {
    const el = document.getElementById('paper-count');
    if (!el) return;
    const sq = document.getElementById('sidebar-search-input')?.value?.trim() || '';
    const df = document.getElementById('sidebar-date-filter')?.value || '';
    const total = allPapers.length;
    const shown = filteredPapers.length;
    const hasFilter = sq || df || Object.values(activeFilters).some(s => s.size > 0);
    el.textContent = hasFilter ? `${shown}/${total} 篇` : `${total} 篇`;
}
```

- [ ] **Step 5: Commit**

```bash
git add js/state.js js/filters.js js/app.js js/render.js
git commit -m "feat: 侧边栏筛选面板JS逻辑，替换顶部过滤器"
```

---

### Task 4: Card Visual Hierarchy — 3-Level Redesign

**Files:**
- Modify: `js/render.js` (card template: title → TLDR → meta only)
- Modify: `css/styles.css` (card styling refinements)
- Modify: `js/modal.js` (detail modal: add Motivation/Method/Result/Conclusion)

- [ ] **Step 1: Rewrite card template in `js/render.js`**

Replace the `renderPapers()` function's card template (lines 27-88). The new template uses 3-level hierarchy:

```js
    container.innerHTML = pagePapers.map((paper, i) => {
        const ai = paper.AI || {};
        const hasAi = !!(ai.tldr || paper.tldr);

        // Level 1: Badges row
        const sourceBadge = paper.source === 'crossref'
            ? `<span class="source-badge crossref">${paper.journal_title || 'Journal'}</span>`
            : paper.source === 'dblp'
            ? `<span class="source-badge dblp">DBLP</span>`
            : paper.source === 'semantic_scholar'
            ? `<span class="source-badge s2">S2</span>`
            : `<span class="source-badge arxiv">arXiv</span>`;
        const venueBadge = paper.venue ? `<span class="venue-badge">${paper.venue}</span>` : '';
        const accBadge = paper.acceptance ? `<span class="acc-badge ${paper.acceptance}">${paper.acceptance}</span>` : '';
        const citeBadge = paper.citation_count ? `<span class="cite-badge">&#9733; ${paper.citation_count}</span>` : '';
        const articleType = paper.article_type || inferType(paper);
        const typeTag = articleType === 'news' ? '<span class="paper-cat" style="background:rgba(249,115,22,0.2);color:#f97316">新闻</span>' : '';
        const aiBadge = hasAi ? '<span class="ai-badge">AI</span>' : '';
        const rec = ai.recommendation || '';
        const recBadge = rec ? `<span class="rec-badge ${rec}">${rec}</span>` : '';
        const codeBadge = paper.code_url ? '<span class="paper-cat code-badge">Code</span>' : '';

        // Level 1: Title
        const title = ai.title_zh || paper.title_zh || paper.title || '';

        // Level 2: TLDR only (not full AI解读)
        const tldr = ai.tldr || paper.tldr || '';
        const cardTldr = tldr ? `<div class="card-tldr">${tldr}</div>` : '';

        // Level 3: Meta
        const categories = (paper.categories || []).map(c => `<span class="paper-cat">${c}</span>`).join('');
        const authorList = (paper.authors || []).slice(0, 3).map(a =>
            `<span class="author-link" data-author-name="${escAttr(a)}">${a}</span>`
        ).join(', ');
        const authors = authorList + ((paper.authors || []).length > 3 ? ' et al.' : '');
        const idx = start + i;
        const isBookmarked = _bookmarks.has(paper.id);
        const isRead = _readPapers.has(paper.id);

        return `
            <div class="paper-card ${isRead ? 'is-read' : ''}" data-idx="${idx}" data-rec="${rec}">
                <div class="paper-header">
                    ${sourceBadge}${venueBadge}${accBadge}${aiBadge}${recBadge}${typeTag}
                    <div class="paper-categories">${categories}${codeBadge}</div>
                    <button class="bookmark-btn ${isBookmarked ? 'active' : ''}" data-bm-id="${escAttr(paper.id)}" title="${isBookmarked ? '取消收藏' : '收藏'}">${isBookmarked ? '★' : '☆'}</button>
                </div>
                <div class="paper-title">${title}</div>
                ${cardTldr}
                <div class="paper-footer">
                    <span class="paper-authors">${authors}</span>
                    <span class="paper-meta-date">${paper.published_date || ''} ${citeBadge}</span>
                </div>
            </div>`;
    }).join('');
```

- [ ] **Step 2: Update card CSS for 3-level hierarchy**

In `css/styles.css`, update/add these rules:

```css
.paper-title {
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 4px;
    line-height: 1.4;
}

.card-tldr {
    margin: 4px 0;
    padding: 6px 8px;
    background: var(--accent-bg);
    border-radius: 4px;
    font-size: 0.78rem;
    color: var(--text-secondary);
    line-height: 1.5;
}

.paper-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 6px;
    gap: 8px;
}

.paper-authors {
    font-size: 0.78rem;
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
}

.paper-meta-date {
    font-size: 0.72rem;
    color: var(--text-muted);
    white-space: nowrap;
    flex-shrink: 0;
}

/* Code badge */
.paper-cat.code-badge {
    background: rgba(34,197,94,0.15);
    color: #22c55e;
}
```

Remove the old `.paper-summary`, `.paper-meta`, `.paper-authors` rules that conflict (keep only the ones above). Remove the old `.card-tldr` rule at line 504-509 (replaced by the new one). Remove the `.score-bar` and related score display CSS (scores move to detail modal only).

- [ ] **Step 3: Update detail modal in `js/modal.js`**

The detail modal already shows all AI fields (lines 28-45). No changes needed — it already displays TLDR, Motivation, Method, Result, Conclusion.

- [ ] **Step 4: Commit**

```bash
git add js/render.js js/modal.js css/styles.css
git commit -m "feat: 卡片三级层次（标题→TLDR→元信息），AI详情移至模态框"
```

---

### Task 5: Header Cleanup and Responsive Adjustments

**Files:**
- Modify: `css/styles.css` (responsive media queries, header cleanup)
- Modify: `index.html` (remove redundant header elements already moved to sidebar)

- [ ] **Step 1: Clean up header in `index.html`**

After Task 2 and 3, the header should only contain:
- Logo/title
- Paper count
- Crawl trigger dropdown
- Profile button
- Theme button
- Subscription button

Verify the `header-right` div only has:
```html
<div class="header-right">
    <span id="paper-count" class="paper-count"></span>
    <div class="filter-dropdown" id="dd-crawl">
        <button class="gear-btn" data-dropdown="crawl" title="手动爬取">🔄</button>
        <div class="filter-dropdown-panel" id="panel-crawl" style="min-width:160px;right:0;left:auto">
            <div class="filter-option" data-crawl="arxiv"><span>arXiv</span><span class="count" id="crawl-arxiv">—</span></div>
            <div class="filter-option" data-crawl="crossref"><span>期刊</span><span class="count" id="crawl-crossref">—</span></div>
            <div class="filter-option" data-crawl="dblp"><span>DBLP</span><span class="count" id="crawl-dblp">—</span></div>
            <div class="filter-option" data-crawl="s2"><span>S2 搜索</span><span class="count" id="crawl-s2">—</span></div>
            <hr style="border-color:var(--border-color);margin:4px 0">
            <div class="filter-option" data-crawl="all"><span>全部爬取</span></div>
            <div class="filter-option" data-crawl="enhance"><span>补 AI 增强</span></div>
        </div>
    </div>
    <button id="btn-profile" class="gear-btn" title="研究方向">🎯</button>
    <button id="btn-theme" class="gear-btn" title="切换主题（深色/浅色/学术/暖色）">🌙</button>
    <button id="btn-subs" class="gear-btn" title="订阅管理">⚙️</button>
</div>
```

- [ ] **Step 2: Update responsive media queries in `css/styles.css`**

Replace the existing media queries (lines 559-601) with:

```css
@media (max-width: 1024px) {
    #paper-container {
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    }
    #paper-container.sidebar-open {
        margin-left: 0;
    }
    header.sidebar-open {
        padding-left: 24px;
    }
    .filter-sidebar {
        width: 260px;
    }
    .sidebar-toggle.open {
        left: 260px;
    }
}

@media (max-width: 768px) {
    header {
        flex-wrap: wrap;
        gap: 8px;
        padding: 12px 16px;
    }
    .header-right {
        width: 100%;
        justify-content: flex-end;
    }
    .filter-sidebar {
        width: 100%;
    }
    .sidebar-toggle.open {
        left: 0;
        top: auto;
        bottom: 16px;
        right: 16px;
        border-radius: 50%;
        width: 44px;
        height: 44px;
    }
    #paper-container {
        grid-template-columns: 1fr;
        padding: 12px;
    }
    #paper-container.sidebar-open {
        margin-left: 0;
    }
}

@media (max-width: 480px) {
    header h1 { font-size: 1.1rem; }
    .paper-title { font-size: 0.9rem; }
}
```

- [ ] **Step 3: Commit**

```bash
git add css/styles.css index.html
git commit -m "refactor: header精简+响应式适配侧边栏"
```

---

### Task 6: Integration Verification

**Files:**
- All modified files

- [ ] **Step 1: Start the daemon and verify in browser**

```bash
cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily
python daemon.py --port 5000
```

Open `http://localhost:5000` in browser. Check:

1. Default theme renders correctly (dark)
2. Click theme button → cycles through dark → light → academic → warm → dark
3. Sidebar toggle (☰) opens/closes sidebar
4. Filter groups expand/collapse correctly
5. Checkbox filtering works
6. Sort radio buttons work
7. Search and date filter work from sidebar
8. Cards show 3-level hierarchy: title → TLDR → meta
9. Click card → detail modal shows full AI解读
10. `/` focuses sidebar search
11. Mobile responsive: sidebar full-width on narrow screens

- [ ] **Step 2: Fix any issues found during verification**

Address each issue individually, then re-verify.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "fix: 前端UI重构集成验证修复"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- ✅ Card 3-level hierarchy: title → TLDR → meta (Task 4)
- ✅ AI detail moved to modal (Task 4 — modal already has it)
- ✅ 4 themes: dark/light/academic/warm (Task 1)
- ✅ Pure CSS variables (Task 1)
- ✅ Collapsible sidebar filter panel (Task 2, 3)
- ✅ Grouped collapsible sections (Task 3)
- ✅ Grid equal-height cards (Task 4 — unchanged)
- ✅ System font stack (no changes needed)

**2. Placeholder scan:** No TBD/TODO/placeholder patterns found.

**3. Type consistency:**
- `activeFilters` uses `Set` objects with `has/add/delete` — consistent across all tasks
- `sortOrder` is a string — consistent
- `sidebarOpen` is boolean — consistent
- Element IDs: `sidebar-search-input`, `sidebar-date-filter`, `sidebar-filter-groups`, `sidebar-sort` — defined in Task 2 HTML, referenced in Task 3 JS
- `escAttr()` used consistently for data attributes
- `setSidebarOpen()` manages CSS classes on sidebar, toggle, container, header — all defined
