# Frontend Design System Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the entire CSS architecture from a single monolithic styles.css + sidebar.css into a token-driven design system with 4 new CSS files, synchronized JS class names, and deleted legacy files.

**Architecture:** Create `tokens.css` (design variables for 4 themes) → `base.css` (reset + typography) → `components.css` (all UI components using tokens) → `utilities.css` (helper classes). Then clean subscriptions.css, update index.html links + Google Fonts, synchronize JS class references, and delete legacy files.

**Tech Stack:** Pure HTML + CSS (no framework), CSS custom properties, Google Fonts (Space Grotesk + Inter + JetBrains Mono)

**Design Spec:** `docs/superpowers/specs/2026-06-03-frontend-design-system-rebuild.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `css/tokens.css` | Create | All CSS custom properties: theme colors, spacing, radius, shadows, transitions, fonts |
| `css/base.css` | Create | CSS reset, typography, body/layout, scrollbar, generic elements |
| `css/components.css` | Create | Cards, badges, buttons, modal, sidebar, forms, toast, skeleton, header |
| `css/utilities.css` | Create | Spacing, flex, text-truncation, visibility helpers |
| `css/subscriptions.css` | Modify | Replace hardcoded colors with token vars, trim unused rules |
| `css/sidebar.css` | Delete | Merged into components.css |
| `css/styles.css` | Delete | Split into tokens.css + base.css + components.css + utilities.css |
| `index.html` | Modify | Update `<link>` tags, add Google Fonts `<link>` |
| `js/render.js` | Modify | Update badge/button class names to new design system |
| `js/modal.js` | Modify | Update button class names |
| `js/filters.js` | Modify | Update sort button class names |
| `js/subscriptions.js` | Modify | Update chip/badge class names |

---

### Task 1: Create tokens.css

**Files:**
- Create: `css/tokens.css`

- [ ] **Step 1: Create tokens.css with shared tokens**

```css
/* ============================================
   tokens.css — Design System Variables
   All theme-independent tokens + theme overrides
   ============================================ */

/* --- Shared tokens (all themes) --- */
:root {
  /* Spacing scale (4px base) */
  --sp-1: 4px;  --sp-2: 8px;  --sp-3: 12px;
  --sp-4: 16px; --sp-5: 24px; --sp-6: 32px; --sp-8: 48px;

  /* Border radius */
  --radius-sm: 4px;  --radius-md: 8px;
  --radius-lg: 12px; --radius-full: 9999px;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.12);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.16);
  --shadow-lg: 0 8px 24px rgba(0,0,0,0.22);

  /* Transitions */
  --transition-fast: 0.15s ease;
  --transition-base: 0.25s ease;
  --transition-slow: 0.4s ease;
  --transition-spring: 0.25s cubic-bezier(0.16, 1, 0.3, 1);

  /* Fonts */
  --font-display: 'Space Grotesk', sans-serif;
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;

  /* Font sizes */
  --text-xs: 0.7rem;   --text-sm: 0.8rem;   --text-base: 0.9rem;
  --text-md: 1rem;     --text-lg: 1.15rem;   --text-xl: 1.35rem;
  --text-2xl: 1.6rem;
}

