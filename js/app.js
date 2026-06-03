// js/app.js — entry point

import {
    setAllPapers, setRefreshTimer, setSortOrder, setCurrentPage,
    refreshTimer, toggleBookmark, showToast,
    filteredPapers, currentPage, setCurrentTheme, currentTheme, setSidebarOpen, sidebarOpen,
    setFeedbackData, feedbackData,
} from './state.js';
import { fetchPapers, quickFollowAuthor, triggerCrawl, exportBibtex, deletePaper as apiDeletePaper } from './api.js';
import { buildFilterOptions, toggleFilter, clearAllFilters } from './filters.js';
import { renderPapers, changePage } from './render.js';
import { openPaperDetail, closePaperModal, openProfileModal, closeProfileModal, saveProfile } from './modal.js';
import { loadGraph } from './graph.js';
import { loadTrendRadar } from './trend.js';

// Theme
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

// Expose for inline onclick handlers
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

async function fetchFeedback() {
    try {
        const resp = await fetch('/api/feedback');
        if (resp.ok) {
            const data = await resp.json();
            setFeedbackData(data);
        }
    } catch (e) {
        console.error('Failed to load feedback:', e);
    }
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
    fetchFeedback();
    startAutoRefresh();
    window.addEventListener('beforeunload', () => { if (refreshTimer) clearInterval(refreshTimer); });

    // Sidebar toggle (in header)
    const sidebarToggle = document.getElementById('sidebar-toggle');
    sidebarToggle?.addEventListener('click', () => {
        const isOpen = sidebarOpen;
        setSidebarOpen(!isOpen);
        sidebarToggle.classList.toggle('active', !isOpen);
    });

    // Sidebar filter group expand/collapse
    document.getElementById('sidebar-filter-groups')?.addEventListener('click', (e) => {
        const header = e.target.closest('[data-group-toggle]');
        if (!header) return;
        const key = header.dataset.groupToggle;
        if (key === 'sort') return;
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

    // Sidebar search and date
    document.getElementById('sidebar-search-input')?.addEventListener('input', () => renderPapers());
    document.getElementById('sidebar-date-filter')?.addEventListener('change', () => renderPapers());

    // Sidebar clear
    document.getElementById('sidebar-clear')?.addEventListener('click', () => { clearAllFilters(); buildFilterOptions(); renderPapers(); });

    document.getElementById('btn-profile').addEventListener('click', openProfileModal);
    document.getElementById('btn-theme').addEventListener('click', cycleTheme);
    document.getElementById('btn-subs').addEventListener('click', () => window.openSubscriptionModal());

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
            return;
        }
                const delBtn = e.target.closest('[data-delete-id]');
        if (delBtn) {
            e.stopPropagation();
            const paperId = delBtn.dataset.deleteId;
            if (!confirm('确定删除这篇论文？此操作不可恢复。')) return;
            apiDeletePaper(paperId).then(() => {
                showToast('论文已删除');
                closePaperModal();
                loadPapers();
            }).catch(() => showToast('删除失败'));
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
        if (e.key === 'Escape') {
            // Close all modals uniformly
            document.querySelectorAll('.modal.active, .subscription-modal.active').forEach(m => {
                m.classList.remove('active');
            });
            document.body.style.overflow = '';
            return;
        }
        if (typing) return;
        if (e.key === 'j') changePage(1);
        else if (e.key === 'k') changePage(-1);
        else if (e.key === 'f') {
            const { filteredPapers: fp, currentPage: cp, toggleBookmark: tb } = await import('./state.js');
            const first = fp[cp - 1];
            if (first) { tb(first.id); renderPapers(); }
        }
        else if (e.key === '/') { e.preventDefault(); document.getElementById('sidebar-search-input')?.focus(); }
        else if (e.key === '?') { showToast('j/k 翻页 | f 收藏首篇 | / 搜索 | ? 帮助', 3000); }
    });

    // Knowledge graph
    document.getElementById('btn-refresh-graph')?.addEventListener('click', loadGraph);

    // Trend radar
    document.getElementById('btn-generate-trend')?.addEventListener('click', async () => {
        await fetch('/api/trigger/trend', { method: 'POST' });
        showToast('趋势报告生成中...');
        setTimeout(loadTrendRadar, 30000);
    });

    // Idea check
    document.getElementById('btn-check-idea')?.addEventListener('click', async () => {
        const idea = document.getElementById('idea-input')?.value?.trim();
        if (!idea) return;
        const emptyEl = document.getElementById('idea-empty');
        const el = document.getElementById('idea-result');
        // Hide empty state, show loading
        if (emptyEl) emptyEl.style.display = 'none';
        el.innerHTML = '<div class="spinner"></div>';
        try {
            const resp = await fetch('/api/idea-check', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({idea})
            });
            const {analysis} = await resp.json();
            if (!analysis) {
                el.innerHTML = '';
                if (emptyEl) {
                    emptyEl.innerHTML = '<p>分析失败</p><p class="hint">请稍后重试</p>';
                    emptyEl.style.display = '';
                }
                return;
            }
            const colors = {high: '#22c55e', medium: '#eab308', low: '#ef4444'};
            el.innerHTML = `
                <div style="display:flex;gap:12px;margin-bottom:12px">
                    <span style="color:${colors[analysis.feasibility]}">可行性: ${analysis.feasibility}</span>
                    <span style="color:${colors[analysis.novelty]}">新颖性: ${analysis.novelty}</span>
                </div>
                <h3>相关工作</h3><p style="font-size:0.88rem">${analysis.related_work}</p>
                <h3>差异化建议</h3><p style="font-size:0.88rem">${analysis.differentiation}</p>
                <h3>风险</h3><p style="font-size:0.88rem">${analysis.risks}</p>`;
        } catch {
            el.innerHTML = '';
            if (emptyEl) {
                emptyEl.innerHTML = '<p>请求失败</p><p class="hint">请检查网络后重试</p>';
                emptyEl.style.display = '';
            }
        }
    });

    // Close dropdowns on outside click (no-op for sidebar)
    document.addEventListener('click', (e) => {
        // Sidebar doesn't need outside click handling
    });

    // Data management
    const toggleMgmt = document.getElementById('toggle-data-mgmt');
    const mgmtBody = document.getElementById('data-mgmt-body');
    toggleMgmt?.addEventListener('click', () => {
        const open = mgmtBody.style.display !== 'none';
        mgmtBody.style.display = open ? 'none' : 'block';
        toggleMgmt.classList.toggle('expanded', !open);
    });

    document.getElementById('btn-purge-skip')?.addEventListener('click', async () => {
        if (!confirm('确定删除所有 AI 标记为 skip 的论文？此操作不可恢复。')) return;
        try {
            const { purgePapers } = await import('./api.js');
            const result = await purgePapers({ skip_rated: true });
            showToast(`已删除 ${result.purged} 篇 skip 论文`);
            loadPapers();
        } catch { showToast('删除失败'); }
    });

    document.getElementById('btn-purge-before')?.addEventListener('click', async () => {
        const dateInput = document.getElementById('purge-date-input');
        const dateStr = dateInput?.value;
        if (!dateStr) { showToast('请选择日期'); return; }
        if (!confirm(`确定删除 ${dateStr} 之前的所有论文？此操作不可恢复。`)) return;
        try {
            const { deletePapersBefore } = await import('./api.js');
            const result = await deletePapersBefore(dateStr);
            showToast(`已删除 ${result.deleted_count} 篇论文`);
            loadPapers();
        } catch { showToast('删除失败'); }
    });

    // Ignored papers viewer
    const ignoredModal = document.getElementById('ignored-modal');
    document.getElementById('btn-view-ignored')?.addEventListener('click', () => {
        ignoredModal.classList.add('active');
        loadIgnored();
    });
    document.getElementById('close-ignored-modal')?.addEventListener('click', () => {
        ignoredModal.classList.remove('active');
    });
    document.getElementById('ignored-reason-filter')?.addEventListener('change', () => loadIgnored());

    async function loadIgnored(page = 1) {
        const reason = document.getElementById('ignored-reason-filter')?.value || '';
        const resp = await fetch(`/api/ignored?page=${page}&per_page=50${reason ? '&reason=' + encodeURIComponent(reason) : ''}`);
        const data = await resp.json();
        const statsEl = document.getElementById('ignored-stats');
        statsEl.innerHTML = data.stats.map(s => `${s.reason}: ${s.count}`).join(' &nbsp;|&nbsp; ');
        const listEl = document.getElementById('ignored-list');
        listEl.innerHTML = data.ignored.map(p =>
            `<div style="padding:4px 0;border-bottom:1px solid var(--border);font-size:0.82rem">
                <span style="color:var(--text-3)">${p.paper_id}</span>
                <span style="float:right;color:var(--accent-primary);font-size:0.75rem">${p.reason}</span>
                <span style="display:block;color:var(--text-3);font-size:0.72rem">${p.ignored_at || ''}</span>
            </div>`
        ).join('') || '<p style="color:var(--text-3);text-align:center;padding:20px">无被过滤论文</p>';
        const pagEl = document.getElementById('ignored-pagination');
        const pages = Math.ceil(data.total / data.per_page);
        pagEl.textContent = pages > 1 ? `第 ${page}/${pages} 页 (共 ${data.total} 篇)` : `共 ${data.total} 篇`;
    }

    // Feedback: like/dislike buttons (delegation from card and modal)
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-feedback-action]');
        if (!btn) return;
        e.stopPropagation();
        const paperId = btn.dataset.feedbackId;
        const action = btn.dataset.feedbackAction;
        const current = feedbackData[paperId] || {};
        const newRating = current.rating === action ? '' : action;

        fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                paper_id: paperId,
                rating: newRating,
                relevance: current.relevance || null,
                novelty: current.novelty || null,
            }),
        }).then(r => r.ok ? fetchFeedback() : Promise.resolve()).then(() => renderPapers());
    });

    // Feedback: sliders (delegation from card and modal)
    document.addEventListener('change', (e) => {
        if (!e.target.classList.contains('feedback-slider')) return;
        const paperId = e.target.dataset.sliderId;
        const type = e.target.dataset.sliderType;
        const value = parseInt(e.target.value);
        const current = feedbackData[paperId] || {};

        fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                paper_id: paperId,
                rating: current.rating || '',
                relevance: type === 'relevance' ? value : (current.relevance || null),
                novelty: type === 'novelty' ? value : (current.novelty || null),
            }),
        }).then(r => r.ok ? fetchFeedback() : null).then(() => {
            const valSpan = e.target.nextElementSibling;
            if (valSpan) valSpan.textContent = value;
        });
    });
});
