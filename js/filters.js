// js/filters.js — filter and sort logic

import {
    allPapers, filteredPapers, activeFilters, searchQuery, dateFilter, sortOrder,
    currentPage, _bookmarks, _readPapers, escAttr, inferType,
    setFilteredPapers, setCurrentPage,
} from './state.js';

export let _filterCounts = {};
export let _openDropdown = null;

export function buildFilterOptions() {
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
        Object.entries(journals).sort((a, b) => b[1] - a[1]).map(([j, c]) => ({ value: j, label: j, count: c }))
    );
    const venues = {};
    for (const p of allPapers) {
        if (p.venue) venues[p.venue] = (venues[p.venue] || 0) + 1;
    }
    _filterCounts.venues = venues;
    renderFilterDropdown('venue',
        Object.entries(venues).sort((a, b) => b[1] - a[1]).map(([v, c]) => ({ value: v, label: v, count: c }))
    );
    renderFilterDropdown('category',
        Object.entries(categories).sort((a, b) => b[1] - a[1]).map(([c, n]) => ({ value: c, label: c, count: n }))
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

function renderFilterDropdown(name, options) {
    const panel = document.getElementById(`panel-${name}`);
    if (!panel) return;
    const active = activeFilters[name];
    panel.innerHTML = options.map(o => `
        <label class="filter-option">
            <input type="checkbox" ${active.has(o.value) ? 'checked' : ''}
                   onchange="window._toggleFilter('${escAttr(name)}', '${escAttr(o.value)}')">
            <span>${o.label}</span>
            ${o.count != null ? `<span class="count">${o.count}</span>` : ''}
        </label>
    `).join('');
}

export function toggleDropdown(name) {
    const panel = document.getElementById(`panel-${name}`);
    const btn = panel.previousElementSibling;
    const isOpen = panel.classList.contains('show');
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

export function toggleFilter(name, value) {
    const set = activeFilters[name];
    if (set.has(value)) set.delete(value);
    else set.add(value);
    updateFilterBadges();
    setCurrentPage(1);
}

export function updateFilterBadges() {
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

export function clearAllFilters() {
    for (const key of Object.keys(activeFilters)) activeFilters[key].clear();
    document.querySelectorAll('.filter-dropdown-panel input').forEach(cb => cb.checked = false);
    document.getElementById('search-input').value = '';
    document.getElementById('date-filter').value = '';
    setCurrentPage(1);
}

export function handleSearch() {
    // searchQuery is read fresh via import
}

export function applyFiltersAndSort() {
    let result = [...allPapers];

    if (activeFilters.source.size > 0)
        result = result.filter(p => activeFilters.source.has(p.source));
    if (activeFilters.journal.size > 0)
        result = result.filter(p => activeFilters.journal.has(p.journal_title));
    if (activeFilters.venue.size > 0)
        result = result.filter(p => activeFilters.venue.has(p.venue));
    if (activeFilters.category.size > 0)
        result = result.filter(p => (p.categories || []).some(c => activeFilters.category.has(c)));
    if (activeFilters.type.size > 0)
        result = result.filter(p => {
            if (activeFilters.type.has('unread')) return !_readPapers.has(p.id);
            const at = p.article_type || inferType(p);
            const rec = (p.AI || {}).recommendation || '';
            return activeFilters.type.has(at) || activeFilters.type.has(rec);
        });
    if (activeFilters.bookmarked.size > 0)
        result = result.filter(p => _bookmarks.has(p.id));

    const sq = document.getElementById('search-input')?.value?.trim().toLowerCase() || '';
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

    const df = document.getElementById('date-filter')?.value || '';
    if (df) {
        result = result.filter(p => (p.published_date || '').startsWith(df));
    }

    result.sort((a, b) => {
        if (sortOrder === 'relevance') return ((b.AI || {}).relevance_score || 0) - ((a.AI || {}).relevance_score || 0);
        if (sortOrder === 'quality') return ((b.AI || {}).quality_score || 0) - ((a.AI || {}).quality_score || 0);
        if (sortOrder === 'citations') return (b.citation_count || 0) - (a.citation_count || 0);
        if (sortOrder === 'rec') {
            const ra = (b.AI || {}).recommendation === 'must_read' ? 3 : (b.AI || {}).recommendation === 'recommended' ? 2 : (b.AI || {}).recommendation === 'worth_reading' ? 1 : 0;
            const la = (a.AI || {}).recommendation === 'must_read' ? 3 : (a.AI || {}).recommendation === 'recommended' ? 2 : (a.AI || {}).recommendation === 'worth_reading' ? 1 : 0;
            if (ra !== la) return ra - la;
            return ((b.AI || {}).quality_score || 0) - ((a.AI || {}).quality_score || 0);
        }
        if (sortOrder === 'source') {
            const sa = (a.source || '').localeCompare(b.source || '');
            if (sa !== 0) return sa;
            return (b.published_date || '').localeCompare(a.published_date || '');
        }
        const da = a.published_date || '';
        const db = b.published_date || '';
        return sortOrder === 'desc' ? db.localeCompare(da) : da.localeCompare(db);
    });

    setFilteredPapers(result);
    return result;
}

export function closeAllDropdowns() {
    document.querySelectorAll('.filter-dropdown-panel').forEach(p => p.classList.remove('show'));
    document.querySelectorAll('.filter-dropdown-btn').forEach(b => b.classList.remove('open'));
    _openDropdown = null;
}
