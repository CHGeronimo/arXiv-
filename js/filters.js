// js/filters.js — filter and sort logic

import {
    allPapers, filteredPapers, activeFilters, searchQuery, dateFilter, dateWithinDays, sortOrder,
    currentPage, _bookmarks, _readPapers, escAttr, inferType,
    setFilteredPapers, setCurrentPage,
} from './state.js';

export let _filterCounts = {};

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
            { value: 'openalex', label: 'OA 搜索' },
            { value: 'citation', label: '引文追踪' },
            { value: 'author_s2', label: '作者' },
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
        { key: 'type', label: '推荐级别', options: [
            { value: 'must-read', label: 'Must Read' },
            { value: 'recommended', label: 'Recommended' },
            { value: 'reference', label: 'Reference' },
            { value: 'ref-low', label: '浅参考' },
            { value: 'ignore', label: '已过滤' },
            { value: 'unread', label: '未读' },
        ]},
        { key: 'today', label: '时效', options: [
            { value: 'yes', label: '🌅 今日新到' },
        ]},
        { key: 'code', label: '代码', options: [
            { value: 'yes', label: '🐙 有代码' },
        ]},
        { key: 'bookmarked', label: '收藏', options: [
            { value: 'yes', label: '⭐ 已收藏' },
        ]},
        { key: 'ccf', label: 'CCF 等级', options: [
            { value: 'A', label: 'CCF-A' },
            { value: 'B', label: 'CCF-B' },
            { value: 'C', label: 'CCF-C' },
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

export function toggleFilter(name, value) {
    const set = activeFilters[name];
    if (set.has(value)) set.delete(value);
    else set.add(value);
    updateFilterBadges();
    setCurrentPage(1);
}

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

export function clearAllFilters() {
    for (const key of Object.keys(activeFilters)) activeFilters[key].clear();
    document.querySelectorAll('#sidebar-filter-groups input[type="checkbox"]').forEach(cb => cb.checked = false);
    const searchInput = document.getElementById('sidebar-search-input');
    const dateInput = document.getElementById('sidebar-date-filter');
    if (searchInput) searchInput.value = '';
    if (dateInput) dateInput.value = '';
    setCurrentPage(1);
}

export function handleSearch() {
    // searchQuery is read fresh via import
}

export function applyFiltersAndSort() {
    const showIgnored = activeFilters.type.has('ignore');
    const showRefLow = activeFilters.type.has('ref-low');
    let result = [...allPapers].filter(p => {
        const ai = p.AI || {};
        if (ai.recommendation === 'ignore') return showIgnored;
        if (ai.recommendation === 'reference' && (ai.relevance_score || 0) < 7) return showRefLow;
        return true;
    });

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
            const ai = p.AI || {};
            const rec = ai.recommendation || '';
            const isRefLow = rec === 'reference' && (ai.relevance_score || 0) < 7;
            const recKey = isRefLow ? 'ref-low' : rec;
            const at = p.article_type || inferType(p);

            // Build all applicable type tags for this paper
            const tags = new Set([at, recKey]);
            if (!_readPapers.has(p.id)) tags.add('unread');

            // Intersection: paper must match ALL selected type filters
            for (const f of activeFilters.type) {
                if (!tags.has(f)) return false;
            }
            return true;
        });
    if (activeFilters.bookmarked.size > 0)
        result = result.filter(p => _bookmarks.has(p.id));
    if (activeFilters.ccf.size > 0)
        result = result.filter(p => activeFilters.ccf.has(p.ccf_tier || ''));
    if (activeFilters.today.size > 0) {
        // created_at 是 UTC：本地凌晨 2 点的跑批落在 UTC 前一天，36h 窗口兜住
        const cutoff = new Date(Date.now() - 36 * 3600 * 1000).toISOString().slice(0, 10);
        result = result.filter(p => (p.created_at || '') >= cutoff);
    }
    if (activeFilters.code.size > 0)
        result = result.filter(p => !!p.code_url);
    if (dateWithinDays > 0) {
        // 快捷日期段（今天/3天/7天/30天）：按入库时间
        const cutoff = new Date(Date.now() - dateWithinDays * 24 * 3600 * 1000).toISOString().slice(0, 10);
        result = result.filter(p => (p.created_at || '') >= cutoff);
    }

    const sq = document.getElementById('sidebar-search-input')?.value?.trim().toLowerCase() || '';
    if (sq) {
        // 列表为轻字段模式（无摘要全文），abstract: 前缀已移除；
        // 普通搜索覆盖 标题(中英) + TLDR + 作者
        const prefixFields = { 'title:': 'title', 'author:': 'authors' };
        const terms = sq.split(/\s+/);
        result = result.filter(p => {
            return terms.every(term => {
                for (const [prefix, field] of Object.entries(prefixFields)) {
                    if (term.startsWith(prefix)) {
                        const q = term.slice(prefix.length);
                        if (!q) return true;
                        if (field === 'authors') return (p.authors || []).some(a => a.toLowerCase().includes(q));
                        const val = ((p.AI || {}).title_zh || p.title || '').toLowerCase();
                        return val.includes(q);
                    }
                }
                const allText = ((p.AI || {}).title_zh || p.title || '') + ' ' +
                    ((p.AI || {}).tldr || '') + ' ' +
                    (p.authors || []).join(' ');
                return allText.toLowerCase().includes(term);
            });
        });
    }

    const df = document.getElementById('sidebar-date-filter')?.value || '';
    if (df) {
        result = result.filter(p => (p.published_date || '').startsWith(df));
    }

    result.sort((a, b) => {
        if (sortOrder === 'relevance') return ((b.AI || {}).relevance_score || 0) - ((a.AI || {}).relevance_score || 0);
        if (sortOrder === 'quality') return ((b.AI || {}).quality_score || 0) - ((a.AI || {}).quality_score || 0);
        if (sortOrder === 'citations') return (b.citation_count || 0) - (a.citation_count || 0);
        if (sortOrder === 'rec') {
            const recRank = { 'must-read': 5, 'recommended': 4, 'reference': 3, 'ref-low': 2, 'ignore': 1 };
            const getRecKey = (p) => {
                const rec = (p.AI || {}).recommendation || '';
                const rel = (p.AI || {}).relevance_score || 0;
                if (rec === 'reference' && rel < 7) return 'ref-low';
                return rec;
            };
            const ra = recRank[getRecKey(b)] || 0;
            const la = recRank[getRecKey(a)] || 0;
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
    // No-op: sidebar replaces dropdowns
}
