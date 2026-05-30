// js/subscriptions.js
let subscriptions = { arxiv: { categories: [] }, crossref: { journals: [] }, conferences: [], search: { keywords: [], useProfile: true } };

const ARXIV_CATEGORIES = [
    { cat: "cs.AI", label: "AI", group: "CS" },
    { cat: "cs.CL", label: "CL", group: "CS" },
    { cat: "cs.CV", label: "CV", group: "CS" },
    { cat: "cs.LG", label: "LG", group: "CS" },
    { cat: "cs.RO", label: "RO", group: "CS" },
    { cat: "cs.NE", label: "NE", group: "CS" },
    { cat: "cs.MM", label: "MM", group: "CS" },
    { cat: "cs.CR", label: "CR", group: "CS" },
    { cat: "cs.IR", label: "IR", group: "CS" },
    { cat: "cs.HC", label: "HC", group: "CS" },
    { cat: "cs.DB", label: "DB", group: "CS" },
    { cat: "cs.DC", label: "DC", group: "CS" },
    { cat: "cs.SE", label: "SE", group: "CS" },
    { cat: "cs.SY", label: "SY", group: "CS" },
    { cat: "eess.SP", label: "SP", group: "EESS" },
    { cat: "eess.IV", label: "IV", group: "EESS" },
    { cat: "eess.AS", label: "AS", group: "EESS" },
    { cat: "math.OC", label: "OC", group: "Math" },
    { cat: "math.ST", label: "ST", group: "Math" },
    { cat: "stat.ML", label: "ML", group: "Stat" },
    { cat: "stat.AP", label: "AP", group: "Stat" },
    { cat: "physics.optics", label: "Optics", group: "Physics" },
    { cat: "physics.app-ph", label: "Applied", group: "Physics" },
    { cat: "physics.med-ph", label: "Medical", group: "Physics" },
    { cat: "q-bio.NC", label: "Neurons", group: "Bio" },
    { cat: "q-bio.QM", label: "Quant", group: "Bio" },
];

const QUICK_JOURNALS = [
    { issn: "0028-0836", name: "Nature" },
    { issn: "0036-8075", name: "Science" },
    { issn: "0036-8075", name: "Science" },
    { issn: "0027-8424", name: "PNAS" },
    { issn: "0092-8674", name: "Cell" },
    { issn: "0140-6736", name: "The Lancet" },
    { issn: "1546-170X", name: "Nature Medicine" },
    { issn: "1545-7885", name: "PLoS Biology" },
    { issn: "2051-5960", name: "Nature Communications" },
    { issn: "1755-4330", name: "Nature Methods" },
    { issn: "1545-9993", name: "Nature Biotechnology" },
    { issn: "2051-5874", name: "Nature Machine Intelligence" },
];

const CONFERENCES = [
    // CV
    { venue: "CVPR", label: "CVPR", group: "计算机视觉" },
    { venue: "ICCV", label: "ICCV", group: "计算机视觉" },
    { venue: "ECCV", label: "ECCV", group: "计算机视觉" },
    { venue: "WACV", label: "WACV", group: "计算机视觉" },
    // ML
    { venue: "NeurIPS", label: "NeurIPS", group: "机器学习" },
    { venue: "ICML", label: "ICML", group: "机器学习" },
    { venue: "ICLR", label: "ICLR", group: "机器学习" },
    { venue: "AAAI", label: "AAAI", group: "机器学习" },
    { venue: "IJCAI", label: "IJCAI", group: "机器学习" },
    // NLP
    { venue: "ACL", label: "ACL", group: "自然语言处理" },
    { venue: "EMNLP", label: "EMNLP", group: "自然语言处理" },
    { venue: "NAACL", label: "NAACL", group: "自然语言处理" },
    { venue: "COLING", label: "COLING", group: "自然语言处理" },
    // Data Mining / IR
    { venue: "KDD", label: "KDD", group: "数据挖掘/信息检索" },
    { venue: "SIGIR", label: "SIGIR", group: "数据挖掘/信息检索" },
    { venue: "WWW", label: "TheWebConf", group: "数据挖掘/信息检索" },
    { venue: "WSDM", label: "WSDM", group: "数据挖掘/信息检索" },
    // Speech
    { venue: "INTERSPEECH", label: "INTERSPEECH", group: "语音" },
    { venue: "ICASSP", label: "ICASSP", group: "语音" },
    // Medical
    { venue: "MICCAI", label: "MICCAI", group: "医学影像" },
];

