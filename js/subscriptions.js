// js/subscriptions.js
let subscriptions = { arxiv: { categories: [] }, crossref: { journals: [] }, conferences: [], search: { keywords: [], useProfile: true }, authors: [] };

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

// CONFERENCES now derived from CCF_CONFERENCES (ccf-data.js)
// Keep backward compat: build from CCF data if available
const CONFERENCES = (typeof CCF_CONFERENCES !== 'undefined') ? CCF_CONFERENCES.map(c => ({
    venue: c.venue,
    label: c.venue,
    group: c.domain,
    tier: c.tier,
})) : [
    { venue: "CVPR", label: "CVPR", group: "人工智能" },
    { venue: "NeurIPS", label: "NeurIPS", group: "人工智能" },
    { venue: "ACL", label: "ACL", group: "人工智能" },
    { venue: "ICML", label: "ICML", group: "人工智能" },
    { venue: "ICLR", label: "ICLR", group: "人工智能" },
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
    if (!subscriptions.authors) subscriptions.authors = [];
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
    renderCCFJournals();
    renderQuickJournals();
    renderCrossrefJournals();
    renderConferenceChips();
    renderSubscribedAuthors();
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
    // Count CCF-tiered subscribed conferences
    let ccfA = 0, ccfB = 0, ccfC = 0;
    const subVenues = new Set((subscriptions.conferences || []).map(c => c.venue));
    for (const venue of subVenues) {
        const info = CCF_CONF_MAP[venue];
        if (info) {
            if (info.tier === 'A') ccfA++;
            else if (info.tier === 'B') ccfB++;
            else ccfC++;
        }
    }
    const authors = (subscriptions.authors || []).length;
    el.innerHTML = `订阅统计：${cats} arXiv 分类 · ${journals} 期刊 · ${confs} 会议 (CCF A:${ccfA} B:${ccfB} C:${ccfC}) · ${authors} 作者 · ${keywords || (useProfile ? '使用研究方向' : 0)} 搜索关键词`;
}

