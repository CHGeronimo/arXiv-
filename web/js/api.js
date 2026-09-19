// js/api.js — API fetch wrappers

import { showToast } from './state.js';

export async function fetchPapers() {
    const resp = await fetch('/api/papers?per_page=10000&light=1');
    if (!resp.ok) throw new Error('fetch failed');
    const data = await resp.json();
    return data.papers || [];
}

export async function fetchFullPaper(paperId) {
    try {
        const resp = await fetch(`/api/paper/${encodeURIComponent(paperId)}`);
        if (!resp.ok) return null;
        return await resp.json();
    } catch {
        return null;
    }
}

export async function quickFollowAuthor(name) {
    try {
        const resp = await fetch(`/api/author/search?query=${encodeURIComponent(name)}`);
        if (!resp.ok) throw new Error('search failed');
        const data = await resp.json();
        const authors = data.authors || [];
        if (!authors.length) { showToast('未找到该作者'); return; }
        const best = authors[0];
        const subsResp = await fetch('/api/subscriptions');
        const subs = subsResp.ok ? await subsResp.json() : {};
        if (!subs.authors) subs.authors = [];
        if (subs.authors.some(a => a.authorId === best.authorId)) {
            showToast(`已关注 ${best.name}`);
            return;
        }
        subs.authors.push({
            name: best.name,
            authorId: best.authorId,
            affiliation: best.affiliations?.[0] || '',
            paperCount: best.paperCount || 0,
            lastUpdated: null,
        });
        const putResp = await fetch('/api/subscriptions', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(subs),
        });
        if (putResp.ok) {
            showToast(`已关注 ${best.name}，正在爬取论文...`);
            fetch('/api/trigger/author', { method: 'POST' }).catch(() => {});
        }
    } catch {
        showToast('关注失败，请重试');
    }
}

