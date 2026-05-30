// js/app.js
let allPapers = [];
let filteredPapers = [];
let activeFilters = {
    source: new Set(),    // 'arxiv', 'crossref', 'dblp', 'semantic_scholar'
    journal: new Set(),   // journal names
    category: new Set(),  // arXiv categories
    venue: new Set(),     // conference venues
    type: new Set(),      // 'research', 'news'
    bookmarked: new Set(), // 'yes' — filter bookmarked
};
let searchQuery = '';
let dateFilter = '';
let sortOrder = 'desc';
let refreshTimer = null;
let currentPage = 1;
const PAGE_SIZE = 30;

const _bookmarks = new Set(JSON.parse(localStorage.getItem('bookmarks') || '[]'));
function _saveBookmarks() { localStorage.setItem('bookmarks', JSON.stringify([..._bookmarks])); }
function toggleBookmark(id) { _bookmarks.has(id) ? _bookmarks.delete(id) : _bookmarks.add(id); _saveBookmarks(); }

const _readPapers = new Set(JSON.parse(localStorage.getItem('readPapers') || '[]'));
function _markRead(id) { if (!_readPapers.has(id)) { _readPapers.add(id); localStorage.setItem('readPapers', JSON.stringify([..._readPapers])); } }

function showToast(msg, duration = 2000) {
    let el = document.getElementById('toast');
    if (!el) { el = document.createElement('div'); el.id = 'toast'; document.body.appendChild(el); }
    el.textContent = msg;
    el.className = 'toast show';
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.className = 'toast'; }, duration);
}

function _initTheme() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    return theme;
}
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    document.getElementById('btn-theme').textContent = next === 'dark' ? '🌙' : '☀️';
}
_initTheme();

document.addEventListener('DOMContentLoaded', () => {
    loadPapers();
    startAutoRefresh();
    window.addEventListener('beforeunload', () => { if (refreshTimer) clearInterval(refreshTimer); });

    document.getElementById('search-input').addEventListener('input', handleSearch);
    document.getElementById('date-filter').addEventListener('change', handleDateFilter);
    document.getElementById('panel-sort')?.addEventListener('click', (e) => {
        const opt = e.target.closest('[data-sort]');
        if (!opt) return;
        sortOrder = opt.dataset.sort;
        // Update button label
        const btn = document.querySelector('#dd-sort .sort-btn');
        btn.innerHTML = opt.textContent.trim() + ' <span class="arrow">▼</span>';
        // Highlight active
        document.querySelectorAll('#panel-sort .filter-option').forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        closeAllDropdowns();
        renderPapers();
    });
    document.getElementById('btn-profile').addEventListener('click', openProfileModal);
    document.getElementById('btn-theme').addEventListener('click', toggleTheme);
    document.getElementById('btn-subs').addEventListener('click', openSubscriptionModal);
    document.getElementById('btn-clear-filters').addEventListener('click', clearAllFilters);

    // Dropdown toggle delegation
    document.querySelectorAll('[data-dropdown]').forEach(btn => {
        btn.addEventListener('click', () => toggleDropdown(btn.dataset.dropdown));
    });

    // Crawl trigger delegation
    document.getElementById('panel-crawl').addEventListener('click', (e) => {
        const item = e.target.closest('[data-crawl]');
        if (item) triggerCrawl(item.dataset.crawl);
    });

    // Modal close buttons
    document.getElementById('close-paper-modal').addEventListener('click', closePaperModal);
    document.getElementById('paper-modal').addEventListener('click', (e) => {
        if (e.target === e.currentTarget) { closePaperModal(); return; }
        const bibtexBtn = e.target.closest('[data-export-bibtex]');
        if (bibtexBtn) {
            const pid = bibtexBtn.dataset.exportBibtex;
            fetch('/api/export/bibtex', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ids: [pid]}) })
                .then(r => r.ok ? r.text() : Promise.reject('failed'))
                .then(text => { navigator.clipboard.writeText(text).then(() => showToast('BibTeX 已复制到剪贴板')); })
                .catch(() => showToast('导出失败'));
        }
    });
    document.getElementById('close-profile-modal').addEventListener('click', closeProfileModal);
    document.getElementById('profile-modal').addEventListener('click', (e) => { if (e.target === e.currentTarget) closeProfileModal(); });
    document.getElementById('btn-save-profile').addEventListener('click', saveProfile);

    // Subscription modal
    document.getElementById('close-subs-modal').addEventListener('click', closeSubscriptionModal);
    document.getElementById('subscription-modal').addEventListener('click', (e) => { if (e.target === e.currentTarget) closeSubscriptionModal(); });
    document.getElementById('btn-save-keywords').addEventListener('click', () => saveSearchKeywords());

    // Sub tabs delegation
    document.getElementById('sub-tabs-container').addEventListener('click', (e) => {
        const tab = e.target.closest('[data-tab]');
        if (tab) switchSubTab(tab.dataset.tab, tab);
    });

    // Journal search
    document.getElementById('journal-search-input').addEventListener('input', handleJournalSearch);
    document.getElementById('use-profile-keywords').addEventListener('change', toggleCustomKeywords);

    document.getElementById('paper-container').addEventListener('click', async (e) => {
        const bmBtn = e.target.closest('.bookmark-btn');
        if (bmBtn) {
            e.stopPropagation();
            toggleBookmark(bmBtn.dataset.bmId);
            renderPapers();
            return;
        }
        const fbBtn = e.target.closest('[data-feedback-id]');
        if (fbBtn) {
            e.stopPropagation();
            const id = fbBtn.dataset.feedbackId;
            const rating = fbBtn.dataset.feedbackRating;
            try {
                await fetch('/api/feedback', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({paper_id: id, rating})
                });
                fbBtn.classList.add('voted');
                showToast(rating === 'useful' ? '已标记为有用' : '已标记为没用');
            } catch {}
            return;
        }
        const card = e.target.closest('.paper-card[data-idx]');
        if (card) {
            const idx = parseInt(card.dataset.idx);
            if (filteredPapers[idx]) openPaperDetail(filteredPapers[idx]);
        }
    });

    document.addEventListener('keydown', (e) => {
        const active = document.activeElement;
        const typing = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA');
        if (e.key === 'Escape') {
            closePaperModal();
            closeSubscriptionModal();
            closeProfileModal();
            closeAllDropdowns();
            return;
        }
        if (typing) return;
        if (e.key === 'j') { changePage(1); }
        else if (e.key === 'k') { changePage(-1); }
        else if (e.key === 'f') {
            const first = filteredPapers[currentPage - 1];
            if (first) { toggleBookmark(first.id); renderPapers(); }
        }
        else if (e.key === '/') { e.preventDefault(); document.getElementById('search-input').focus(); }
        else if (e.key === '?') { showToast('j/k 翻页 | f 收藏首篇 | / 搜索 | ? 帮助', 3000); }
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.filter-dropdown')) {
            document.querySelectorAll('.filter-dropdown-panel').forEach(p => p.classList.remove('show'));
            document.querySelectorAll('.filter-dropdown-btn').forEach(b => b.classList.remove('open'));
        }
    });
});

