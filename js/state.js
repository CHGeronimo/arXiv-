// js/state.js — shared application state

export let allPapers = [];
export let filteredPapers = [];
export let activeFilters = {
    source: new Set(),
    journal: new Set(),
    category: new Set(),
    venue: new Set(),
    type: new Set(),
    bookmarked: new Set(),
    ccf: new Set(),
    today: new Set(),
    code: new Set(),
};
export let searchQuery = '';
export let dateFilter = '';
export let dateWithinDays = 0;  // >0 = 最近N天入库快捷筛选（created_at 窗口）
export let sortOrder = 'desc';
export let refreshTimer = null;
export let currentPage = 1;
export const PAGE_SIZE = 40;

export let currentTheme = localStorage.getItem('theme') || 'dark';
export let sidebarOpen = false;

const THEMES = ['dark', 'light', 'academic', 'warm', 'auto'];
export function cycleThemeList() { return THEMES; }

function _resolvedTheme(t) {
    if (t !== 'auto') return t;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export function setCurrentTheme(t) {
    currentTheme = t;
    localStorage.setItem('theme', t);
    document.documentElement.setAttribute('data-theme', _resolvedTheme(t));
    if (t === 'auto' && window.matchMedia) {
        try {
            window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
                if (currentTheme === 'auto')
                    document.documentElement.setAttribute('data-theme', _resolvedTheme('auto'));
            });
        } catch {}
    }
}

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

export const _bookmarks = new Set(JSON.parse(localStorage.getItem('bookmarks') || '[]'));
export const _readPapers = new Set(JSON.parse(localStorage.getItem('readPapers') || '[]'));

function _postFlag(url, body) {
    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    }).catch(() => {});
}

export async function syncServerFlags() {
    // 启动时把服务端收藏/已读合并进本地（服务端为准补充，本地缓存兜底）
    try {
        const resp = await fetch('/api/bookmarks');
        if (!resp.ok) return;
        const { bookmarks = [], reads = [] } = await resp.json();
        let changed = false;
        bookmarks.forEach(id => { if (!_bookmarks.has(id)) { _bookmarks.add(id); changed = true; } });
        reads.forEach(id => { if (!_readPapers.has(id)) { _readPapers.add(id); changed = true; } });
        if (changed) {
            localStorage.setItem('bookmarks', JSON.stringify([..._bookmarks]));
            localStorage.setItem('readPapers', JSON.stringify([..._readPapers]));
        }
    } catch {}
}

// Mutators
export function setAllPapers(p) { allPapers = p; }
export function setFilteredPapers(p) { filteredPapers = p; }
export function setSearchQuery(q) { searchQuery = q; }
export function setDateFilter(d) { dateFilter = d; }
export function setDateWithinDays(d) { dateWithinDays = d; }
export function setSortOrder(s) { sortOrder = s; }
export function setCurrentPage(p) { currentPage = p; }
export function setRefreshTimer(t) { refreshTimer = t; }

// ── UI 状态持久化（F5 恢复筛选/排序/搜索/页码）──
export function saveUIState() {
    try {
        const st = {
            filters: Object.fromEntries(Object.entries(activeFilters).map(([k, s]) => [k, [...s]])),
            sort: sortOrder,
            page: currentPage,
            search: document.getElementById('sidebar-search-input')?.value || '',
            date: document.getElementById('sidebar-date-filter')?.value || '',
            within: dateWithinDays,
        };
        localStorage.setItem('uiState', JSON.stringify(st));
    } catch {}
}

export function restoreUIState() {
    try {
        const st = JSON.parse(localStorage.getItem('uiState') || 'null');
        if (!st) return false;
        for (const [k, arr] of Object.entries(st.filters || {})) {
            if (activeFilters[k]) activeFilters[k] = new Set(arr);
        }
        sortOrder = st.sort || 'desc';
        currentPage = st.page || 1;
        dateWithinDays = st.within || 0;
        const si = document.getElementById('sidebar-search-input');
        if (si && st.search) si.value = st.search;
        const di = document.getElementById('sidebar-date-filter');
        if (di && st.date) di.value = st.date;
        return true;
    } catch { return false; }
}

export function clearUIState() {
    try { localStorage.removeItem('uiState'); } catch {}
}

export function saveBookmarks() {
    localStorage.setItem('bookmarks', JSON.stringify([..._bookmarks]));
}
export function toggleBookmark(id) {
    const on = !_bookmarks.has(id);
    if (on) _bookmarks.add(id);
    else _bookmarks.delete(id);
    saveBookmarks();
    _postFlag('/api/bookmark', { paper_id: id, on });
}
export function markRead(id) {
    if (!_readPapers.has(id)) {
        _readPapers.add(id);
        localStorage.setItem('readPapers', JSON.stringify([..._readPapers]));
        _postFlag('/api/read', { paper_id: id });
        return true;
    }
    return false;
}

export function showToast(msg, duration = 2000) {
    let el = document.getElementById('toast');
    if (!el) { el = document.createElement('div'); el.id = 'toast'; document.body.appendChild(el); }
    el.textContent = msg;
    el.className = 'toast show';
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.className = 'toast'; }, duration);
}

export function escAttr(s) {
    return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;');
}

export function inferType(p) {
    if (p.source === 'arxiv') return 'research';
    const doi = p.doi || '';
    if (doi.includes('/s41586-')) return 'research';
    if (doi.includes('/d41586-')) return 'news';
    return p.summary ? 'research' : 'news';
}

export let feedbackData = {};

export function setFeedbackData(data) {
    feedbackData = data;
}

export function getFeedbackForPaper(paperId) {
    return feedbackData[paperId] || {};
}