async function loadSubscriptions() {
    try {
        const resp = await fetch('/api/subscriptions');
        if (resp.ok) {
            subscriptions = await resp.json();
        }
    } catch (e) {
        console.error('Failed to load subscriptions:', e);
        const saved = localStorage.getItem('subscriptions');
        if (saved) subscriptions = JSON.parse(saved);
    }
    if (!subscriptions.conferences) subscriptions.conferences = [];
    if (!subscriptions.search) subscriptions.search = { keywords: [], useProfile: true };
    renderSubscriptionUI();
    return subscriptions;
}

async function saveSubscriptions(newSubs, changedSource) {
    subscriptions = newSubs;
    localStorage.setItem('subscriptions', JSON.stringify(newSubs));
    try {
        const resp = await fetch('/api/subscriptions', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newSubs),
        });
        if (resp.ok && changedSource) {
            if (typeof showToast === 'function') showToast('订阅已保存，正在爬取...');
            fetch(`/api/trigger/${changedSource}`, { method: 'POST' }).catch(() => {});
        } else if (resp.ok) {
            if (typeof showToast === 'function') showToast('订阅已保存');
        }
    } catch (e) {
        console.error('Failed to save subscriptions to server:', e);
        if (typeof showToast === 'function') showToast('保存失败，已缓存到本地');
    }
}

function renderSubscriptionUI() {
    renderArxivCategories();
    renderQuickJournals();
    renderCrossrefJournals();
    renderConferenceChips();
    renderSubStats();
}

function renderSubStats() {
    const el = document.getElementById('sub-stats');
    if (!el) return;
    const cats = subscriptions.arxiv?.categories?.length || 0;
    const journals = subscriptions.crossref?.journals?.length || 0;
    const confs = (subscriptions.conferences || []).length;
    const keywords = subscriptions.search?.keywords?.length || 0;
    const useProfile = subscriptions.search?.useProfile !== false;
    el.innerHTML = `订阅统计：${cats} arXiv 分类 · ${journals} 期刊 · ${confs} 会议 · ${keywords || (useProfile ? '使用研究方向' : 0)} 搜索关键词`;
}

function renderQuickJournals() {
    const container = document.getElementById('quick-journal-chips');
    if (!container) return;
    const subscribed = new Set((subscriptions.crossref?.journals || []).map(j => j.issn));
    container.innerHTML = QUICK_JOURNALS.map(j => {
        const sub = subscribed.has(j.issn);
        return `<button class="sub-chip ${sub ? 'selected' : ''}" data-quick-issn="${j.issn}" data-quick-name="${j.name}" style="cursor:pointer">${sub ? '✓ ' : ''}${j.name}</button>`;
    }).join('');

    container.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-quick-issn]');
        if (!btn) return;
        const issn = btn.dataset.quickIssn;
        const name = btn.dataset.quickName;
        if (isJournalFollowed(issn)) {
            unfollowJournal(issn);
        } else {
            followJournal(issn, name);
        }
        renderQuickJournals();
    }, { once: true });
}

function renderArxivCategories() {
    const container = document.getElementById('arxiv-category-chips');
    if (!container) return;
    const selected = new Set(subscriptions.arxiv?.categories || []);
    let html = '';
    let currentGroup = '';
    for (const item of ARXIV_CATEGORIES) {
        if (item.group !== currentGroup) {
            if (currentGroup) html += '<div style="height:8px"></div>';
            html += `<div style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:4px">${item.group}</div>`;
            currentGroup = item.group;
        }
        const sel = selected.has(item.cat);
        html += `<label class="sub-chip ${sel ? 'selected' : ''}" style="display:inline-block;margin:2px 4px">
            <input type="checkbox" ${sel ? 'checked' : ''} data-arxiv-cat="${item.cat}">
            ${item.label}
        </label>`;
    }
    container.innerHTML = html;

    // Event delegation for arXiv checkboxes
    container.addEventListener('change', (e) => {
        const cb = e.target.closest('[data-arxiv-cat]');
        if (!cb) return;
        if (!subscriptions.arxiv) subscriptions.arxiv = { categories: [] };
        const cats = subscriptions.arxiv.categories || [];
        if (cb.checked) {
            if (!cats.includes(cb.dataset.arxivCat)) cats.push(cb.dataset.arxivCat);
        } else {
            const idx = cats.indexOf(cb.dataset.arxivCat);
            if (idx >= 0) cats.splice(idx, 1);
        }
        subscriptions.arxiv.categories = cats;
        saveSubscriptions(subscriptions, 'arxiv');
        renderArxivCategories();
    }, { once: true }); // re-renders on each change so listener is fresh
}

