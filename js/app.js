// js/app.js
let allPapers = [];
let filteredPapers = [];
let activeFilters = {
    source: new Set(),    // 'arxiv', 'crossref'
    journal: new Set(),   // journal names
    category: new Set(),  // arXiv categories
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
    ]);
    renderFilterDropdown('journal',
        Object.entries(journals).sort((a,b) => b[1]-a[1]).map(([j, c]) => ({ value: j, label: j, count: c }))
    );
    renderFilterDropdown('category',
        Object.entries(categories).sort((a,b) => b[1]-a[1]).map(([c, n]) => ({ value: c, label: c, count: n }))
    );
    renderFilterDropdown('type', [
        { value: 'research', label: '研究论文' },
        { value: 'news', label: '新闻评论' },
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
    sortOrder = sortOrder === 'desc' ? 'asc' : 'desc';
    document.getElementById('sort-btn').textContent = sortOrder === 'desc' ? '↓ 新→旧' : '↑ 旧→新';
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
            return typeSet.has(at);
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
            : `<span class="source-badge arxiv">arXiv</span>`;
        const articleType = paper.article_type || _inferType(paper);
        const typeTag = articleType === 'news'
            ? '<span class="paper-cat" style="background:rgba(249,115,22,0.2);color:#f97316">新闻</span>'
            : '';
        const aiBadge = hasAi ? '<span class="ai-badge">AI</span>' : '';

        const categories = (paper.categories || []).map(c =>
            `<span class="paper-cat">${c}</span>`
        ).join('');

        const authors = (paper.authors || []).slice(0, 3).join(', ') +
            ((paper.authors || []).length > 3 ? ' et al.' : '');

        const summary = ai.summary_zh || paper.summary_zh || paper.summary || '';
        const title = ai.title_zh || paper.title_zh || paper.title || '';
        const tldr = (ai.tldr || paper.tldr) ? `<div class="paper-tldr">${ai.tldr || paper.tldr}</div>` : '';
        const codeBadge = paper.code_url ? `<span class="paper-cat" style="background:rgba(34,197,94,0.2);color:#22c55e">Code</span>` : '';

        const idx = start + i;
        return `
            <div class="paper-card" data-idx="${idx}">
                <div class="paper-header">
                    ${sourceBadge}${aiBadge}${typeTag}
                    <div class="paper-categories">${categories}${codeBadge}</div>
                </div>
                <div class="paper-title">${title}</div>
                <div class="paper-authors">${authors}</div>
                <div class="paper-summary">${summary.substring(0, 200)}...</div>
                ${tldr}
                <div class="paper-meta">
                    <span>${paper.published_date || ''}</span>
                    <span>${paper.publisher || ''}</span>
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

    const title = paper.title_zh || paper.title;
    const origTitle = (paper.title_zh && paper.title) ? `<div style="color:var(--text-secondary);font-size:0.85rem;margin-top:4px">${paper.title}</div>` : '';
    const sourceBadge = paper.source === 'crossref'
        ? `<span class="source-badge crossref">${paper.journal_title || 'Journal'}</span>`
        : `<span class="source-badge arxiv">arXiv</span>`;

    const aiFields = paper.AI || {};
    const sections = [];
    if (aiFields.tldr) sections.push(`<h3>TL;DR</h3><p>${aiFields.tldr}</p>`);
    if (aiFields.motivation) sections.push(`<h3>Motivation</h3><p>${aiFields.motivation}</p>`);
    if (aiFields.method) sections.push(`<h3>Method</h3><p>${aiFields.method}</p>`);
    if (aiFields.result) sections.push(`<h3>Result</h3><p>${aiFields.result}</p>`);
    if (aiFields.conclusion) sections.push(`<h3>Conclusion</h3><p>${aiFields.conclusion}</p>`);

    if (!sections.length) {
        if (paper.tldr) sections.push(`<h3>TL;DR</h3><p>${paper.tldr}</p>`);
        if (paper.motivation) sections.push(`<h3>Motivation</h3><p>${paper.motivation}</p>`);
        if (paper.method) sections.push(`<h3>Method</h3><p>${paper.method}</p>`);
        if (paper.result) sections.push(`<h3>Result</h3><p>${paper.result}</p>`);
        if (paper.conclusion) sections.push(`<h3>Conclusion</h3><p>${paper.conclusion}</p>`);
    }

    const abstract = paper.summary_zh || aiFields.summary_zh || paper.summary || '';
    if (abstract && !sections.length) sections.push(`<h3>Abstract</h3><p>${abstract}</p>`);

    const codeUrl = paper.code_url || '';
    const codeStars = paper.code_stars ? ` (${paper.code_stars} stars)` : '';

    detail.innerHTML = `
        <div class="paper-header">${sourceBadge}
            <span class="paper-cat">${paper.published_date || ''}</span>
        </div>
        <h2 style="margin:12px 0">${title}</h2>
        ${origTitle}
        <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:12px">
            ${(paper.authors || []).join(', ')}
        </p>
        ${sections.join('<hr style="border-color:var(--border-color);margin:12px 0">')}
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

function _inferType(p) {
    if (p.source === 'arxiv') return 'research';
    const doi = p.doi || '';
    if (doi.includes('/s41586-')) return 'research';
    if (doi.includes('/d41586-')) return 'news';
    return p.summary ? 'research' : 'news';
}