async function loadPapers() {
    try {
        const resp = await fetch('/api/papers?per_page=1000');
        if (resp.ok) {
            const data = await resp.json();
            allPapers = data.papers || [];
        }
    } catch (e) {
        console.error('Failed to load papers:', e);
    }
    buildFilterOptions();
    renderPapers();
}

function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(async () => {
        try {
            const resp = await fetch('/api/papers?per_page=1000');
            if (resp.ok) {
                const data = await resp.json();
                const newPapers = data.papers || [];
                if (data.total !== allPapers.length || newPapers.length !== allPapers.length) {
                    allPapers = newPapers;
                    buildFilterOptions();
                    renderPapers();
                }
            }
        } catch {}
    }, 15000);
}

// ── Filter Bar ──────────────────────────────────────────────────

let _filterCounts = {};
let _openDropdown = null;

function buildFilterOptions() {
    const journals = {};
    const categories = {};
    for (const p of allPapers) {
        if (p.source === 'crossref' && p.journal_title) {
            journals[p.journal_title] = (journals[p.journal_title] || 0) + 1;
        }
        for (const c of (p.categories || [])) {
            categories[c] = (categories[c] || 0) + 1;
        }
    }
    _filterCounts = { journals, categories };

    renderFilterDropdown('source', [
        { value: 'arxiv', label: 'arXiv' },
        { value: 'crossref', label: '期刊' },
        { value: 'dblp', label: 'DBLP 会议' },
        { value: 'semantic_scholar', label: 'S2 搜索' },
    ]);
    renderFilterDropdown('journal',
        Object.entries(journals).sort((a,b) => b[1]-a[1]).map(([j, c]) => ({ value: j, label: j, count: c }))
    );
    const venues = {};
    for (const p of allPapers) {
        if (p.venue) venues[p.venue] = (venues[p.venue] || 0) + 1;
    }
    _filterCounts.venues = venues;
    renderFilterDropdown('venue',
        Object.entries(venues).sort((a,b) => b[1]-a[1]).map(([v, c]) => ({ value: v, label: v, count: c }))
    );
    renderFilterDropdown('category',
        Object.entries(categories).sort((a,b) => b[1]-a[1]).map(([c, n]) => ({ value: c, label: c, count: n }))
    );
    renderFilterDropdown('type', [
        { value: 'must-read', label: 'Must Read' },
        { value: 'worth-reading', label: 'Worth Reading' },
        { value: 'skim', label: 'Skim' },
        { value: 'unread', label: '未读' },
    ]);
    renderFilterDropdown('bookmarked', [
        { value: 'yes', label: '⭐ 已收藏' },
    ]);
    updateFilterBadges();
}