function renderConferenceChips() {
    const container = document.getElementById('conference-chips');
    if (!container) return;
    const selected = new Set((subscriptions.conferences || []).map(c => c.venue));
    let html = '';
    let currentGroup = '';
    for (const conf of CONFERENCES) {
        if (conf.group !== currentGroup) {
            if (currentGroup) html += '<div style="height:8px"></div>';
            html += `<div style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:4px">${conf.group}</div>`;
            currentGroup = conf.group;
        }
        const sel = selected.has(conf.venue);
        html += `<label class="sub-chip ${sel ? 'selected' : ''}" style="display:inline-block;margin:2px 4px">
            <input type="checkbox" ${sel ? 'checked' : ''} data-conf-venue="${conf.venue}">
            ${conf.label}
        </label>`;
    }
    container.innerHTML = html;

    container.addEventListener('change', (e) => {
        const cb = e.target.closest('[data-conf-venue]');
        if (!cb) return;
        toggleConference(cb.dataset.confVenue, cb.checked);
    }, { once: true });
}

function toggleConference(venue, checked) {
    if (!subscriptions.conferences) subscriptions.conferences = [];
    if (checked) {
        if (!subscriptions.conferences.some(c => c.venue === venue)) {
            subscriptions.conferences.push({ venue, lastUpdated: null });
        }
    } else {
        subscriptions.conferences = subscriptions.conferences.filter(c => c.venue !== venue);
    }
    saveSubscriptions(subscriptions, 'dblp');
    renderConferenceChips();
}

function renderCrossrefJournals() {
    const container = document.getElementById('crossref-journals-list');
    if (!container) return;
    if (!subscriptions.crossref.journals.length) {
        container.innerHTML = '<p class="empty-hint">No journals subscribed yet. Search above to add.</p>';
        return;
    }
    container.innerHTML = subscriptions.crossref.journals.map(j => `
        <div class="journal-item">
            <span class="journal-name">${j.name}</span>
            <span class="journal-issn">${j.issn}</span>
            <button class="unfollow-btn" data-unfollow-issn="${j.issn}">Unfollow</button>
        </div>
    `).join('');

    container.addEventListener('click', (e) => {
        const btn = e.target.closest('[data-unfollow-issn]');
        if (btn) { unfollowJournal(btn.dataset.unfollowIssn); }
    }, { once: true });
}

function unfollowJournal(issn) {
    subscriptions.crossref.journals = subscriptions.crossref.journals.filter(
        j => j.issn !== issn
    );
    saveSubscriptions(subscriptions, 'crossref');
    renderCrossrefJournals();
}

function openSubscriptionModal() {
    document.getElementById('subscription-modal').classList.add('active');
    loadSubscriptions();
}

function closeSubscriptionModal() {
    document.getElementById('subscription-modal').classList.remove('active');
}

function switchSubTab(tab, el) {
    document.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    ['arxiv', 'journals', 'conferences', 'search', 'notify'].forEach(t => {
        const tabEl = document.getElementById(`sub-tab-${t}`);
        if (tabEl) tabEl.style.display = t === tab ? 'block' : 'none';
    });
}

function toggleCustomKeywords() {
    const useProfile = document.getElementById('use-profile-keywords').checked;
    document.getElementById('custom-keywords').style.display = useProfile ? 'none' : 'block';
}

async function saveSearchKeywords() {
    const useProfile = document.getElementById('use-profile-keywords').checked;
    if (useProfile) {
        subscriptions.search = { keywords: [], useProfile: true };
    } else {
        const text = document.getElementById('custom-keywords').value;
        const keywords = text.split('\n').map(k => k.trim()).filter(k => k);
        subscriptions.search = { keywords, useProfile: false };
    }
    await saveSubscriptions(subscriptions, 's2');
    fetch('/api/trigger/s2', { method: 'POST' }).catch(() => {});
}

// ── Import / Export ──────────────────────────────────────────────