/* --- Dark theme (default) --- */
:root[data-theme="dark"],
:root {
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

/* --- Light theme --- */
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

/* --- Academic theme --- */
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

/* --- Warm theme --- */
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

- [ ] **Step 2: Verify tokens.css loads without errors**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python3 -c "
import re
with open('css/tokens.css') as f: css = f.read()
themes = re.findall(r'data-theme=\"(\w+)\"', css)
print(f'Themes found: {themes}')
vars_dark = set(re.findall(r'--[\w-]+', css.split('data-theme=\"light\"')[0]))
print(f'Dark theme vars: {len(vars_dark)}')
assert len(themes) == 4, 'Expected 4 themes'
assert len(vars_dark) >= 25, 'Expected >=25 dark vars'
print('PASS')
"`
Expected: Themes found: ['dark', 'light', 'academic', 'warm'] / PASS

- [ ] **Step 3: Commit**

```bash
git add css/tokens.css
git commit -m "feat: add design system tokens (4 themes, spacing, radius, shadows)"
```

---

### Task 2: Create base.css

**Files:**
- Create: `css/base.css`

- [ ] **Step 1: Create base.css with reset, typography, and layout**

```css
/* ============================================
   base.css — Reset, Typography, Layout
   ============================================ */

/* --- Reset --- */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  scroll-behavior: smooth;
}

body {
  font-family: var(--font-body);
  font-size: var(--text-base);
  color: var(--text-1);
  background: var(--surface-0);
  line-height: 1.6;
  min-height: 100vh;
  transition: background var(--transition-base), color var(--transition-base);
}

a { color: var(--accent-primary); text-decoration: none; }
a:hover { text-decoration: underline; }

img { max-width: 100%; display: block; }

button {
  font-family: inherit;
  font-size: inherit;
  cursor: pointer;
  border: none;
  background: none;
  color: inherit;
}

input, textarea, select {
  font-family: inherit;
  font-size: inherit;
  color: inherit;
}

/* --- Typography --- */
h1, h2, h3, h4 {
  font-family: var(--font-display);
  color: var(--text-0);
  line-height: 1.3;
}
h1 { font-size: var(--text-2xl); }
h2 { font-size: var(--text-xl); }
h3 { font-size: var(--text-lg); }
h4 { font-size: var(--text-md); }

code, pre {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  background: var(--surface-2);
  border-radius: var(--radius-sm);
  padding: var(--sp-1) var(--sp-2);
}

/* --- Layout --- */
#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.main-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--surface-1);
  border-bottom: 1px solid var(--border);
  padding: var(--sp-3) var(--sp-5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-4);
}

.main-content {
  flex: 1;
  padding: var(--sp-5);
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

/* --- Scrollbar --- */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--border-hover);
  border-radius: var(--radius-full);
}
::-webkit-scrollbar-thumb:hover { background: var(--text-3); }

/* --- Selection --- */
::selection {
  background: var(--accent-muted);
  color: var(--text-0);
}

/* --- Focus visible --- */
:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}

/* --- Utility: screen reader only --- */
.sr-only {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  border: 0;
}
```

- [ ] **Step 2: Verify base.css parses correctly**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python3 -c "
with open('css/base.css') as f: css = f.read()
# Check no hardcoded colors remain
import re
hex_colors = re.findall(r'#[0-9a-fA-F]{3,8}(?!;)', css)
rgb_colors = re.findall(r'rgb[a]?\([^)]+\)', css)
issues = []
for c in hex_colors:
    if c not in ['#fff']: issues.append(f'hex: {c}')
print(f'Hardcoded hex colors (excl #fff): {issues}')
print(f'RGB/RGBA instances: {len(rgb_colors)} (0 is expected)')
assert len(issues) == 0, f'Found hardcoded colors: {issues}'
print('PASS')
"`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add css/base.css
git commit -m "feat: add base stylesheet (reset, typography, layout, scrollbar)"
```

---

### Task 3: Create components.css

**Files:**
- Create: `css/components.css`

This is the largest file. It replaces styles.css + sidebar.css with token-driven component styles.

- [ ] **Step 1: Create components.css — Header section**

```css
/* ============================================
   components.css — All UI Components
   Uses tokens from tokens.css exclusively
   ============================================ */

/* ===================== HEADER ===================== */
.header-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--text-0);
  white-space: nowrap;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: wrap;
}

.header-search {
  background: var(--surface-0);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--sp-2) var(--sp-3);
  color: var(--text-1);
  font-size: var(--text-sm);
  width: 220px;
  transition: border-color var(--transition-fast);
}
.header-search:focus {
  border-color: var(--accent-primary);
  outline: none;
}
.header-search::placeholder { color: var(--text-3); }

.theme-select {
  background: var(--surface-0);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--sp-2) var(--sp-3);
  color: var(--text-1);
  font-size: var(--text-sm);
  cursor: pointer;
}

/* ===================== CARDS GRID ===================== */
#papers-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--sp-4);
}

/* ===================== PAPER CARD ===================== */
.paper-card {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--sp-4);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  cursor: pointer;
  transition: box-shadow var(--transition-fast), border-color var(--transition-fast);
  position: relative;
}

/* Left accent stripe */
.paper-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  transition: background var(--transition-fast);
}

.paper-card[data-rec="must-read"]::before   { background: var(--rec-must); }
.paper-card[data-rec="recommended"]::before  { background: var(--rec-recommend); }
.paper-card[data-rec="reference"]::before    { background: var(--rec-reference); }
.paper-card[data-rec="ref-low"]::before      { background: var(--rec-ignore); }

