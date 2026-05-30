// js/api.js — API fetch wrappers

import { showToast } from './state.js';

export async function fetchPapers() {
    const resp = await fetch('/api/papers?per_page=1000');
    if (!resp.ok) throw new Error('fetch failed');
    const data = await resp.json();
    return data.papers || [];
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
    const jobs = job === 'all' ? ['arxiv', 'crossref', 'dblp', 's2'] : [job];
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
