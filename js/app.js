// js/app.js — entry point

import {
    setAllPapers, setRefreshTimer, setSortOrder, setCurrentPage,
    refreshTimer, toggleBookmark, showToast,
    filteredPapers, currentPage,
} from './state.js';
import { fetchPapers, quickFollowAuthor, triggerCrawl, saveFeedback, exportBibtex } from './api.js';
import { buildFilterOptions, toggleFilter, toggleDropdown, clearAllFilters, closeAllDropdowns } from './filters.js';
import { renderPapers, changePage } from './render.js';
import { openPaperDetail, closePaperModal, openProfileModal, closeProfileModal, saveProfile } from './modal.js';

// Theme
function _initTheme() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute('data-theme', saved || (prefersDark ? 'dark' : 'light'));
}
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    document.getElementById('btn-theme').textContent = next === 'dark' ? '🌙' : '☀️';
}
_initTheme();

// Expose for inline onclick handlers
window._toggleFilter = (name, value) => { toggleFilter(name, value); renderPapers(); };
window._changePage = changePage;

// Data loading
async function loadPapers() {
    try {
        const papers = await fetchPapers();
        setAllPapers(papers);
    } catch (e) {
        console.error('Failed to load papers:', e);
    }
    buildFilterOptions();
    renderPapers();
}

function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    const timer = setInterval(async () => {
        try {
            const papers = await fetchPapers();
            const { allPapers } = await import('./state.js');
            if (papers.length !== allPapers.length) {
                setAllPapers(papers);
                buildFilterOptions();
                renderPapers();
            }
        } catch {}
    }, 15000);
    setRefreshTimer(timer);
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    loadPapers();
    startAutoRefresh();
    window.addEventListener('beforeunload', () => { if (refreshTimer) clearInterval(refreshTimer); });

    // Sort panel
    document.getElementById('panel-sort')?.addEventListener('click', (e) => {
        const opt = e.target.closest('[data-sort]');
        if (!opt) return;
        setSortOrder(opt.dataset.sort);
        const btn = document.querySelector('#dd-sort .sort-btn');
        btn.innerHTML = opt.textContent.trim() + ' <span class="arrow">▼</span>';
        document.querySelectorAll('#panel-sort .filter-option').forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        closeAllDropdowns();
        renderPapers();
    });

    document.getElementById('btn-profile').addEventListener('click', openProfileModal);
    document.getElementById('btn-theme').addEventListener('click', toggleTheme);
    document.getElementById('btn-subs').addEventListener('click', () => window.openSubscriptionModal());
    document.getElementById('btn-clear-filters').addEventListener('click', () => { clearAllFilters(); renderPapers(); });
    document.getElementById('search-input').addEventListener('input', () => renderPapers());
    document.getElementById('date-filter').addEventListener('change', () => renderPapers());

    // Dropdown toggle
    document.querySelectorAll('[data-dropdown]').forEach(btn => {
        btn.addEventListener('click', () => toggleDropdown(btn.dataset.dropdown));
    });

    // Crawl trigger
    document.getElementById('panel-crawl').addEventListener('click', (e) => {
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

    // Subscription modal (functions from subscriptions.js — global scope)
    document.getElementById('close-subs-modal').addEventListener('click', () => window.closeSubscriptionModal());
    document.getElementById('subscription-modal').addEventListener('click', (e) => { if (e.target === e.currentTarget) window.closeSubscriptionModal(); });
    document.getElementById('btn-save-keywords').addEventListener('click', () => window.saveSearchKeywords?.());
    document.getElementById('sub-tabs-container').addEventListener('click', (e) => {
        const tab = e.target.closest('[data-tab]');
        if (tab) window.switchSubTab(tab.dataset.tab, tab);
    });
    document.getElementById('journal-search-input')?.addEventListener('input', (e) => window.handleJournalSearch?.());
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
            // Live import to get current filteredPapers
            const { filteredPapers: fp } = await import('./state.js');
            if (fp[idx]) openPaperDetail(fp[idx]);
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', async (e) => {
        const active = document.activeElement;
        const typing = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA');
        if (e.key === 'Escape') { closePaperModal(); window.closeSubscriptionModal?.(); closeProfileModal(); closeAllDropdowns(); return; }
        if (typing) return;
        if (e.key === 'j') changePage(1);
        else if (e.key === 'k') changePage(-1);
        else if (e.key === 'f') {
            const { filteredPapers: fp, currentPage: cp, toggleBookmark: tb } = await import('./state.js');
            const first = fp[cp - 1];
            if (first) { tb(first.id); renderPapers(); }
        }
        else if (e.key === '/') { e.preventDefault(); document.getElementById('search-input').focus(); }
        else if (e.key === '?') { showToast('j/k 翻页 | f 收藏首篇 | / 搜索 | ? 帮助', 3000); }
    });

    // Close dropdowns on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.filter-dropdown')) closeAllDropdowns();
    });
});