function _escAttr(s) { return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;'); }

function renderFilterDropdown(name, options) {
    const panel = document.getElementById(`panel-${name}`);
    if (!panel) return;
    const active = activeFilters[name];
    panel.innerHTML = options.map(o => `
        <label class="filter-option">
            <input type="checkbox" ${active.has(o.value) ? 'checked' : ''}
                   onchange="toggleFilter('${_escAttr(name)}', '${_escAttr(o.value)}')">
            <span>${o.label}</span>
            ${o.count != null ? `<span class="count">${o.count}</span>` : ''}
        </label>
    `).join('');
}

function toggleDropdown(name) {
    const panel = document.getElementById(`panel-${name}`);
    const btn = panel.previousElementSibling;
    const isOpen = panel.classList.contains('show');

    // Close all
    document.querySelectorAll('.filter-dropdown-panel').forEach(p => p.classList.remove('show'));
    document.querySelectorAll('.filter-dropdown-btn').forEach(b => b.classList.remove('open'));

    if (!isOpen) {
        panel.classList.add('show');
        btn.classList.add('open');
        _openDropdown = name;
    } else {
        _openDropdown = null;
    }
}

function toggleFilter(name, value) {
    const set = activeFilters[name];
    if (set.has(value)) set.delete(value);
    else set.add(value);
    updateFilterBadges();
    currentPage = 1;
    renderPapers();
}

function updateFilterBadges() {
    for (const name of Object.keys(activeFilters)) {
        const badge = document.getElementById(`badge-${name}`);
        const btn = badge?.parentElement;
        if (!badge || !btn) continue;
        const count = activeFilters[name].size;
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-flex' : 'none';
        btn.classList.toggle('has-active', count > 0);
    }
}

function clearAllFilters() {
    for (const key of Object.keys(activeFilters)) activeFilters[key].clear();
    document.querySelectorAll('.filter-dropdown-panel input').forEach(cb => cb.checked = false);
    document.getElementById('search-input').value = '';
    searchQuery = '';
    document.getElementById('date-filter').value = '';
    dateFilter = '';
    updateFilterBadges();
    currentPage = 1;
    renderPapers();
}

function handleSearch() {
    searchQuery = document.getElementById('search-input').value.trim().toLowerCase();
    currentPage = 1;
    renderPapers();
}

function handleDateFilter() {
    dateFilter = document.getElementById('date-filter').value;
    currentPage = 1;
    renderPapers();
}

function toggleSort() {
    const modes = ['desc', 'asc', 'relevance', 'quality', 'citations', 'rec', 'source'];
    const idx = (modes.indexOf(sortOrder) + 1) % modes.length;
    sortOrder = modes[idx];
    const opt = document.querySelector(`[data-sort="${sortOrder}"]`);
    if (opt) {
        const btn = document.querySelector('#dd-sort .sort-btn');
        btn.innerHTML = opt.textContent.trim() + ' <span class="arrow">▼</span>';
        document.querySelectorAll('#panel-sort .filter-option').forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
    }
    renderPapers();
}

function closeAllDropdowns() {
    document.querySelectorAll('.filter-dropdown-panel').forEach(p => p.classList.remove('show'));
    document.querySelectorAll('.filter-dropdown-btn').forEach(b => b.classList.remove('open'));
    _openDropdown = null;
}

// ── Render ──────────────────────────────────────────────────────

function renderPapers() {
    const container = document.getElementById('paper-container');
    filteredPapers = allPapers;

    // Source filter
    const srcSet = activeFilters.source;
    if (srcSet.size > 0) {
        filteredPapers = filteredPapers.filter(p => srcSet.has(p.source));
    }

    // Journal filter
    const jSet = activeFilters.journal;
    if (jSet.size > 0) {
        filteredPapers = filteredPapers.filter(p => jSet.has(p.journal_title));
    }

    // Venue filter
    const venueSet = activeFilters.venue;
    if (venueSet.size > 0) {
        filteredPapers = filteredPapers.filter(p => venueSet.has(p.venue));
    }

    // Category filter
    const catSet = activeFilters.category;
    if (catSet.size > 0) {
        filteredPapers = filteredPapers.filter(p =>
            (p.categories || []).some(c => catSet.has(c))
        );
    }

    // Type filter (includes unread)
    const typeSet = activeFilters.type;
    if (typeSet.size > 0) {
        filteredPapers = filteredPapers.filter(p => {
            if (typeSet.has('unread')) return !_readPapers.has(p.id);
            const at = p.article_type || _inferType(p);
            const rec = (p.AI || {}).recommendation || '';
            return typeSet.has(at) || typeSet.has(rec);
        });
    }

    // Bookmark filter
    const bmSet = activeFilters.bookmarked;
    if (bmSet.size > 0) {
        filteredPapers = filteredPapers.filter(p => _bookmarks.has(p.id));
    }

    // Search (supports title: abstract: author: prefix)
    if (searchQuery) {
        const prefixFields = { 'title:': 'title', 'abstract:': 'summary', 'author:': 'authors' };
        const terms = searchQuery.split(/\s+/);
        filteredPapers = filteredPapers.filter(p => {
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

    // Date filter
    if (dateFilter) {
        filteredPapers = filteredPapers.filter(p => (p.published_date || '').startsWith(dateFilter));
    }

    // Sort
    filteredPapers.sort((a, b) => {
        if (sortOrder === 'relevance') {
            return ((b.AI || {}).relevance_score || 0) - ((a.AI || {}).relevance_score || 0);
        }
        if (sortOrder === 'quality') {
            return ((b.AI || {}).quality_score || 0) - ((a.AI || {}).quality_score || 0);
        }
        if (sortOrder === 'citations') {
            return (b.citation_count || 0) - (a.citation_count || 0);
        }
        if (sortOrder === 'rec') {
            const ra = (b.AI || {}).recommendation === 'must_read' ? 3 :
                       (b.AI || {}).recommendation === 'recommended' ? 2 :
                       (b.AI || {}).recommendation === 'worth_reading' ? 1 : 0;
            const la = (a.AI || {}).recommendation === 'must_read' ? 3 :
                       (a.AI || {}).recommendation === 'recommended' ? 2 :
                       (a.AI || {}).recommendation === 'worth_reading' ? 1 : 0;
            if (ra !== la) return ra - la;
            return ((b.AI || {}).quality_score || 0) - ((a.AI || {}).quality_score || 0);
        }
        if (sortOrder === 'source') {
            const sa = (a.source || '').localeCompare(b.source || '');
            if (sa !== 0) return sa;
            const da = a.published_date || '';
            const db = b.published_date || '';
            return db.localeCompare(da);
        }
        const da = a.published_date || '';
        const db = b.published_date || '';
        return sortOrder === 'desc' ? db.localeCompare(da) : da.localeCompare(db);
    });

    if (!filteredPapers.length) {
        container.innerHTML = '<div class="empty-state">暂无匹配论文。尝试调整筛选条件。</div>';
        updatePaperCount();
        return;
    }

    updatePaperCount();

    const totalPages = Math.ceil(filteredPapers.length / PAGE_SIZE);
    currentPage = Math.max(1, Math.min(currentPage, totalPages || 1));
    const start = (currentPage - 1) * PAGE_SIZE;
    const pagePapers = filteredPapers.slice(start, start + PAGE_SIZE);

    container.innerHTML = pagePapers.map((paper, i) => {
        const ai = paper.AI || {};
        const hasAi = !!(ai.tldr || paper.tldr);
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
        const isBookmarked = _bookmarks.has(paper.id);
        const isRead = _readPapers.has(paper.id);
        return `
            <div class="paper-card ${isRead ? 'is-read' : ''}" data-idx="${idx}" data-rec="${rec}">
                <div class="paper-header">
                    ${sourceBadge}${venueBadge}${accBadge}${aiBadge}${recBadge}${typeTag}
                    <div class="paper-categories">${categories}${codeBadge}</div>
                    <button class="bookmark-btn ${isBookmarked ? 'active' : ''}" data-bm-id="${_escAttr(paper.id)}" title="${isBookmarked ? '取消收藏' : '收藏'}">${isBookmarked ? '★' : '☆'}</button>
                    <button class="feedback-btn" data-feedback-id="${_escAttr(paper.id)}" data-feedback-rating="useful" title="有用">👍</button>
                    <button class="feedback-btn" data-feedback-id="${_escAttr(paper.id)}" data-feedback-rating="not_useful" title="没用">👎</button>
                </div>
                <div class="paper-title">${title}</div>
                ${cardTldr}
                <div class="paper-authors">${authors}</div>
                <div class="paper-summary">${summary.substring(0, 200)}...</div>
                ${scoreBar}
                <div class="paper-meta">
                    <span>${paper.published_date || ''}</span>
                    <span>${citeBadge || (paper.publisher || '')}</span>
                </div>
            </div>
        `;
    }).join('');

    if (totalPages > 1) {
        container.innerHTML += `
            <div class="pagination" style="grid-column:1/-1;display:flex;justify-content:center;gap:8px;padding:16px">
                <button class="follow-btn" onclick="changePage(-1)" ${currentPage <= 1 ? 'disabled style="opacity:0.5"' : ''}>上一页</button>
                <span style="padding:6px 12px;color:var(--text-secondary)">${currentPage}/${totalPages}</span>
                <button class="follow-btn" onclick="changePage(1)" ${currentPage >= totalPages ? 'disabled style="opacity:0.5"' : ''}>下一页</button>
            </div>
        `;
    }
}

function changePage(delta) {
    currentPage += delta;
    renderPapers();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function openPaperDetail(paper) {
    _markRead(paper.id);
    const modal = document.getElementById('paper-modal');
    const detail = document.getElementById('paper-detail');

    const aiTitle = (paper.AI || {}).title_zh || '';
    const titleZh = aiTitle || paper.title_zh || '';
    const titleEn = paper.title || '';
    const title = titleZh || titleEn;
    const origTitle = (titleZh && titleEn && titleZh !== titleEn) ? `<div style="color:var(--text-secondary);font-size:0.85rem;margin-top:4px">${titleEn}</div>` : '';
    const sourceBadge = paper.source === 'crossref'
        ? `<span class="source-badge crossref">${paper.journal_title || 'Journal'}</span>`
        : paper.source === 'dblp'
        ? `<span class="source-badge dblp">DBLP</span>`
        : paper.source === 'semantic_scholar'
        ? `<span class="source-badge s2">S2</span>`
        : `<span class="source-badge arxiv">arXiv</span>`;
    const venueInfo = paper.venue ? ` <span class="venue-badge">${paper.venue}</span>` : '';
    const accInfo = paper.acceptance ? ` <span class="acc-badge ${paper.acceptance}">${paper.acceptance}</span>` : '';
    const citeInfo = paper.citation_count ? `<div style="margin-bottom:8px;font-size:0.85rem;color:var(--text-secondary)">&#9733; ${paper.citation_count} citations</div>` : '';

    const aiFields = paper.AI || {};
    const sections = [];

    // AI analysis: merge into one cohesive block
    const aiParts = [];
    if (aiFields.tldr) aiParts.push(`<b>TL;DR</b> ${aiFields.tldr}`);
    if (aiFields.motivation) aiParts.push(`<b>Motivation</b> ${aiFields.motivation}`);
    if (aiFields.method) aiParts.push(`<b>Method</b> ${aiFields.method}`);
    if (aiFields.result) aiParts.push(`<b>Result</b> ${aiFields.result}`);
    if (aiFields.conclusion) aiParts.push(`<b>Conclusion</b> ${aiFields.conclusion}`);
    if (aiParts.length) {
        sections.push(`<h3>AI 解读</h3><p>${aiParts.join('<br><br>')}</p>`);
    }

    // Fallback to non-AI structured fields
    if (!aiParts.length) {
        const fallbackParts = [];
        if (paper.tldr) fallbackParts.push(`<b>TL;DR</b> ${paper.tldr}`);
        if (paper.motivation) fallbackParts.push(`<b>Motivation</b> ${paper.motivation}`);
        if (paper.method) fallbackParts.push(`<b>Method</b> ${paper.method}`);
        if (paper.result) fallbackParts.push(`<b>Result</b> ${paper.result}`);
        if (paper.conclusion) fallbackParts.push(`<b>Conclusion</b> ${paper.conclusion}`);
        if (fallbackParts.length) {
            sections.push(`<h3>解读</h3><p>${fallbackParts.join('<br><br>')}</p>`);
        }
    }

    // Show Chinese summary if available
    const summaryZh = aiFields.summary_zh || paper.summary_zh || '';
    if (summaryZh) {
        sections.push(`<h3>中文摘要</h3><p>${summaryZh}</p>`);
    }

    // Always show original abstract
    const abstractEn = paper.summary || '';
    if (abstractEn) {
        sections.push(`<h3>Abstract</h3><p>${abstractEn}</p>`);
    }

    // Final fallback
    if (!sections.length) {
        sections.push(`<p style="color:var(--text-secondary)">暂无摘要</p>`);
    }

    const codeUrl = paper.code_url || '';
    const codeStars = paper.code_stars ? ` (${paper.code_stars} stars)` : '';

    detail.innerHTML = `
        <div class="paper-header">${sourceBadge}${venueInfo}${accInfo}
            <span class="paper-cat">${paper.published_date || ''}</span>
        </div>
        <h2 style="margin:12px 0">${title}</h2>
        ${origTitle}
        <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:12px">
            ${(paper.authors || []).join(', ')}
        </p>
        ${citeInfo}
        ${sections.join('')}
        <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap">
            ${paper.url ? `<a href="${paper.url}" target="_blank" class="follow-btn">论文链接</a>` : ''}
            ${paper.pdf ? `<a href="${paper.pdf}" target="_blank" class="follow-btn">PDF</a>` : ''}
            ${paper.doi ? `<a href="https://doi.org/${paper.doi}" target="_blank" class="follow-btn">DOI</a>` : ''}
            ${codeUrl ? `<a href="${codeUrl}" target="_blank" class="follow-btn" style="border-color:#22c55e;color:#22c55e">Code${codeStars}</a>` : ''}
            <button class="follow-btn" data-export-bibtex="${_escAttr(paper.id)}">BibTeX</button>
        </div>
    `;

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closePaperModal() {
    document.getElementById('paper-modal').classList.remove('active');
    document.body.style.overflow = '';
}

function updatePaperCount() {
    const el = document.getElementById('paper-count');
    if (!el) return;
    const total = allPapers.length;
    const shown = filteredPapers.length;
    const hasFilter = searchQuery || dateFilter || Object.values(activeFilters).some(s => s.size > 0);
    el.textContent = hasFilter ? `${shown}/${total} 篇` : `${total} 篇`;
}

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

function _inferType(p) {
    if (p.source === 'arxiv') return 'research';
    const doi = p.doi || '';
    if (doi.includes('/s41586-')) return 'research';
    if (doi.includes('/d41586-')) return 'news';
    return p.summary ? 'research' : 'news';
}

async function triggerCrawl(job) {
    if (job === 'enhance') {
        try {
            const resp = await fetch('/api/trigger/enhance', { method: 'POST' });
            showToast(resp.ok ? '补 AI 增强已启动' : '启动失败');
        } catch { showToast('启动失败'); }
        setTimeout(loadPapers, 30000);
        return;
    }
    const jobs = job === 'all' ? ['arxiv', 'crossref', 'dblp', 's2'] : [job];
    for (const j of jobs) {
        const el = document.getElementById(`crawl-${j}`);
        if (el) el.textContent = '...';
        try {
            const resp = await fetch(`/api/trigger/${j}`, { method: 'POST' });
            if (el) el.textContent = resp.ok ? '⏳' : '✗';
        } catch {
            if (el) el.textContent = '✗';
        }
    }
    // Poll job status
    const pollInterval = setInterval(async () => {
        try {
            const resp = await fetch('/api/jobs');
            if (!resp.ok) return;
            const status = await resp.json();
            let allDone = true;
            for (const j of jobs) {
                const s = status[j];
                const el = document.getElementById(`crawl-${j}`);
                if (!s || s.status === 'running') { allDone = false; if (el) el.textContent = '⏳'; }
                else if (s.status === 'done') { if (el) el.textContent = `✓ ${s.message || ''}`; }
                else if (s.status === 'error') { if (el) el.textContent = '✗'; }
                else { if (el) el.textContent = '—'; }
            }
            if (allDone) {
                clearInterval(pollInterval);
                loadPapers();
                setTimeout(() => {
                    jobs.forEach(j => { const el = document.getElementById(`crawl-${j}`); if (el) el.textContent = '—'; });
                }, 10000);
            }
        } catch { clearInterval(pollInterval); }
    }, 3000);
}