.paper-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--border-hover);
}
.paper-card:hover::before { filter: brightness(1.2); }

.paper-card.is-read { opacity: 0.6; }
.paper-card.is-read:hover { opacity: 1; }

/* Card inner sections */
.card-badges {
  display: flex;
  gap: var(--sp-1);
  flex-wrap: wrap;
  align-items: center;
}

.card-title {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--text-0);
  line-height: 1.4;
}

.card-tldr {
  font-size: var(--text-sm);
  color: var(--text-2);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: var(--sp-2);
  border-top: 1px solid var(--border);
  font-size: var(--text-xs);
  color: var(--text-3);
}

.card-authors {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 70%;
}

.card-actions {
  display: flex;
  gap: var(--sp-1);
  align-items: center;
}

/* ===================== BADGES ===================== */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--sp-2);
  font-size: var(--text-xs);
  font-weight: 600;
  border-radius: var(--radius-full);
  line-height: 1.4;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.badge--must       { background: rgba(52,211,153,0.15); color: var(--rec-must); }
.badge--recommend  { background: rgba(96,165,250,0.15); color: var(--rec-recommend); }
.badge--reference  { background: rgba(167,139,250,0.15); color: var(--rec-reference); }
.badge--ref-low    { background: rgba(107,114,128,0.1);  color: var(--text-3); }
.badge--ignore     { background: transparent; color: var(--text-3); }
.badge--secondary  { background: var(--surface-2); border: 1px solid var(--border); color: var(--text-1); }

.badge--source-arxiv     { background: rgba(181,57,62,0.12); color: var(--source-arxiv); }
.badge--source-crossref  { background: rgba(46,139,87,0.12); color: var(--source-crossref); }
.badge--source-dblp      { background: rgba(232,163,23,0.12); color: var(--source-dblp); }
.badge--source-s2        { background: rgba(107,141,214,0.12); color: var(--source-s2); }
.badge--source-openalex  { background: rgba(156,39,176,0.12); color: #9c27b0; }

.badge--ccf { background: var(--accent-muted); color: var(--accent-primary); }

.badge--venue {
  background: var(--surface-2);
  color: var(--text-2);
  font-weight: 400;
}

.badge--acc {
  background: rgba(251,191,36,0.12);
  color: var(--warning);
}

/* ===================== BUTTONS ===================== */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-1);
  padding: var(--sp-1) var(--sp-3);
  font-size: var(--text-sm);
  font-weight: 500;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  cursor: pointer;
  border: none;
  background: none;
  color: inherit;
  line-height: 1;
}

.btn--primary {
  background: var(--accent-primary);
  color: #fff;
}
.btn--primary:hover { background: var(--accent-hover); }

.btn--secondary {
  background: transparent;
  border: 1px solid var(--border-hover);
  color: var(--text-1);
}
.btn--secondary:hover {
  background: var(--surface-2);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.btn--ghost {
  background: transparent;
  color: var(--text-2);
}
.btn--ghost:hover {
  color: var(--text-1);
  background: var(--surface-2);
}

.btn--icon {
  background: transparent;
  color: var(--text-2);
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: var(--radius-full);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-base);
  transition: all var(--transition-fast);
}
.btn--icon:hover {
  background: var(--surface-2);
  color: var(--text-0);
}
.btn--icon.active {
  color: var(--accent-primary);
}

.btn:active { transform: scale(0.97); }
.btn:disabled { opacity: 0.4; pointer-events: none; }

/* Vote buttons (card-level) */
.card-vote-btn {
  font-size: 1.15rem;
  padding: var(--sp-1) var(--sp-2);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  cursor: pointer;
  background: none;
  border: none;
  line-height: 1;
}
.card-vote-btn:hover { transform: scale(1.3); }
.card-vote-btn.voted { font-weight: 600; transform: scale(1.05); }

.card-vote-btn.up   { color: var(--success); }
.card-vote-btn.down { color: var(--danger); }

/* ===================== MODAL ===================== */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(4px);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn var(--transition-fast);
}

.modal {
  background: var(--surface-3);
  border-radius: var(--radius-lg);
  max-width: 720px;
  width: 90vw;
  max-height: 85vh;
  overflow-y: auto;
  padding: var(--sp-5);
  box-shadow: var(--shadow-lg);
  animation: slideUp var(--transition-spring);
  position: relative;
}

