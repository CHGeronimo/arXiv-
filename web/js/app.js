// js/app.js — entry point

import {
    setAllPapers, setRefreshTimer, setSortOrder, setCurrentPage,
    refreshTimer, toggleBookmark, showToast, syncServerFlags, restoreUIState,
    filteredPapers, currentPage, setCurrentTheme, currentTheme, setSidebarOpen, sidebarOpen,
    setFeedbackData, feedbackData, activeFilters, setDateWithinDays, dateWithinDays,
} from './state.js';
import { fetchPapers, quickFollowAuthor, triggerCrawl, exportBibtex, deletePaper as apiDeletePaper } from './api.js';
import { escAttr } from './state.js';
import { buildFilterOptions, toggleFilter, clearAllFilters } from './filters.js';
import { renderPapers, changePage } from './render.js';
import { openPaperDetail, closePaperModal, navigateModal } from './modal.js';
import { loadGraph } from './graph.js';
import { loadTrendRadar } from './trend.js';import { initDigestPage } from './digest.js';
import { toggleCompare, openCompare, closeCompare, clearCompare } from './compare.js';

// Theme
const THEME_LABELS = { dark: '深色', light: '浅色', academic: '学术', warm: '暖色', auto: '自动' };
const THEME_ICONS = { dark: '🌙', light: '☀️', academic: '📖', warm: '🔥', auto: '🖥️' };

