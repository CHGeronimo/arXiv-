// js/jobcenter.js — ⚡ 任务中心：全局常驻进度面板 + 顶部细进度条

const JOB_LABELS = {
    arxiv: '📡 arXiv 抓取', crossref: '📡 期刊抓取', dblp: '📡 DBLP 抓取',
    s2: '📡 S2 搜索', author: '📡 作者订阅', citations: '📡 引文追踪',
    trend_auto: '📡 趋势刷新', enhance_rerun: '♻️ 重跑旧流程', clustering: '🕸️ 图谱聚类',
    trend: '📡 趋势报告', digest: '📰 今日简报', selftest: '🧪 系统自检',
    enhance: '🤖 补 AI 增强', knowledge: '🗂 知识卡片提取', fulltext: '📄 补全文分析',
};
const STATUS_META = {
    running: { icon: '<span class="spinner" style="width:10px;height:10px;border-width:2px"></span>', cls: 'var(--accent-primary)' },
    done: { icon: '✓', cls: 'var(--success)' },
    error: { icon: '✗', cls: 'var(--danger)' },
    skipped: { icon: '⊘', cls: 'var(--text-3)' },
};

let _panelOpen = false;

function _esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function _renderJobs(all) {
    const panel = document.getElementById('panel-jobs');
    const badge = document.getElementById('jobs-badge');
    if (!panel) return;
    const jobs = Object.entries(all).filter(([k]) => !k.startsWith('__'));
    const running = jobs.filter(([, v]) => v?.status === 'running');
    if (badge) {
        badge.style.display = running.length ? '' : 'none';
        badge.textContent = running.length;
    }
    const ddEl = document.getElementById('dd-jobs');
    if (ddEl) ddEl.classList.toggle('has-running', running.length > 0);
    if (!jobs.length) {
        panel.innerHTML = '<div style="padding:10px;font-size:0.8rem;color:var(--text-3)">暂无任务记录</div>';
    } else {
        panel.innerHTML = jobs.map(([key, v]) => {
            const meta = STATUS_META[v?.status] || { icon: '·', cls: 'var(--text-3)' };
            const label = JOB_LABELS[key] || key;
            const pr = v?.progress;
            let bar = '';
            if (v?.status === 'running' && pr?.total) {
                const pct = Math.min(100, Math.round(pr.done / pr.total * 100));
                bar = `<div style="margin:5px 0 2px;height:4px;background:var(--surface-2);border-radius:2px;overflow:hidden">
                            <div style="height:100%;width:${pct}%;background:var(--accent-primary);border-radius:2px;transition:width .8s ease"></div>
                       </div>
                       <div style="display:flex;justify-content:space-between;font-size:0.68rem;color:var(--text-3);font-family:var(--font-mono)">
                            <span>${pr.done}/${pr.total}（${pct}%）</span>
                            <span>${pr.eta_min != null ? `ETA ${pr.eta_min}分` : ''}${pr.speed_pmin ? ` · ${pr.speed_pmin}篇/分` : ''}</span>
                       </div>`;
            } else if (v?.status === 'running') {
                bar = `<div style="margin:5px 0 2px;font-size:0.68rem;color:var(--text-3)">进行中…${pr?.done ?? ''}</div>`;
            }
            const msg = v?.message ? `<div style="font-size:0.7rem;color:var(--text-3);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${_esc(v.message)}">${_esc(v.message)}</div>` : '';
            return `<div style="padding:8px 12px;border-bottom:1px dashed var(--border)">
                        <div style="display:flex;align-items:center;gap:6px;font-size:0.82rem;color:var(--text-0)">
                            ${meta.icon}<span style="flex:1">${_esc(label)}</span>
                            <span style="color:${meta.cls};font-size:0.7rem">${v?.updated ? v.updated.slice(11, 19) : ''}</span>
                        </div>
                        ${bar}${msg}
                    </div>`;
        }).join('');
    }
    // 顶部细进度条：取最近更新的有 total 的 running 任务
    const top = document.getElementById('top-progress');
    if (top) {
        const withTotal = running.filter(([, v]) => v?.progress?.total)
            .sort((a, b) => (b[1].updated || '').localeCompare(a[1].updated || ''));
        const target = withTotal[0];
        if (target) {
            const pr = target[1].progress;
            top.style.display = '';
            top.style.width = Math.min(100, Math.round(pr.done / pr.total * 100)) + '%';
        } else {
            top.style.display = running.length ? '' : 'none';
            top.style.width = running.length ? '35%' : '0';
            if (running.length) top.style.opacity = '0.5'; else top.style.opacity = '1';
        }
    }
}

export function initJobCenter() {
    const dd = document.getElementById('dd-jobs');
    const panel = document.getElementById('panel-jobs');
    if (!dd || !panel) return;
    dd.querySelector('[data-dropdown]')?.addEventListener('click', (e) => {
        e.stopPropagation();
        const wasOpen = dd.classList.contains('open');
        document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
        if (!wasOpen) dd.classList.add('open');
        _panelOpen = !wasOpen;
    });
    panel.addEventListener('click', (e) => e.stopPropagation());

    const poll = async () => {
        try {
            const r = await fetch('/api/jobs');
            if (r.ok) _renderJobs(await r.json());
        } catch { /* 瞬时失败继续 */ }
        setTimeout(poll, _panelOpen ? 3000 : 8000);
    };
    poll();
}