.modal.modal--sm { max-width: 560px; }

.modal-close {
  position: absolute;
  top: var(--sp-3);
  right: var(--sp-3);
}

.modal-header {
  padding-bottom: var(--sp-3);
  border-bottom: 1px solid var(--border);
  margin-bottom: var(--sp-4);
}

.modal-title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--text-0);
  padding-right: var(--sp-8);
}

.modal-section {
  margin-bottom: var(--sp-4);
}

.modal-section-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--sp-2);
}

.modal-actions {
  display: flex;
  gap: var(--sp-2);
  justify-content: flex-end;
  padding-top: var(--sp-4);
  border-top: 1px solid var(--border);
}

/* Vote buttons in modal */
.modal-vote-btn {
  padding: var(--sp-2) var(--sp-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  border: 1px solid;
  transition: all var(--transition-fast);
  cursor: pointer;
  background: none;
}
.modal-vote-btn.up {
  border-color: var(--success);
  color: var(--success);
}
.modal-vote-btn.up:hover {
  background: rgba(52,211,153,0.1);
}
.modal-vote-btn.up.voted {
  background: rgba(52,211,153,0.15);
  font-weight: 600;
}
.modal-vote-btn.down {
  border-color: var(--danger);
  color: var(--danger);
}
.modal-vote-btn.down:hover {
  background: rgba(248,113,113,0.1);
}
.modal-vote-btn.down.voted {
  background: rgba(248,113,113,0.15);
  font-weight: 600;
}

/* ===================== SIDEBAR ===================== */
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: 320px;
  height: 100vh;
  background: var(--surface-2);
  border-right: 1px solid var(--border);
  z-index: 150;
  overflow-y: auto;
  padding: var(--sp-5);
  transform: translateX(-100%);
  transition: transform var(--transition-spring);
}

.sidebar.open { transform: translateX(0); }

.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.3);
  z-index: 149;
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--transition-base);
}
.sidebar-overlay.visible {
  opacity: 1;
  pointer-events: auto;
}

.sidebar-section { margin-bottom: var(--sp-5); }

.sidebar-title {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--text-0);
  margin-bottom: var(--sp-3);
}

.filter-group { margin-bottom: var(--sp-3); }

.filter-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  padding: var(--sp-2) 0;
  color: var(--text-1);
  font-weight: 500;
  font-size: var(--text-sm);
  user-select: none;
}

.filter-group-header:hover { color: var(--accent-primary); }

.filter-group-body {
  max-height: 0;
  overflow: hidden;
  transition: max-height var(--transition-base);
}
.filter-group-body.expanded { max-height: 800px; }

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  padding: var(--sp-1) var(--sp-2);
  margin: var(--sp-1);
  background: var(--surface-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  color: var(--text-2);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.filter-chip:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}
.filter-chip.active {
  background: var(--accent-muted);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

/* ===================== FORMS ===================== */
.form-input,
.form-textarea,
.form-select {
  width: 100%;
  background: var(--surface-0);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--sp-2) var(--sp-3);
  color: var(--text-1);
  font-size: var(--text-sm);
  transition: border-color var(--transition-fast);
}
.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  border-color: var(--accent-primary);
  outline: none;
  box-shadow: 0 0 0 3px var(--accent-muted);
}
.form-input::placeholder,
.form-textarea::placeholder { color: var(--text-3); }

.form-checkbox {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-primary);
  cursor: pointer;
}

.form-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-2);
  margin-bottom: var(--sp-1);
}

/* ===================== TOAST ===================== */
.toast {
  position: fixed;
  top: var(--sp-5);
  right: var(--sp-5);
  padding: var(--sp-3) var(--sp-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  box-shadow: var(--shadow-lg);
  z-index: 300;
  animation: slideInRight var(--transition-spring);
  max-width: 360px;
}
.toast--success { border-left: 3px solid var(--success); background: var(--surface-3); }
.toast--error   { border-left: 3px solid var(--danger);  background: var(--surface-3); }
.toast--info    { border-left: 3px solid var(--info);    background: var(--surface-3); }

/* ===================== SKELETON ===================== */
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

/* ===================== ANIMATIONS ===================== */
@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(20px); }
  to   { opacity: 1; transform: translateX(0); }
}