function renderCCFJournals() {
    const container = document.getElementById('ccf-journal-section');
    if (!container || typeof CCF_JOURNALS === 'undefined') return;

    const subscribedIssns = new Set((subscriptions.crossref?.journals || []).map(j => j.issn));

    // Group by domain
    const byDomain = {};
    for (const j of CCF_JOURNALS) {
        if (!byDomain[j.domain]) byDomain[j.domain] = [];
        byDomain[j.domain].push(j);
    }

    let html = '';

    // Tier filter
    html += '<div style="margin-bottom:8px;display:flex;gap:4px;flex-wrap:wrap">';
    ['all', 'A', 'B', 'C'].forEach(t => {
        const active = t === 'all' ? ' active' : '';
        html += `<button class="ccf-tier-filter${active}" data-ccf-jfilter="${t}">${t === 'all' ? '全部' : 'CCF-' + t}</button>`;
    });
    html += '</div>';

    for (const [domain, journals] of Object.entries(byDomain)) {
        html += `<div style="font-size:0.75rem;color:var(--text-secondary);margin:8px 0 4px;font-weight:500">${domain}</div>`;
        html += '<div style="display:flex;flex-wrap:wrap;gap:4px">';
        for (const j of journals) {
            const tierTag = `<span class="ccf-badge ${ccfTierClass(j.tier)}">${j.tier}</span>`;
            html += `<span class="sub-chip" data-ccf-jtier="${j.tier}" title="${j.name} (${j.publisher})" style="display:inline-flex;align-items:center;gap:3px;cursor:default">${tierTag}<span style="font-size:0.8rem">${j.abbr}</span></span>`;
        }
        html += '</div>';
    }

    container.innerHTML = html;

    // Tier filter
    container.querySelectorAll('.ccf-tier-filter').forEach(btn => {
        btn.addEventListener('click', () => {
            container.querySelectorAll('.ccf-tier-filter').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const tier = btn.dataset.ccfJfilter;
            container.querySelectorAll('[data-ccf-jtier]').forEach(el => {
                el.style.display = (tier === 'all' || el.dataset.ccfJtier === tier) ? '' : 'none';
            });
        });
    });
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

    // Add tier filter bar
    let html = '<div style="margin-bottom:8px;display:flex;gap:4px;flex-wrap:wrap">';
    ['all', 'A', 'B', 'C'].forEach(t => {
        const active = t === 'all' ? ' active' : '';
        html += `<button class="ccf-tier-filter${active}" data-ccf-filter="${t}">${t === 'all' ? '全部' : 'CCF-' + t}</button>`;
    });
    html += '</div>';

    let currentGroup = '';
    const sorted = [...CONFERENCES].sort((a, b) => {
        const dComp = a.group.localeCompare(b.group);
        if (dComp !== 0) return dComp;
        const tOrder = { A: 0, B: 1, C: 2 };
        return (tOrder[a.tier] ?? 3) - (tOrder[b.tier] ?? 3);
    });

    for (const conf of sorted) {
        if (conf.group !== currentGroup) {
            if (currentGroup) html += '<div style="height:8px"></div>';
            html += `<div style="font-size:0.75rem;color:var(--text-secondary);margin:6px 0 4px;font-weight:500">${conf.group}</div>`;
            currentGroup = conf.group;
        }
        const sel = selected.has(conf.venue);
        const tierCls = conf.tier ? ` ${ccfTierClass(conf.tier)}` : '';
        const tierTag = conf.tier ? `<span class="ccf-badge ${ccfTierClass(conf.tier)}">${conf.tier}</span>` : '';
        html += `<label class="sub-chip${tierCls}${sel ? ' selected' : ''}" style="display:inline-flex;align-items:center;gap:3px;margin:2px 4px" data-ccf-tier="${conf.tier || ''}">
            <input type="checkbox" ${sel ? 'checked' : ''} data-conf-venue="${conf.venue}">
            ${tierTag}${conf.label}
        </label>`;
    }
    container.innerHTML = html;

    // Tier filter buttons
    container.querySelectorAll('.ccf-tier-filter').forEach(btn => {
        btn.addEventListener('click', () => {
            container.querySelectorAll('.ccf-tier-filter').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const tier = btn.dataset.ccfFilter;
            container.querySelectorAll('.sub-chip[data-ccf-tier]').forEach(chip => {
                chip.style.display = (tier === 'all' || chip.dataset.ccfTier === tier) ? '' : 'none';
            });
        });
    });

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
    ['arxiv', 'journals', 'conferences', 'authors', 'search', 'notify'].forEach(t => {
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

// ── Author Subscriptions ────────────────────────────────────────

async function searchAuthors(query) {
    const resultsEl = document.getElementById('author-search-results');
    if (!resultsEl || !query || query.length < 2) {
        if (resultsEl) resultsEl.innerHTML = '';
        return;
    }
    resultsEl.innerHTML = '<div style="color:var(--text-secondary);font-size:0.85rem">搜索中...</div>';
    try {
        const resp = await fetch(`/api/author/search?query=${encodeURIComponent(query)}`);
        if (!resp.ok) throw new Error('search failed');
        const data = await resp.json();
        const authors = data.authors || [];
        if (!authors.length) {
            resultsEl.innerHTML = '<div style="color:var(--text-secondary);font-size:0.85rem">未找到匹配作者</div>';
            return;
        }
        const subscribedIds = new Set((subscriptions.authors || []).map(a => a.authorId));
        resultsEl.innerHTML = authors.map(a => {
            const subbed = subscribedIds.has(a.authorId);
            const aff = a.affiliations?.[0] || '';
            const orcid = a.externalIds?.ORCID || a._orcid || '';
            const orcidTag = orcid ? `<span style="font-size:0.7rem;background:rgba(168,85,247,0.15);color:#a855f7;padding:1px 5px;border-radius:3px;margin-left:4px">ORCID</span>` : '';
            return `<div class="author-search-item" style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-bottom:1px solid var(--border-color)">
                <div style="min-width:0;flex:1">
                    <div style="font-size:0.88rem;font-weight:500">${a.name}${orcidTag}</div>
                    <div style="font-size:0.75rem;color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${aff}${aff ? ' · ' : ''}${a.paperCount || 0} 篇论文${orcid ? ' · ' + orcid : ''}</div>
                </div>
                <button class="follow-btn ${subbed ? 'followed' : ''}" data-author-id="${a.authorId}" data-author-name="${a.name}" data-author-aff="${aff}" data-author-papers="${a.paperCount || 0}" style="font-size:0.78rem;padding:4px 10px;flex-shrink:0">${subbed ? '✓ 已关注' : '+ 关注'}</button>
            </div>`;
        }).join('');
    } catch (e) {
        resultsEl.innerHTML = '<div style="color:var(--text-secondary);font-size:0.85rem">搜索失败，请重试</div>';
    }
}

function followAuthor(authorId, name, affiliation, paperCount) {
    if (!subscriptions.authors) subscriptions.authors = [];
    if (subscriptions.authors.some(a => a.authorId === authorId)) return;
    subscriptions.authors.push({
        name,
        authorId,
        affiliation: affiliation || '',
        paperCount: paperCount || 0,
        lastUpdated: null,
    });
    saveSubscriptions(subscriptions, 'author');
    renderSubscribedAuthors();
}

function unfollowAuthor(authorId) {
    subscriptions.authors = (subscriptions.authors || []).filter(a => a.authorId !== authorId);
    saveSubscriptions(subscriptions, 'author');
    renderSubscribedAuthors();
}

function renderSubscribedAuthors() {
    const container = document.getElementById('subscribed-authors-list');
    if (!container) return;
    const authors = subscriptions.authors || [];
    if (!authors.length) {
        container.innerHTML = '<p class="empty-hint">暂无关注作者。在上方搜索添加。</p>';
        return;
    }
    container.innerHTML = authors.map(a => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border-color)">
            <div>
                <div style="font-size:0.88rem;font-weight:500">${a.name}</div>
                <div style="font-size:0.75rem;color:var(--text-secondary)">${a.affiliation || ''}${a.affiliation ? ' · ' : ''}${a.paperCount || 0} 篇</div>
            </div>
            <button class="unfollow-btn" data-unfollow-author="${a.authorId}">取消关注</button>
        </div>
    `).join('');
}

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('author-search-input');
    const searchBtn = document.getElementById('btn-search-author');
    let searchTimer = null;

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => searchAuthors(searchInput.value.trim()), 400);
        });
    }
    if (searchBtn) {
        searchBtn.addEventListener('click', () => searchAuthors(searchInput?.value?.trim()));
    }

    // Event delegation for author search results and subscribed list
    const resultsEl = document.getElementById('author-search-results');
    if (resultsEl) {
        resultsEl.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-author-id]');
            if (!btn) return;
            followAuthor(btn.dataset.authorId, btn.dataset.authorName, btn.dataset.authorAff, parseInt(btn.dataset.authorPapers));
            // Re-render search results to update button state
            searchAuthors(searchInput?.value?.trim());
        });
    }

    const subList = document.getElementById('subscribed-authors-list');
    if (subList) {
        subList.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-unfollow-author]');
            if (btn) unfollowAuthor(btn.dataset.unfollowAuthor);
        });
    }

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
