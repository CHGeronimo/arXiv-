// js/app.js — entry point

import {
    setAllPapers, setRefreshTimer, setSortOrder, setCurrentPage,
    refreshTimer, toggleBookmark, showToast, syncServerFlags,
    filteredPapers, currentPage, setCurrentTheme, currentTheme, setSidebarOpen, sidebarOpen,
    setFeedbackData, feedbackData,
} from './state.js';
import { fetchPapers, quickFollowAuthor, triggerCrawl, exportBibtex, deletePaper as apiDeletePaper } from './api.js';
import { buildFilterOptions, toggleFilter, clearAllFilters } from './filters.js';
import { renderPapers, changePage } from './render.js';
import { openPaperDetail, closePaperModal } from './modal.js';
import { loadGraph } from './graph.js';
import { loadTrendRadar } from './trend.js';
import { initDigestPage } from './digest.js';
import { toggleCompare, openCompare, closeCompare, clearCompare } from './compare.js';

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
// Expose for non-module scripts (subscriptions.js etc.) — toasts were silently lost before
window.showToast = showToast;

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
            // 先查轻量计数，库变了才拉全量列表（列表接口 ~MB 级）
            const statResp = await fetch('/api/stats');
            if (!statResp.ok) return;
            const { total_papers } = await statResp.json();
            const { allPapers } = await import('./state.js');
            if (total_papers !== allPapers.length) {
                const papers = await fetchPapers();
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
    syncServerFlags();  // 合并服务端收藏/已读到本地状态
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

    document.getElementById('btn-profile').addEventListener('click', () => {
        const searchTab = document.querySelector('[data-tab="search"]');
        if (searchTab) window.switchSubTab('search', searchTab);
        window.openSubscriptionModal();
    });
    document.getElementById('btn-theme').addEventListener('click', cycleTheme);
    document.getElementById('btn-subs').addEventListener('click', () => window.openSubscriptionModal());

    // Crawl trigger
    // Dropdown toggle（🔄 手动爬取菜单；侧边栏重构时曾被误删，2026-09-05 恢复）
    document.querySelectorAll('[data-dropdown]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const dd = btn.closest('.dropdown');
            const wasOpen = dd.classList.contains('open');
            document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
            if (!wasOpen) dd.classList.add('open');
        });
    });
    document.getElementById('panel-crawl').addEventListener('click', (e) => {
        const item = e.target.closest('[data-crawl]');
        if (item) {
            triggerCrawl(item.dataset.crawl, { loadPapers });
            item.closest('.dropdown')?.classList.remove('open');
        }
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

    // Profile 编辑入口在订阅面板"研究方向"tab（旧 profile-modal 已移除）

    // Subscription modal (functions from subscriptions.js — global scope)
    document.getElementById('close-subs-modal').addEventListener('click', () => window.closeSubscriptionModal());
    document.getElementById('subscription-modal').addEventListener('click', (e) => { if (e.target === e.currentTarget) window.closeSubscriptionModal(); });
    document.getElementById('sub-tabs-container').addEventListener('click', (e) => {
        const tab = e.target.closest('[data-tab]');
        if (tab) window.switchSubTab(tab.dataset.tab, tab);
    });
    document.getElementById('journal-search-input')?.addEventListener('input', (e) => window.handleJournalSearch?.());

    // Paper container delegation
    document.getElementById('paper-container').addEventListener('click', async (e) => {
        const pageBtn = e.target.closest('.page-btn[data-goto]');
        if (pageBtn) { e.stopPropagation(); setCurrentPage(parseInt(pageBtn.dataset.goto)); renderPapers(); window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
        const bmBtn = e.target.closest('.bookmark-btn');
        if (bmBtn) { e.stopPropagation(); toggleBookmark(bmBtn.dataset.bmId); renderPapers(); return; }
        const delBtn = e.target.closest('.card-vote-btn.delete');
        if (delBtn) {
            e.stopPropagation();
            const paperId = delBtn.dataset.deleteId;
            if (paperId && confirm('确认删除此论文？')) {
                fetch(`/api/paper/${encodeURIComponent(paperId)}`, { method: 'DELETE' }).then(r => {
                    if (r.ok) { loadPapers(); } else { alert('删除失败'); }
                });
            }
            return;
        }
        const authorLink = e.target.closest('.author-link');
        if (authorLink) {
            e.stopPropagation();
            const name = authorLink.dataset.authorName;
            if (name && confirm(`关注作者 "${name}" 的最新论文？`)) quickFollowAuthor(name);
            return;
        }
        const cmpBtn = e.target.closest('.compare-btn');
        if (cmpBtn) {
            e.stopPropagation();
            const cmpId = cmpBtn.dataset.compareId;
            const { filteredPapers: fpLive } = await import('./state.js');
            const target = fpLive.find(p => p.id === cmpId) || { id: cmpId, title: '' };
            toggleCompare(target);
            return;
        }
        const card = e.target.closest('.paper-card[data-idx]');
        if (card && !e.target.closest('[data-feedback-action], .card-feedback-detail, .bookmark-btn, .card-vote-btn.delete, .author-link')) {
            const idx = parseInt(card.dataset.idx);
            // Live import to get current filteredPapers
            const { filteredPapers: fp } = await import('./state.js');
            if (fp[idx]) openPaperDetail(fp[idx]);
        }
    });

    // Paper container delegation (page jump Enter key)
    document.getElementById('paper-container').addEventListener('keydown', (e) => {
        if (e.target.id === 'page-jump' && e.key === 'Enter') {
            const p = parseInt(e.target.value);
            if (p && p > 0) { setCurrentPage(p); renderPapers(); window.scrollTo({ top: 0, behavior: 'smooth' }); }
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', async (e) => {
        const active = document.activeElement;
        const typing = active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA');
        if (e.key === 'Escape') {
            // Close all modals and dropdowns uniformly
            document.querySelectorAll('.modal.active, .subscription-modal.active').forEach(m => {
                m.classList.remove('active');
            });
            document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
            document.body.style.overflow = '';
            return;
        }
        if (typing) return;
        if (e.key === 'j') changePage(1);
        else if (e.key === 'k') changePage(-1);
        else if (e.key === 'f') {
            const { filteredPapers: fp, currentPage: cp, PAGE_SIZE: ps, toggleBookmark: tb } = await import('./state.js');
            const first = fp[(cp - 1) * ps] || fp[0];  // 当前页第一篇，而非全列表第 N 篇
            if (first) { tb(first.id); renderPapers(); }
        }
        else if (e.key === '/') { e.preventDefault(); document.getElementById('sidebar-search-input')?.focus(); }
        else if (e.key === '?') { showToast('j/k 翻页 | f 收藏首篇 | / 搜索 | ? 帮助', 3000); }
    });

    // L1/L2/L3 页面导航（hash 路由：#/graph #/trend #/idea 可刷新、可收藏、可后退）
    const PAGE_LOADERS = {
        graph: { id: 'graph-page', load: () => loadGraph() },
        trend: { id: 'trend-page', load: () => loadTrendRadar() },
        idea: { id: 'idea-page', load: null },
        digest: { id: 'digest-page', load: () => initDigestPage() },
    };
    function showPage(pageId) {
        document.getElementById('paper-container').style.display = 'none';
        document.querySelectorAll('.page-section').forEach(el => el.style.display = 'none');
        const page = document.getElementById(pageId);
        if (page) page.style.display = 'block';
    }
    function hidePages() {
        document.querySelectorAll('.page-section').forEach(el => el.style.display = 'none');
        document.getElementById('paper-container').style.display = '';
    }
    function applyHash() {
        const key = location.hash.replace(/^#\/?/, '');
        const page = PAGE_LOADERS[key];
        if (page) {
            showPage(page.id);
            page.load?.();
        } else {
            hidePages();
        }
    }
    window.addEventListener('hashchange', applyHash);
    document.getElementById('btn-graph')?.addEventListener('click', () => { location.hash = '#/graph'; });
    document.getElementById('btn-trend')?.addEventListener('click', () => { location.hash = '#/trend'; });
    document.getElementById('btn-idea')?.addEventListener('click', () => { location.hash = '#/idea'; });
    document.getElementById('btn-digest')?.addEventListener('click', () => { location.hash = '#/digest'; });
    document.querySelectorAll('.btn-back-papers').forEach(btn => {
        btn.addEventListener('click', () => { location.hash = '#/'; });
    });
    document.querySelector('.header-left h1')?.addEventListener('click', () => { location.hash = '#/'; });
    applyHash();  // 刷新/直接打开 #/graph 时恢复对应页面

    // Knowledge graph
    document.getElementById('btn-refresh-graph')?.addEventListener('click', loadGraph);

    // Trend radar
    document.getElementById('btn-generate-trend')?.addEventListener('click', async () => {
        await fetch('/api/trigger/trend', { method: 'POST' });
        showToast('趋势报告生成中，完成后自动刷新...');
        let retries = 0;
        const pollTrend = setInterval(async () => {
            retries++;
            try {
                const resp = await fetch('/api/trend-radar');
                if (!resp.ok) return;
                const { report } = await resp.json();
                if (report || retries > 12) {
                    clearInterval(pollTrend);
                    loadTrendRadar();
                }
            } catch { clearInterval(pollTrend); }
        }, 10000);
    });

    // Idea check
    document.getElementById('btn-check-idea')?.addEventListener('click', async () => {
        const idea = document.getElementById('idea-input')?.value?.trim();
        if (!idea) return;
        const emptyEl = document.getElementById('idea-empty');
        const el = document.getElementById('idea-result');
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
            const gaugeColors = {high: 'var(--success)', medium: 'var(--warning)', low: 'var(--danger)'};
            const gaugeBg = {high: 'rgba(52,211,153,0.15)', medium: 'rgba(251,191,36,0.15)', low: 'rgba(248,113,113,0.15)'};
            const feasColor = gaugeColors[analysis.feasibility] || 'var(--text-3)';
            const novelColor = gaugeColors[analysis.novelty] || 'var(--text-3)';
            const feasBg = gaugeBg[analysis.feasibility] || 'var(--surface-2)';
            const novelBg = gaugeBg[analysis.novelty] || 'var(--surface-2)';
            const feasLabel = {high: '高', medium: '中', low: '低'}[analysis.feasibility] || analysis.feasibility;
            const novelLabel = {high: '高', medium: '中', low: '低'}[analysis.novelty] || analysis.novelty;
            el.innerHTML = `
                <div class="idea-gauges">
                    <div class="idea-gauge">
                        <div class="idea-gauge-ring" style="background:${feasBg};color:${feasColor};border:2px solid ${feasColor}">${feasLabel}</div>
                        <span class="idea-gauge-label">可行性</span>
                    </div>
                    <div class="idea-gauge">
                        <div class="idea-gauge-ring" style="background:${novelBg};color:${novelColor};border:2px solid ${novelColor}">${novelLabel}</div>
                        <span class="idea-gauge-label">新颖性</span>
                    </div>
                </div>
                <div class="idea-section">
                    <div class="idea-section-title">相关工作</div>
                    <div class="idea-section-body">${analysis.related_work || ''}</div>
                </div>
                <div class="idea-section">
                    <div class="idea-section-title">差异化建议</div>
                    <div class="idea-section-body">${analysis.differentiation || ''}</div>
                </div>
                <div class="idea-section">
                    <div class="idea-section-title">风险</div>
                    <div class="idea-section-body">${analysis.risks || ''}</div>
                </div>`;
        } catch {
            el.innerHTML = '';
            if (emptyEl) {
                emptyEl.innerHTML = '<p>请求失败</p><p class="hint">请检查网络后重试</p>';
                emptyEl.style.display = '';
            }
        }
    });

    // Compare modal + floating bar
    document.getElementById('close-compare-modal')?.addEventListener('click', closeCompare);
    document.getElementById('compare-modal')?.addEventListener('click', (e) => { if (e.target === e.currentTarget) closeCompare(); });
    document.getElementById('btn-compare-go')?.addEventListener('click', openCompare);
    document.getElementById('btn-compare-clear')?.addEventListener('click', clearCompare);

    // BibTeX batch export: current filtered list → .bib download
    document.getElementById('btn-export-bibtex')?.addEventListener('click', async () => {
        const { filteredPapers: fp } = await import('./state.js');
        if (!fp.length) { showToast('当前筛选无论文'); return; }
        const ids = fp.map(p => p.id);
        try {
            const resp = await fetch('/api/export/bibtex', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids }),
            });
            if (!resp.ok) throw new Error();
            const text = await resp.text();
            const blob = new Blob([text], { type: 'application/x-bibtex' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `arxivsci-${new Date().toISOString().slice(0, 10)}-${ids.length}papers.bib`;
            a.click();
            URL.revokeObjectURL(a.href);
            showToast(`已导出 ${ids.length} 篇 BibTeX`);
        } catch { showToast('导出失败'); }
    });

    // Close dropdowns on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
        }
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
                ${p.reason_detail ? `<span style="display:block;color:var(--text-2);font-size:0.76rem;margin-top:2px">${p.reason_detail}</span>` : ''}
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

    // Feedback: note input (delegation from card and modal; 'change' fires on blur with modified value)
    document.addEventListener('change', (e) => {
        const noteInput = e.target;
        if (!noteInput.classList || !noteInput.classList.contains('feedback-note')) return;
        const paperId = noteInput.dataset.noteId;
        const current = feedbackData[paperId] || {};
        fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                paper_id: paperId,
                rating: current.rating || '',
                relevance: current.relevance || null,
                novelty: current.novelty || null,
                note: noteInput.value.trim().slice(0, 200),
            }),
        }).then(r => r.ok ? fetchFeedback() : null).then(() => showToast('评语已保存，将影响后续评分'));
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