/* ===================== RESPONSIVE ===================== */
@media (max-width: 1023px) {
  #papers-container {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

@media (max-width: 767px) {
  .main-header {
    flex-wrap: wrap;
    padding: var(--sp-3);
  }
  .header-search { width: 100%; order: 10; }
  #papers-container {
    grid-template-columns: 1fr;
  }
  .sidebar { width: 100%; }
  .badge--venue,
  .badge--acc { display: none; }
}
```

- [ ] **Step 2: Verify no hardcoded colors in components.css**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python3 -c "
import re
with open('css/components.css') as f: css = f.read()
# Allow only #fff in btn--primary and rgba in badge backgrounds
hex_colors = re.findall(r'#[0-9a-fA-F]{3,8}', css)
allowed = {'#fff'}
bad = [c for c in hex_colors if c not in allowed]
print(f'Hardcoded hex (excl #fff): {bad}')
assert len(bad) == 0, f'Found hardcoded colors: {bad}'
print('PASS')
"`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add css/components.css
git commit -m "feat: add component stylesheet (cards, badges, buttons, modal, sidebar, forms)"
```

---

### Task 4: Create utilities.css

**Files:**
- Create: `css/utilities.css`

- [ ] **Step 1: Create utilities.css**

```css
/* ============================================
   utilities.css — Helper Classes
   ============================================ */

/* --- Spacing --- */
.mt-1 { margin-top: var(--sp-1); }  .mt-2 { margin-top: var(--sp-2); }
.mt-3 { margin-top: var(--sp-3); }  .mt-4 { margin-top: var(--sp-4); }
.mt-5 { margin-top: var(--sp-5); }
.mb-1 { margin-bottom: var(--sp-1); } .mb-2 { margin-bottom: var(--sp-2); }
.mb-3 { margin-bottom: var(--sp-3); } .mb-4 { margin-bottom: var(--sp-4); }
.p-2  { padding: var(--sp-2); }  .p-3 { padding: var(--sp-3); }
.p-4  { padding: var(--sp-4); }  .p-5 { padding: var(--sp-5); }

/* --- Flex --- */
.flex      { display: flex; }
.flex-col  { flex-direction: column; }
.flex-wrap { flex-wrap: wrap; }
.items-center   { align-items: center; }
.justify-between { justify-content: space-between; }
.gap-1 { gap: var(--sp-1); } .gap-2 { gap: var(--sp-2); }
.gap-3 { gap: var(--sp-3); } .gap-4 { gap: var(--sp-4); }

/* --- Text --- */
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.text-center { text-align: center; }
.text-sm     { font-size: var(--text-sm); }
.text-xs     { font-size: var(--text-xs); }
.text-muted  { color: var(--text-2); }

/* --- Visibility --- */
.hidden { display: none; }
.visible { visibility: visible; }
.invisible { visibility: hidden; }

/* --- Width --- */
.w-full { width: 100%; }
.max-w-prose { max-width: 65ch; }
```

- [ ] **Step 2: Commit**

```bash
git add css/utilities.css
git commit -m "feat: add utility classes (spacing, flex, text, visibility)"
```

---

### Task 5: Clean subscriptions.css

**Files:**
- Modify: `css/subscriptions.css`

- [ ] **Step 1: Replace hardcoded colors with token variables in subscriptions.css**

Read the current `css/subscriptions.css`. Replace all hardcoded color values with the corresponding CSS custom properties from tokens.css. Specifically:

- Replace `background: #...` on `.subs-panel`, `.subs-section`, `.sub-chip` etc. with `background: var(--surface-N)` (pick the right level)
- Replace `color: #...` text colors with `color: var(--text-N)`
- Replace `border-color: #...` with `border-color: var(--border)` or `var(--border-hover)`
- Replace any theme-specific selectors (like `[data-theme="dark"]` blocks inside subscriptions.css) — these should now be unnecessary since tokens.css handles theme switching
- Keep the structural CSS (display, padding, margin, position, etc.) unchanged
- Remove any duplicate rules that are now covered by components.css (.badge, .btn--icon, etc.)

The cleaned file should be approximately 60-80 lines.

