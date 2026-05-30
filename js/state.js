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
};
export let searchQuery = '';
export let dateFilter = '';
export let sortOrder = 'desc';
export let refreshTimer = null;
export let currentPage = 1;
export const PAGE_SIZE = 40;

export const _bookmarks = new Set(JSON.parse(localStorage.getItem('bookmarks') || '[]'));
export const _readPapers = new Set(JSON.parse(localStorage.getItem('readPapers') || '[]'));

// Mutators
export function setAllPapers(p) { allPapers = p; }
export function setFilteredPapers(p) { filteredPapers = p; }
export function setSearchQuery(q) { searchQuery = q; }
export function setDateFilter(d) { dateFilter = d; }
export function setSortOrder(s) { sortOrder = s; }
export function setCurrentPage(p) { currentPage = p; }
export function setRefreshTimer(t) { refreshTimer = t; }

export function saveBookmarks() {
    localStorage.setItem('bookmarks', JSON.stringify([..._bookmarks]));
}
export function toggleBookmark(id) {
    _bookmarks.has(id) ? _bookmarks.delete(id) : _bookmarks.add(id);
    saveBookmarks();
}
export function markRead(id) {
    if (!_readPapers.has(id)) {
        _readPapers.add(id);
        localStorage.setItem('readPapers', JSON.stringify([..._readPapers]));
    }
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
