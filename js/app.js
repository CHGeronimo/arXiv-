// js/app.js
let allPapers = [];
let filteredPapers = [];
let activeFilters = {
    source: new Set(),    // 'arxiv', 'crossref', 'dblp', 'semantic_scholar'
    journal: new Set(),   // journal names
    category: new Set(),  // arXiv categories
    venue: new Set(),     // conference venues
    type: new Set(),      // 'research', 'news'
};
let searchQuery = '';
let dateFilter = '';
let sortOrder = 'desc';
let refreshTimer = null;
let currentPage = 1;
const PAGE_SIZE = 30;

document.addEventListener('DOMContentLoaded', () => {
    loadPapers();
    startAutoRefresh();

    document.getElementById('paper-container').addEventListener('click', (e) => {
        const card = e.target.closest('.paper-card[data-idx]');
        if (card) {
            const idx = parseInt(card.dataset.idx);
            if (filteredPapers[idx]) openPaperDetail(filteredPapers[idx]);
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closePaperModal();
            closeSubscriptionModal();
            closeProfileModal();
            closeAllDropdowns();
        }
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
    ]);
    updateFilterBadges();
}

function renderFilterDropdown(name, options) {
    const panel = document.getElementById(`panel-${name}`);
    if (!panel) return;
    const active = activeFilters[name];
    panel.innerHTML = options.map(o => `
        <label class="filter-option">
            <input type="checkbox" ${active.has(o.value) ? 'checked' : ''}
                   onchange="toggleFilter('${name}', '${o.value}')">
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
    const modes = ['desc', 'asc', 'relevance', 'quality'];
    const labels = ['↓ 新→旧', '↑ 旧→新', '★ 相关性', '✦ 质量'];
    const idx = (modes.indexOf(sortOrder) + 1) % modes.length;
    sortOrder = modes[idx];
    document.getElementById('sort-btn').textContent = labels[idx];
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

    // Type filter
    const typeSet = activeFilters.type;
    if (typeSet.size > 0) {
        filteredPapers = filteredPapers.filter(p => {
            const at = p.article_type || _inferType(p);
            const rec = (p.AI || {}).recommendation || '';
            return typeSet.has(at) || typeSet.has(rec);
        });
    }

    // Search
    if (searchQuery) {
        filteredPapers = filteredPapers.filter(p => {
            const text = ((p.title_zh || p.title || '') + ' ' + (p.summary_zh || p.summary || '') + ' ' + (p.authors || []).join(' ')).toLowerCase();
            return text.includes(searchQuery);
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
    if (currentPage > totalPages) currentPage = totalPages || 1;
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
        return `
            <div class="paper-card" data-idx="${idx}" data-rec="${rec}">
                <div class="paper-header">
                    ${sourceBadge}${venueBadge}${accBadge}${aiBadge}${recBadge}${typeTag}
                    <div class="paper-categories">${categories}${codeBadge}</div>
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
        </div>
    `;

    modal.classList.add('active');
}

function closePaperModal() {
    document.getElementById('paper-modal').classList.remove('active');
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