- [ ] **Step 2: Verify subscriptions.css uses only tokens**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python3 -c "
import re
with open('css/subscriptions.css') as f: css = f.read()
hex = re.findall(r'#[0-9a-fA-F]{3,8}', css)
rgb = [r for r in re.findall(r'rgb[a]?\([^)]+\)', css) if 'rgba(0,0,0' not in r and 'rgba(255,255,255' not in r]
issues = hex + rgb
print(f'Hardcoded colors remaining: {issues}')
assert len(issues) == 0, f'Found hardcoded colors: {issues}'
print('PASS')
"`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add css/subscriptions.css
git commit -m "refactor: clean subscriptions.css to use design tokens"
```

---

### Task 6: Update index.html

**Files:**
- Modify: `index.html`

- [ ] **Step 1: Add Google Fonts links and update CSS imports**

In `index.html`, find the existing `<link rel="stylesheet" href="css/styles.css">` and `<link rel="stylesheet" href="css/sidebar.css">` lines. Replace them with:

```html
<!-- Google Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<!-- Design System CSS -->
<link rel="stylesheet" href="css/tokens.css">
<link rel="stylesheet" href="css/base.css">
<link rel="stylesheet" href="css/components.css">
<link rel="stylesheet" href="css/utilities.css">
<link rel="stylesheet" href="css/subscriptions.css">
```

Also add `data-rec` attribute support to paper cards — find where paper cards are rendered and ensure each card container has `data-rec="..."` attribute matching its recommendation level. This is already done in render.js but verify the attribute is set on the outer `.paper-card` element.

- [ ] **Step 2: Verify index.html has all new links and no old links**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python3 -c "
with open('index.html') as f: html = f.read()
assert 'css/tokens.css' in html, 'Missing tokens.css'
assert 'css/base.css' in html, 'Missing base.css'
assert 'css/components.css' in html, 'Missing components.css'
assert 'css/utilities.css' in html, 'Missing utilities.css'
assert 'css/styles.css' not in html, 'Old styles.css still referenced'
assert 'css/sidebar.css' not in html, 'Old sidebar.css still referenced'
assert 'Space+Grotesk' in html, 'Missing Space Grotesk font'
assert 'Inter:wght' in html, 'Missing Inter font'
assert 'JetBrains+Mono' in html, 'Missing JetBrains Mono font'
print('PASS')
"`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: update index.html with design system CSS links and Google Fonts"
```

---

### Task 7: Synchronize JS class names

**Files:**
- Modify: `js/render.js`
- Modify: `js/modal.js`
- Modify: `js/filters.js`
- Modify: `js/subscriptions.js`

This is the most critical task — JS generates HTML with class names that must match the new design system. Do each file carefully.

- [ ] **Step 1: Update render.js badge and button classes**

In `js/render.js`, find and replace these class patterns. The file generates paper card HTML strings.

**Badge classes:**
- `rec-badge must-read` → `badge badge--must`
- `rec-badge recommended` → `badge badge--recommend`
- `rec-badge reference` → `badge badge--reference`
- `rec-badge ref-low` → `badge badge--ref-low`
- `rec-badge ignore` → `badge badge--ignore`
- `source-badge` with source-specific styling → `badge badge--source-${sourceName}` where sourceName is one of: arxiv, crossref, dblp, s2, openalex
- `ccf-badge` → `badge badge--ccf`
- `venue-badge` → `badge badge--venue`
- `acc-badge` → `badge badge--acc`

**Card structure:**
- Ensure the card's outer element has `data-rec="${recommendation}"` attribute for the left stripe to work. If recommendation is "reference" but relevance < 7, use `data-rec="ref-low"`.
- `.card-badges` wrapper should wrap all badges
- `.card-title`, `.card-tldr`, `.card-footer` classes stay the same
- `.follow-btn` (bookmark/star button) → `btn--icon` with additional class for the specific icon
- `.card-vote-btn` stays as-is (already styled in components.css)

- [ ] **Step 2: Update modal.js button classes**

In `js/modal.js`:
- Vote buttons: change inline styles to use `modal-vote-btn up` / `modal-vote-btn down` classes. Remove inline `style=` attributes for border-color and color since components.css handles this.
- Keep the emoji content (☝ and ☟) in the button text.
- Close button: use `btn--icon` class
- Any `.gear-btn` → `btn--icon`

- [ ] **Step 3: Update filters.js sort button classes**

In `js/filters.js`:
- `.sort-btn` → `btn btn--secondary` (or `btn btn--ghost` for less prominent ones)
- Any chip-style filter elements → `filter-chip` class from components.css

- [ ] **Step 4: Update subscriptions.js chip/badge classes**

In `js/subscriptions.js`:
- `.sub-chip` → `badge badge--secondary` (or `badge badge--source-${source}` / `badge badge--ccf` depending on context)
  If the chip represents a source (e.g., "arXiv cs.AI"), use `badge badge--source-arxiv`.
  If it represents a CCF category, use `badge badge--ccf`.
  Otherwise use `badge badge--secondary`.
- Any `.gear-btn` → `btn--icon`
- Checkbox label styling should use `.form-checkbox` and `.form-label` from components.css

- [ ] **Step 5: Verify all JS files compile without syntax errors**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && node -e "
const fs = require('fs');
for (const f of ['js/render.js','js/modal.js','js/filters.js','js/subscriptions.js']) {
  try { new Function(fs.readFileSync(f,'utf8')); console.log(f + ': OK'); }
  catch(e) { console.error(f + ': SYNTAX ERROR - ' + e.message); process.exit(1); }
}
"`
Expected: All 4 files print OK