function _initTheme() {
    // 经 setCurrentTheme 走一遍：auto 档刷新后能正确解析为实际主题
    setCurrentTheme(currentTheme);
    const btn = document.getElementById('btn-theme');
    if (btn) btn.textContent = THEME_ICONS[currentTheme] || '🌙';
}
function cycleTheme() {
    const themes = ['dark', 'light', 'academic', 'warm', 'auto'];
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

function _renderSkeleton() {
    const wrap = document.getElementById('skeleton-wrap');
    if (!wrap) return;
    wrap.innerHTML = Array.from({ length: 8 }).map(() =>
        `<div class="skeleton-card"><div class="sk-line" style="width:60%"></div><div class="sk-line" style="width:90%"></div><div class="sk-line" style="width:80%"></div><div class="sk-line" style="width:40%"></div></div>`
    ).join('');
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
    restoreUIState();  // F5 恢复筛选/排序/搜索/页码（须在首次渲染前）
    _renderSkeleton();
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
    // ⚙️ 抓取设置弹窗
    const openSettingsModal = async () => {
        const modal = document.getElementById('settings-modal');
        const form = document.getElementById('settings-form');
        modal.classList.add('active');
        form.innerHTML = '<div class="spinner"></div>';
        try {
            const resp = await fetch('/api/settings');
            const { settings, meta, scheduled } = await resp.json();
            form.innerHTML = Object.entries(meta).map(([key, m]) => {
                const val = settings[key];
                if (m.type === 'bool') {
                    return `<label style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);font-size:0.85rem">
                        <span>${m.label}${m.restart ? ' <span style="color:var(--warning)">⟳</span>' : ''}</span>
                        <input type="checkbox" data-setting-key="${key}" ${val ? 'checked' : ''}></label>`;
                }
                return `<label style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);font-size:0.85rem">
                    <span>${m.label}${m.restart ? ' <span style="color:var(--warning)">⟳</span>' : ''}</span>
                    <input type="number" data-setting-key="${key}" value="${val}" min="${m.min}" max="${m.max}" style="width:72px;padding:4px 8px;border:1px solid var(--border);border-radius:4px;background:var(--surface-0);color:var(--text-0);text-align:center"></label>`;
            }).join('');
            _renderSchedule(scheduled);
            _loadLlmConfig();
            _loadLlmModels();
            _loadBind();
        } catch { form.innerHTML = '<p style="color:var(--text-3)">加载失败</p>'; }
    };
    const _renderLlmStatus = (cfg) => {
        const el = document.getElementById('llm-config-status');
        if (!el) return;
        el.textContent = cfg.key_configured ? `${cfg.model} · ${cfg.key_masked}` : `${cfg.model} · 未配置 Key`;
        el.style.color = cfg.key_configured ? 'var(--success)' : 'var(--warning)';
    };
    const _syncProviderForm = (cfg, selectedId) => {
        const sel = document.getElementById('llm-provider-select');
        const customRow = document.getElementById('llm-custom-row');
        const keyInput = document.getElementById('llm-key-input');
        const selId = selectedId || sel.value;
        const p = (cfg.providers || []).find(x => x.id === selId);
        customRow.style.display = selId === 'custom' ? 'flex' : 'none';
        if (selId === 'custom' && p) {
            document.getElementById('llm-custom-base').value = p.base_url || '';
            document.getElementById('llm-custom-model').value = p.model || '';
        }
        keyInput.placeholder = p && p.key_set ? '已保存 Key（可留空直接验证切换）' : '粘贴该供应商的 Key';
    };
    const _loadLlmConfig = async () => {
        try {
            const r = await fetch('/api/llm-config');
            const cfg = await r.json();
            const sel = document.getElementById('llm-provider-select');
            sel.innerHTML = (cfg.providers || []).map(p =>
                `<option value="${p.id}" ${p.id === cfg.provider ? 'selected' : ''}>${p.label}${p.key_set && p.id !== cfg.provider ? '（Key 已存）' : ''}</option>`
            ).join('');
            _renderLlmStatus(cfg);
            _syncProviderForm(cfg, cfg.provider);
        } catch { /* 状态行保持为空 */ }
    };

    // 🎛 按任务指定模型（留空 = 跟随默认）
    const _loadLlmModels = async () => {
        const box = document.getElementById('llm-models-form');
        if (!box) return;
        try {
            const r = await fetch('/api/llm-models');
            const cfg = await r.json();
            const input = (key, val, ph) =>
                `<input data-model-key="${key}" value="${val || ''}" placeholder="${ph || ''}" list="model-suggestions" class="model-input">`;
            box.innerHTML =
                `<datalist id="model-suggestions">${(cfg.suggestions || []).map(s => `<option value="${s}">`).join('')}</datalist>` +
                `<label class="model-row"><span>默认模型（全部任务兜底）</span>${input('default', cfg.default, '必填')}</label>` +
                (cfg.tasks || []).map(t =>
                    `<label class="model-row"><span>${t.label}</span>${input(t.id, t.model, '跟随默认')}</label>`).join('');
        } catch { box.innerHTML = '<p style="font-size:0.75rem;color:var(--text-3)">加载失败</p>'; }
    };

    // 🌐 监听地址（重启 daemon 生效）
    const _loadBind = async () => {
        try {
            const r = await fetch('/api/bind');
            const b = await r.json();
            document.getElementById('bind-host').value = b.host;
            document.getElementById('bind-port').value = b.port;
            const st = document.getElementById('bind-status');
            const actual = b.actual_port ? `${b.actual_host}:${b.actual_port}` : '未知';
            st.textContent = b.pending_restart ? `运行中 ${actual} ⟳ 待重启` : `运行中 ${actual}`;
            st.style.color = b.pending_restart ? 'var(--warning)' : 'var(--text-3)';
        } catch { /* 状态行保持为空 */ }
    };
    const _renderSchedule = (scheduled) => {
        const el = document.getElementById('settings-schedule');
        if (!el) return;
        const names = { arxiv: 'arXiv', crossref: '期刊', dblp: 'DBLP', s2: 'S2 搜索', author: '作者', citations: '引文追踪', trend_auto: '趋势刷新' };
        el.innerHTML = '<b style="color:var(--text-1)">下次自动运行</b><br>' +
            Object.entries(scheduled || {}).map(([k, v]) => `${names[k] || k}: <span style="font-family:var(--font-mono)">${v}</span>`).join('<br>');
    };
    document.getElementById('close-settings-modal')?.addEventListener('click', () => {
        document.getElementById('settings-modal').classList.remove('active');
    });
    document.getElementById('settings-modal')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) e.currentTarget.classList.remove('active');
    });
    document.getElementById('btn-save-settings')?.addEventListener('click', async () => {
        const payload = {};
        document.querySelectorAll('#settings-form [data-setting-key]').forEach(inp => {
            payload[inp.dataset.settingKey] = inp.type === 'checkbox' ? inp.checked : parseInt(inp.value);
        });
        try {
            const resp = await fetch('/api/settings', {
                method: 'PUT', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            if (!resp.ok) { showToast(data.error || '保存失败'); return; }
            _renderSchedule(data.scheduled);
            showToast('✓ 已保存并重排时间表');
        } catch { showToast('保存失败'); }
    });

    // 🔑 AI 供应商：下拉选择（GLM/DeepSeek/自定义）→ 验证→保存→即时生效
    document.getElementById('llm-provider-select')?.addEventListener('change', (e) => {
        _syncProviderForm(null, e.target.value);
    });
    document.getElementById('btn-llm-key-eye')?.addEventListener('click', () => {
        const input = document.getElementById('llm-key-input');
        input.type = input.type === 'password' ? 'text' : 'password';
    });
    document.getElementById('btn-llm-key-save')?.addEventListener('click', async () => {
        const sel = document.getElementById('llm-provider-select');
        const keyInput = document.getElementById('llm-key-input');
        const btn = document.getElementById('btn-llm-key-save');
        const payload = { provider: sel.value, key: keyInput.value.trim() };
        if (!payload.key && keyInput.placeholder.indexOf('已保存') === -1) {
            showToast('请先粘贴该供应商的 Key'); return;
        }
        if (sel.value === 'custom') {
            payload.base_url = document.getElementById('llm-custom-base').value.trim();
            payload.model = document.getElementById('llm-custom-model').value.trim();
            if (!payload.base_url.startsWith('http') || !payload.model) {
                showToast('自定义供应商需填写 Base URL 和模型名'); return;
            }
        }
        btn.disabled = true; btn.textContent = '验证中…';
        try {
            const resp = await fetch('/api/llm-config', {
                method: 'PUT', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            if (!resp.ok) { showToast(data.error || '验证失败，未保存'); return; }
            keyInput.value = '';
            await _loadLlmConfig();
            showToast(data.cleared_overrides && data.cleared_overrides.length
                ? `✓ 已切换（清除了 ${data.cleared_overrides.length} 个按任务模型覆盖）`
                : '✓ 已验证并即时生效');
        } catch { showToast('保存失败（网络错误）'); }
        finally { btn.disabled = false; btn.textContent = '验证并切换'; }
    });

    // 🎛 任务模型保存（留空 = 清除覆盖跟随默认，即时生效）
    document.getElementById('btn-llm-models-save')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-llm-models-save');
        const payload = {};
        document.querySelectorAll('#llm-models-form [data-model-key]').forEach(inp => {
            payload[inp.dataset.modelKey] = inp.value.trim();
        });
        btn.disabled = true;
        try {
            const resp = await fetch('/api/llm-models', {
                method: 'PUT', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            if (!resp.ok) { showToast(data.error || '保存失败'); return; }
            showToast('✓ 任务模型已保存（即时生效）');
        } catch { showToast('保存失败（网络错误）'); }
        finally { btn.disabled = false; }
    });

    // 🌐 监听地址保存（重启 daemon 后生效）
    document.getElementById('btn-bind-save')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-bind-save');
        const payload = {
            host: document.getElementById('bind-host').value.trim(),
            port: parseInt(document.getElementById('bind-port').value),
        };
        if (!payload.host || !payload.port) { showToast('请填写地址和端口'); return; }
        btn.disabled = true;
        try {
            const resp = await fetch('/api/bind', {
                method: 'PUT', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await resp.json();
            if (!resp.ok) { showToast(data.error || '保存失败'); return; }
            showToast(data.lan_warning
                ? '⚠ 已保存（0.0.0.0 局域网开放，注意安全），重启 daemon 后生效'
                : '✓ 已保存，重启 daemon 后生效');
            _loadBind();
        } catch { showToast('保存失败（网络错误）'); }
        finally { btn.disabled = false; }
    });

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
            if (item.dataset.crawl === 'settings') { openSettingsModal(); }
            else triggerCrawl(item.dataset.crawl, { loadPapers });
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

    // 预设与日期快捷（晨读/必读/收藏 + 今天/3/7/30天）
    const applyPreset = (name) => {
        for (const key of Object.keys(activeFilters)) activeFilters[key].clear();
        setDateWithinDays(0);
        const di = document.getElementById('sidebar-date-filter'); if (di) di.value = '';
        const si = document.getElementById('sidebar-search-input'); if (si) si.value = '';
        if (name === 'morning') {
            activeFilters.today.add('yes');
            activeFilters.type.add('must-read'); activeFilters.type.add('recommended');
            setSortOrder('relevance');
        } else if (name === 'mustread') {
            activeFilters.type.add('must-read');
            setSortOrder('relevance');
        } else if (name === 'starred') {
            activeFilters.bookmarked.add('yes');
        }
        setCurrentPage(1);
        buildFilterOptions(); renderPapers();
        showToast(`已应用预设：${{morning:'🌅 晨读', mustread:'🔭 全部必读', starred:'⭐ 收藏夹'}[name]}`);
    };
    document.querySelectorAll('.preset-btn').forEach(btn =>
        btn.addEventListener('click', () => applyPreset(btn.dataset.preset)));
    document.querySelectorAll('.within-btn').forEach(btn =>
        btn.addEventListener('click', () => {
            const d = parseInt(btn.dataset.within);
            setDateWithinDays(dateWithinDays === d ? 0 : d);  // 再点一次取消
            setCurrentPage(1);
            buildFilterOptions(); renderPapers();
        }));

    // Paper container delegation (chips 单个移除 + 原有交互)
    document.getElementById('paper-container').addEventListener('click', (e) => {
        const chip = e.target.closest('.active-chip');
        if (chip) {
            const g = chip.dataset.chipGroup, v = chip.dataset.chipValue;
            if (g === 'search') { const si = document.getElementById('sidebar-search-input'); if (si) si.value = ''; }
            else if (g === 'date') { const di = document.getElementById('sidebar-date-filter'); if (di) di.value = ''; }
            else if (g === 'within') setDateWithinDays(0);
            else if (v !== undefined && activeFilters[g]) activeFilters[g].delete(v);
            setCurrentPage(1);
            buildFilterOptions(); renderPapers();
            return;
        }
    });
    // 原主交互委托（分页/收藏/删除/作者/对比/卡片打开）
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
            if (fp[idx]) openPaperDetail(fp[idx], idx);
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
        // 弹窗打开时 J/K = 翻论文而非翻页
        const modalOpen = document.getElementById('paper-modal')?.classList.contains('active');
        if (modalOpen && (e.key === 'j' || e.key === 'k')) {
            navigateModal(e.key === 'k' ? 1 : -1);
            return;
        }
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
    // 空状态一键引导：提取知识卡片（完成后自动聚类）再刷新图谱
    document.getElementById('btn-graph-bootstrap')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-graph-bootstrap');
        btn.disabled = true; btn.textContent = '⏳ 提取中（数分钟，完成后自动聚类）...';
        try {
            await fetch('/api/trigger/knowledge-extract', { method: 'POST' });
            showToast('知识卡片提取已启动，完成后自动聚类，届时回来刷新图谱');
        } catch { showToast('启动失败'); }
        btn.disabled = false; btn.textContent = '⚡ 立即提取知识卡片并聚类';
    });

    // 版本可观测：daemon 代码 vs 磁盘代码，旧版本提示重启
    fetch('/api/stats').then(r => r.json()).then(s => {
        const el = document.getElementById('daemon-version');
        if (!el) return;
        if (s.code_stale) {
            el.innerHTML = `🔄 daemon=${s.daemon_version} < 磁盘=${s.disk_version}：<b style="color:var(--warning)">代码已更新，重启 daemon 生效</b>`;
        } else {
            el.textContent = `✓ 版本 ${s.daemon_version}（最新）`;
        }
    }).catch(() => {});

    // Trend radar 页面的生成/周期切换由 trend.js 自行绑定（generateTrend）

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
    const ignoredModal = document.getElementById('ignored-modal');    document.getElementById('btn-view-ignored')?.addEventListener('click', () => {
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
                <span style="color:var(--text-3)">${escAttr(p.paper_id)}</span>
                <span style="float:right;color:var(--accent-primary);font-size:0.75rem">${p.reason}</span>
                ${p.reason_detail ? `<span style="display:block;color:var(--text-2);font-size:0.76rem;margin-top:2px">${escAttr(p.reason_detail)}</span>` : ''}
                <span style="display:block;color:var(--text-3);font-size:0.72rem">${p.ignored_at || ''}</span>
            </div>`
        ).join('') || '<p style="color:var(--text-3);text-align:center;padding:20px">无被过滤论文</p>';
        const pagEl = document.getElementById('ignored-pagination');
        const pages = Math.ceil(data.total / data.per_page);
        pagEl.textContent = pages > 1 ? `第 ${page}/${pages} 页 (共 ${data.total} 篇)` : `共 ${data.total} 篇`;
    }

    // Feedback: like/dislike buttons (delegation from card and modal)
    // 字段级更新：只写 rating（取消用 clear_rating），不携带其他字段快照——
    // 携带快照会与并发的评语/滑杆请求互相覆盖（用户实测顺序不固定）
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-feedback-action]');
        if (!btn) return;
        e.stopPropagation();
        const paperId = btn.dataset.feedbackId;
        const action = btn.dataset.feedbackAction;
        const current = feedbackData[paperId] || {};
        const newRating = current.rating === action ? '' : action;
        const body = newRating
            ? { paper_id: paperId, rating: newRating }
            : { paper_id: paperId, clear_rating: true };

        fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        }).then(r => r.ok ? fetchFeedback() : Promise.resolve()).then(() => renderPapers());
    });

    // Feedback: note input (delegation; 'change' fires on blur with modified value)
    // 只写 note 字段；保存后重渲染卡片让列表同步显示新评语
    document.addEventListener('change', (e) => {
        const noteInput = e.target;
        if (!noteInput.classList || !noteInput.classList.contains('feedback-note')) return;
        const paperId = noteInput.dataset.noteId;
        fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                paper_id: paperId,
                note: noteInput.value.trim().slice(0, 200),
            }),
        }).then(r => r.ok ? fetchFeedback() : null).then(() => {
            if (feedbackData[paperId]) renderPapers();
            showToast('评语已保存，将影响后续评分');
        });
    });

    // Feedback: sliders (delegation from card and modal) — 只写自己的字段
    document.addEventListener('change', (e) => {
        if (!e.target.classList.contains('feedback-slider')) return;
        const paperId = e.target.dataset.sliderId;
        const type = e.target.dataset.sliderType;
        const value = parseInt(e.target.value);

        fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: paperId, [type]: value }),
        }).then(r => r.ok ? fetchFeedback() : null).then(() => {
            const valSpan = e.target.nextElementSibling;
            if (valSpan) valSpan.textContent = value;
        });
    });
});