export async function triggerCrawl(job, { loadPapers }) {
    if (job === 'enhance') {
        try {
            const resp = await fetch('/api/trigger/enhance', { method: 'POST' });
            showToast(resp.ok ? '补 AI 增强已启动' : '启动失败');
        } catch { showToast('启动失败'); }
        setTimeout(loadPapers, 30000);
        return;
    }
    if (job === 'knowledge-extract') {
        try {
            const resp = await fetch('/api/trigger/knowledge-extract', { method: 'POST' });
            showToast(resp.ok ? '知识卡片提取已启动，完成后自动聚类' : '启动失败');
        } catch { showToast('启动失败'); }
        return;
    }
    if (job === 'digest') {
        try {
            const resp = await fetch('/api/trigger/digest', { method: 'POST' });
            showToast(resp.ok ? '今日简报生成中，稍后到 📰 查看' : '启动失败');
        } catch { showToast('启动失败'); }
        return;
    }
    if (job === 'clustering') {
        try {
            const resp = await fetch('/api/trigger/clustering', { method: 'POST' });
            if (!resp.ok) { showToast('启动失败'); return; }
            showToast('聚类已启动（2000 篇约 2-4 分钟，进度见日志）…');
            const t0 = Date.now();
            const timer = setInterval(async () => {
                try {
                    const st = await (await fetch('/api/jobs')).json();
                    const s = st.clustering;
                    if (!s || s.status === 'running') {
                        if (s?.message) showToast(`聚类进度：${s.message}`);
                        if (Date.now() - t0 > 600000) { clearInterval(timer); showToast('聚类超时，稍后到 🕸️ 刷新查看'); }
                        return;
                    }
                    clearInterval(timer);
                    if (s.status === 'done') showToast(`✓ 聚类完成：${s.message}，到 🕸️ 刷新图谱`);
                    else showToast(`聚类失败：${s.message || s.status}`);
                } catch { /* 轮询瞬时失败继续 */ }
            }, 5000);
        } catch { showToast('启动失败'); }
        return;
    }
    if (job === 'fulltext') {
        try {
            const resp = await fetch('/api/trigger/fulltext-analyze', { method: 'POST' });
            showToast(resp.ok ? '全文分析已启动（补 must-read/recommended 论文）' : '启动失败');
        } catch { showToast('启动失败'); }
        return;
    }
    if (job === 'enhance-rerun') {
        try {
            const resp = await fetch('/api/trigger/enhance-rerun', { method: 'POST' });
            if (!resp.ok) { showToast('启动失败'); return; }
            showToast('♻️ 重跑旧流程结果启动（逐篇重新评分+知识卡片，可中断，再次触发只补剩余）…');
            const t0 = Date.now();
            const timer = setInterval(async () => {
                try {
                    const st = await (await fetch('/api/jobs')).json();
                    const s = st.enhance_rerun;
                    if (!s || s.status === 'running') {
                        if (Date.now() - t0 > 3600000) { clearInterval(timer); showToast('重跑仍在进行，进度见日志/状态'); }
                        return;
                    }
                    clearInterval(timer);
                    showToast(s.status === 'done' ? `✓ ${s.message}` : `重跑失败：${s.message || s.status}`);
                } catch { /* 轮询瞬时失败继续 */ }
            }, 10000);
        } catch { showToast('启动失败'); }
        return;
    }
    if (job === 'selftest') {
        try {
            const resp = await fetch('/api/trigger/selftest', { method: 'POST' });
            if (!resp.ok) { showToast('启动失败'); return; }
            showToast('🧪 自检运行中（30 项：网络源 + LLM 任务 + API 层 + 数据就绪，约 1-3 分钟）…');
            const t0 = Date.now();
            const timer = setInterval(async () => {
                try {
                    const st = await (await fetch('/api/jobs')).json();
                    const s = st.selftest;
                    if (!s || s.status === 'running') {
                        if (Date.now() - t0 > 90000) { clearInterval(timer); showToast('自检超时，稍后重试'); }
                        return;
                    }
                    clearInterval(timer);
                    const r = await (await fetch('/api/selftest')).json();
                    if (typeof window.showSelftestReport === 'function') window.showSelftestReport(r);
                    else showToast(`自检完成: ${s.message || ''}`);
                } catch { /* 轮询瞬时失败继续等 */ }
            }, 2000);
        } catch { showToast('启动失败'); }
        return;
    }
    const jobs = job === 'all' ? ['arxiv', 'crossref', 'dblp', 's2', 'citations'] : [job];
    for (const j of jobs) {
        const el = document.getElementById(`crawl-${j}`);
        if (el) el.textContent = '...';
        try {
            const resp = await fetch(`/api/trigger/${j}`, { method: 'POST' });
            if (el) el.textContent = resp.ok ? '⏳' : '✗';
        } catch {
            if (el) el.textContent = '✗';
        }
    }
    const pollInterval = setInterval(async () => {
        try {
            const resp = await fetch('/api/jobs');
            if (!resp.ok) return;
            const status = await resp.json();
            let allDone = true;
            for (const j of jobs) {
                const s = status[j];
                const el = document.getElementById(`crawl-${j}`);
                if (!s || s.status === 'running') { allDone = false; if (el) el.textContent = '⏳'; }
                else if (s.status === 'done') { if (el) el.textContent = `✓ ${s.message || ''}`; }
                else if (s.status === 'error') { if (el) el.textContent = '✗'; }
                else { if (el) el.textContent = '—'; }
            }
            if (allDone) {
                clearInterval(pollInterval);
                loadPapers();
                setTimeout(() => {
                    jobs.forEach(j => { const el = document.getElementById(`crawl-${j}`); if (el) el.textContent = '—'; });
                }, 10000);
            }
        } catch { clearInterval(pollInterval); }
    }, 3000);
}

export async function saveFeedback(paperId, rating) {
    await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_id: paperId, rating }),
    });
}

export async function exportBibtex(paperId) {
    const resp = await fetch('/api/export/bibtex', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: [paperId] }),
    });
    if (!resp.ok) throw new Error('export failed');
    return resp.text();
}

export async function fetchKnowledgeCard(paperId) {
    const resp = await fetch(`/api/paper/${encodeURIComponent(paperId)}/card`);
    if (!resp.ok) return null;
    const data = await resp.json();
    return data.card;
}

export async function fetchFulltextAnalysis(paperId) {
    try {
        const resp = await fetch(`/api/paper/${paperId}/fulltext`);
        if (resp.ok) {
            const data = await resp.json();
            return data.analysis || null;
        }
    } catch (e) {
        console.error('Failed to fetch fulltext analysis:', e);
    }
    return null;
}

export async function deletePaper(paperId) {
    const resp = await fetch(`/api/paper/${encodeURIComponent(paperId)}`, { method: 'DELETE' });
    if (!resp.ok) throw new Error('delete failed');
    return resp.json();
}

export async function deletePapersBefore(dateStr) {
    const resp = await fetch(`/api/papers/before/${encodeURIComponent(dateStr)}`, { method: 'DELETE' });
    if (!resp.ok) throw new Error('delete failed');
    return resp.json();
}

export async function purgePapers(options) {
    const resp = await fetch('/api/papers/purge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(options),
    });
    if (!resp.ok) throw new Error('purge failed');
    return resp.json();
}