- [ ] **Step 6: Verify no old class names remain**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python3 -c "
import re
old_classes = ['rec-badge must-read', 'rec-badge recommended', 'rec-badge reference',
               'rec-badge ref-low', 'source-badge', 'ccf-badge', 'venue-badge',
               'acc-badge', 'gear-btn']
for f in ['js/render.js','js/modal.js','js/filters.js','js/subscriptions.js']:
    with open(f) as fh: content = fh.read()
    for oc in old_classes:
        if oc in content:
            print(f'WARNING: {f} still contains \"{oc}\"')
print('Scan complete (warnings above if any)')
"`
Expected: Scan complete with no warnings

- [ ] **Step 7: Commit**

```bash
git add js/render.js js/modal.js js/filters.js js/subscriptions.js
git commit -m "refactor: sync JS class names to new design system"
```

---

### Task 8: Delete legacy CSS and regression test

**Files:**
- Delete: `css/styles.css`
- Delete: `css/sidebar.css`

- [ ] **Step 1: Delete legacy CSS files**

```bash
cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily
rm css/styles.css css/sidebar.css
```

- [ ] **Step 2: Verify no references to deleted files remain**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && python3 -c "
import os
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ['.git','node_modules','__pycache__']]
    for f in files:
        if f.endswith(('.html','.js','.py','.json')):
            path = os.path.join(root, f)
            with open(path) as fh:
                content = fh.read()
            if 'styles.css' in content or 'sidebar.css' in content:
                print(f'WARNING: {path} references deleted CSS file')
print('Scan complete')
"`
Expected: Scan complete with no warnings

- [ ] **Step 3: Verify Python server starts without errors**

Run: `cd /home/ch/paper/latex/summary/code/arxiv/arxivSCI-daily && timeout 5 python3 app.py 2>&1 || true`
Expected: Server starts (may timeout and exit, that's fine — we're checking for import/syntax errors only)

- [ ] **Step 4: Full visual regression checklist**

Open the app in a browser and verify ALL of the following:

1. [ ] Dark theme renders correctly (slate-indigo palette)
2. [ ] Light theme renders correctly
3. [ ] Academic theme renders correctly
4. [ ] Warm theme renders correctly
5. [ ] Paper cards show left accent stripe (green for must-read, blue for recommended, purple for reference, gray for ref-low)
6. [ ] Card badges use new .badge styles (rounded-full, consistent sizing)
7. [ ] Card hover shows shadow + stripe brightness
8. [ ] Read cards are dimmed, brighten on hover
9. [ ] Vote buttons (card-level) render at 1.15rem with scale on hover
10. [ ] Modal opens/closes, has backdrop blur, correct padding
11. [ ] Modal vote buttons have colored borders (green/red)
12. [ ] Sidebar opens/closes with slide animation
13. [ ] Filter groups expand/collapse
14. [ ] Subscription panel (CCF journals, quick subscribe, arXiv categories) works
15. [ ] Toast notifications appear in top-right corner
16. [ ] Typography uses Space Grotesk for headings, Inter for body
17. [ ] Responsive: 2-column at 768-1023px, 1-column below 768px
18. [ ] Keyboard Tab navigation works with focus-visible rings
19. [ ] No console errors in browser DevTools

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: delete legacy CSS files (styles.css, sidebar.css)"
```