function exportSubscriptions() {
    const blob = new Blob([JSON.stringify(subscriptions, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'arxivsci-subscriptions.json';
    a.click(); URL.revokeObjectURL(url);
    if (typeof showToast === 'function') showToast('配置已导出');
}

function importSubscriptions(file) {
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const data = JSON.parse(e.target.result);
            if (!data.arxiv && !data.crossref && !data.conferences) {
                if (typeof showToast === 'function') showToast('无效的配置文件');
                return;
            }
            subscriptions = data;
            await saveSubscriptions(subscriptions);
            renderSubscriptionUI();
            if (typeof showToast === 'function') showToast('配置已导入');
        } catch {
            if (typeof showToast === 'function') showToast('解析失败，请检查文件格式');
        }
    };
    reader.readAsText(file);
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn-export-subs')?.addEventListener('click', exportSubscriptions);
    document.getElementById('btn-import-subs')?.addEventListener('click', () => {
        document.getElementById('import-subs-file')?.click();
    });
    document.getElementById('import-subs-file')?.addEventListener('change', (e) => {
        if (e.target.files[0]) importSubscriptions(e.target.files[0]);
        e.target.value = '';
    });
    document.getElementById('btn-auto-recommend')?.addEventListener('click', autoRecommendSubs);
});

const _KEYWORD_MAP = {
    'vision': { cats: ['cs.CV'], confs: ['CVPR', 'ICCV', 'ECCV'] },
    'image': { cats: ['cs.CV', 'eess.IV'], confs: ['CVPR', 'MICCAI'] },
    'nlp': { cats: ['cs.CL'], confs: ['ACL', 'EMNLP', 'NAACL'] },
    'language': { cats: ['cs.CL'], confs: ['ACL', 'EMNLP'] },
    'speech': { cats: ['cs.CL', 'eess.AS'], confs: ['INTERSPEECH', 'ICASSP'] },
    'learning': { cats: ['cs.LG'], confs: ['NeurIPS', 'ICML', 'ICLR'] },
    'reinforcement': { cats: ['cs.LG', 'cs.AI'], confs: ['NeurIPS', 'ICML'] },
    'robot': { cats: ['cs.RO', 'cs.AI'], confs: ['ICRA'] },
    '3d': { cats: ['cs.CV', 'cs.GR'], confs: ['CVPR'] },
    'retrieval': { cats: ['cs.IR'], confs: ['SIGIR', 'WWW'] },
    'recommend': { cats: ['cs.IR'], confs: ['SIGIR', 'KDD'] },
    'security': { cats: ['cs.CR'], confs: [] },
    'medical': { cats: ['cs.CV', 'eess.IV'], confs: ['MICCAI'] },
    'data mining': { cats: ['cs.DB'], confs: ['KDD', 'WSDM'] },
    'optimization': { cats: ['math.OC', 'cs.LG'], confs: ['NeurIPS'] },
    'graph': { cats: ['cs.LG'], confs: ['KDD'] },
    'multimodal': { cats: ['cs.CV', 'cs.CL', 'cs.MM'], confs: ['CVPR', 'ACL'] },
    'generation': { cats: ['cs.CV', 'cs.CL', 'cs.LG'], confs: ['NeurIPS', 'ICLR'] },
};

async function autoRecommendSubs() {
    let keywords = [];
    try {
        const resp = await fetch('/api/profile');
        if (resp.ok) {
            const profile = await resp.json();
            keywords = profile.keywords || [];
        }
    } catch {}
    if (!keywords.length) {
        if (typeof showToast === 'function') showToast('请先设置研究方向关键词');
        return;
    }
    const recommendedCats = new Set(subscriptions.arxiv?.categories || []);
    const recommendedConfs = new Set((subscriptions.conferences || []).map(c => c.venue));
    for (const kw of keywords) {
        const kwLower = kw.toLowerCase();
        for (const [pattern, rec] of Object.entries(_KEYWORD_MAP)) {
            if (kwLower.includes(pattern)) {
                rec.cats.forEach(c => recommendedCats.add(c));
                rec.confs.forEach(c => recommendedConfs.add(c));
            }
        }
    }
    subscriptions.arxiv = subscriptions.arxiv || { categories: [] };
    subscriptions.arxiv.categories = [...recommendedCats];
    subscriptions.conferences = [...recommendedConfs].map(v => {
        const existing = (subscriptions.conferences || []).find(c => c.venue === v);
        return existing || { venue: v, lastUpdated: null };
    });
    await saveSubscriptions(subscriptions);
    renderSubscriptionUI();
    if (typeof showToast === 'function') showToast(`推荐完成：${recommendedCats.size} 分类, ${recommendedConfs.size} 会议`);
}
