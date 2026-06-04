// js/subscriptions.js
let subscriptions = { arxiv: { categories: [] }, crossref: { journals: [] }, conferences: [], search: { keywords: [], useProfile: true }, authors: [] };

const ARXIV_CATEGORIES = [
    // Computer Science
    { cat: "cs.AI", label: "Artificial Intelligence", group: "Computer Science" },
    { cat: "cs.AR", label: "Hardware Architecture", group: "Computer Science" },
    { cat: "cs.CC", label: "Computational Complexity", group: "Computer Science" },
    { cat: "cs.CE", label: "Computational Engineering", group: "Computer Science" },
    { cat: "cs.CG", label: "Computational Geometry", group: "Computer Science" },
    { cat: "cs.CL", label: "Computation and Language", group: "Computer Science" },
    { cat: "cs.CR", label: "Cryptography and Security", group: "Computer Science" },
    { cat: "cs.CV", label: "Computer Vision", group: "Computer Science" },
    { cat: "cs.CY", label: "Computers and Society", group: "Computer Science" },
    { cat: "cs.DB", label: "Databases", group: "Computer Science" },
    { cat: "cs.DC", label: "Distributed Computing", group: "Computer Science" },
    { cat: "cs.DL", label: "Digital Libraries", group: "Computer Science" },
    { cat: "cs.DM", label: "Discrete Mathematics", group: "Computer Science" },
    { cat: "cs.DS", label: "Data Structures and Algorithms", group: "Computer Science" },
    { cat: "cs.ET", label: "Emerging Technologies", group: "Computer Science" },
    { cat: "cs.FL", label: "Formal Languages", group: "Computer Science" },
    { cat: "cs.GL", label: "General Literature", group: "Computer Science" },
    { cat: "cs.GR", label: "Graphics", group: "Computer Science" },
    { cat: "cs.GT", label: "Computer Science and Game Theory", group: "Computer Science" },
    { cat: "cs.HC", label: "Human-Computer Interaction", group: "Computer Science" },
    { cat: "cs.IR", label: "Information Retrieval", group: "Computer Science" },
    { cat: "cs.IT", label: "Information Theory", group: "Computer Science" },
    { cat: "cs.LG", label: "Machine Learning", group: "Computer Science" },
    { cat: "cs.LO", label: "Logic in Computer Science", group: "Computer Science" },
    { cat: "cs.MA", label: "Multiagent Systems", group: "Computer Science" },
    { cat: "cs.MM", label: "Multimedia", group: "Computer Science" },
    { cat: "cs.MS", label: "Mathematical Software", group: "Computer Science" },
    { cat: "cs.NA", label: "Numerical Analysis", group: "Computer Science" },
    { cat: "cs.NE", label: "Neural and Evolutionary Computing", group: "Computer Science" },
    { cat: "cs.NI", label: "Networking and Internet Architecture", group: "Computer Science" },
    { cat: "cs.OH", label: "Other Computer Science", group: "Computer Science" },
    { cat: "cs.OS", label: "Operating Systems", group: "Computer Science" },
    { cat: "cs.PF", label: "Performance", group: "Computer Science" },
    { cat: "cs.PL", label: "Programming Languages", group: "Computer Science" },
    { cat: "cs.RO", label: "Robotics", group: "Computer Science" },
    { cat: "cs.SC", label: "Symbolic Computation", group: "Computer Science" },
    { cat: "cs.SD", label: "Sound", group: "Computer Science" },
    { cat: "cs.SE", label: "Software Engineering", group: "Computer Science" },
    { cat: "cs.SI", label: "Social and Information Networks", group: "Computer Science" },
    { cat: "cs.SY", label: "Systems and Control", group: "Computer Science" },
    // Physics - Astrophysics
    { cat: "astro-ph.CO", label: "Cosmology and Nongalactic Astrophysics", group: "Physics" },
    { cat: "astro-ph.EP", label: "Earth and Planetary Astrophysics", group: "Physics" },
    { cat: "astro-ph.GA", label: "Astrophysics of Galaxies", group: "Physics" },
    { cat: "astro-ph.HE", label: "High Energy Astrophysical Phenomena", group: "Physics" },
    { cat: "astro-ph.IM", label: "Instrumentation and Methods for Astrophysics", group: "Physics" },
    { cat: "astro-ph.SR", label: "Solar and Stellar Astrophysics", group: "Physics" },
    // Physics - Condensed Matter
    { cat: "cond-mat.dis-nn", label: "Disordered Systems and Neural Networks", group: "Physics" },
    { cat: "cond-mat.mes-hall", label: "Mesoscale and Nanoscale Physics", group: "Physics" },
    { cat: "cond-mat.mtrl-sci", label: "Materials Science", group: "Physics" },
    { cat: "cond-mat.other", label: "Other Condensed Matter", group: "Physics" },
    { cat: "cond-mat.quant-gas", label: "Quantum Gases", group: "Physics" },
    { cat: "cond-mat.soft", label: "Soft Condensed Matter", group: "Physics" },
    { cat: "cond-mat.stat-mech", label: "Statistical Mechanics", group: "Physics" },
    { cat: "cond-mat.str-el", label: "Strongly Correlated Electrons", group: "Physics" },
    { cat: "cond-mat.supr-con", label: "Superconductivity", group: "Physics" },
    // Physics - General Relativity and High Energy
    { cat: "gr-qc", label: "General Relativity and Quantum Cosmology", group: "Physics" },
    { cat: "hep-ex", label: "High Energy Physics - Experiment", group: "Physics" },
    { cat: "hep-lat", label: "High Energy Physics - Lattice", group: "Physics" },
    { cat: "hep-ph", label: "High Energy Physics - Phenomenology", group: "Physics" },
    { cat: "hep-th", label: "High Energy Physics - Theory", group: "Physics" },
    { cat: "math-ph", label: "Mathematical Physics", group: "Physics" },
    // Physics - Nonlinear Sciences
    { cat: "nlin.AO", label: "Adaptation and Self-Organizing Systems", group: "Physics" },
    { cat: "nlin.CD", label: "Cellular Automata and Lattice Gases", group: "Physics" },
    { cat: "nlin.CG", label: "Chaotic Dynamics", group: "Physics" },
    { cat: "nlin.PS", label: "Pattern Formation and Solitons", group: "Physics" },
    { cat: "nlin.SI", label: "Exactly Solvable and Integrable Systems", group: "Physics" },
    // Physics - Nuclear
    { cat: "nucl-ex", label: "Nuclear Experiment", group: "Physics" },
    { cat: "nucl-th", label: "Nuclear Theory", group: "Physics" },
    // Physics - General Physics
    { cat: "physics.acc-ph", label: "Accelerator Physics", group: "Physics" },
    { cat: "physics.ao-ph", label: "Atmospheric and Oceanic Physics", group: "Physics" },
    { cat: "physics.app-ph", label: "Applied Physics", group: "Physics" },
    { cat: "physics.atm-clus", label: "Atomic and Molecular Clusters", group: "Physics" },
    { cat: "physics.atom-ph", label: "Atomic Physics", group: "Physics" },
    { cat: "physics.bio-ph", label: "Biological Physics", group: "Physics" },
    { cat: "physics.chem-ph", label: "Chemical Physics", group: "Physics" },
    { cat: "physics.class-ph", label: "Classical Physics", group: "Physics" },
    { cat: "physics.comp-ph", label: "Computational Physics", group: "Physics" },
    { cat: "physics.data-an", label: "Data Analysis, Statistics and Probability", group: "Physics" },
    { cat: "physics.flu-dyn", label: "Fluid Dynamics", group: "Physics" },
    { cat: "physics.gen-ph", label: "General Physics", group: "Physics" },
    { cat: "physics.geo-ph", label: "Geophysics", group: "Physics" },
    { cat: "physics.hist-ph", label: "History and Philosophy of Physics", group: "Physics" },
    { cat: "physics.ins-det", label: "Instrumentation and Detectors", group: "Physics" },
    { cat: "physics.med-ph", label: "Medical Physics", group: "Physics" },
    { cat: "physics.optics", label: "Optics", group: "Physics" },
    { cat: "physics.soc-ph", label: "Physics and Society", group: "Physics" },
    { cat: "physics.ed-ph", label: "Physics Education", group: "Physics" },
    { cat: "physics.plasm-ph", label: "Plasma Physics", group: "Physics" },
    { cat: "physics.pop-ph", label: "Popular Physics", group: "Physics" },
    { cat: "physics.space-ph", label: "Space Physics", group: "Physics" },
    // Physics - Quantum
    { cat: "quant-ph", label: "Quantum Physics", group: "Physics" },
    // Mathematics
    { cat: "math.AG", label: "Algebraic Geometry", group: "Mathematics" },
    { cat: "math.AT", label: "Algebraic Topology", group: "Mathematics" },
    { cat: "math.AP", label: "Analysis of PDEs", group: "Mathematics" },
    { cat: "math.CT", label: "Category Theory", group: "Mathematics" },
    { cat: "math.CA", label: "Classical Analysis and ODEs", group: "Mathematics" },
    { cat: "math.CO", label: "Combinatorics", group: "Mathematics" },
    { cat: "math.AC", label: "Commutative Algebra", group: "Mathematics" },
    { cat: "math.CV", label: "Complex Variables", group: "Mathematics" },
    { cat: "math.DG", label: "Differential Geometry", group: "Mathematics" },
    { cat: "math.DS", label: "Dynamical Systems", group: "Mathematics" },
    { cat: "math.FA", label: "Functional Analysis", group: "Mathematics" },
    { cat: "math.GM", label: "General Mathematics", group: "Mathematics" },
    { cat: "math.GN", label: "General Topology", group: "Mathematics" },
    { cat: "math.GT", label: "Geometric Topology", group: "Mathematics" },
    { cat: "math.GR", label: "Group Theory", group: "Mathematics" },
    { cat: "math.HO", label: "History and Overview", group: "Mathematics" },
    { cat: "math.IT", label: "Information Theory", group: "Mathematics" },
    { cat: "math.KT", label: "K-Theory and Homology", group: "Mathematics" },
    { cat: "math.LO", label: "Logic", group: "Mathematics" },
    { cat: "math.MP", label: "Mathematical Physics", group: "Mathematics" },
    { cat: "math.MG", label: "Metric Geometry", group: "Mathematics" },
    { cat: "math.NT", label: "Number Theory", group: "Mathematics" },
    { cat: "math.NA", label: "Numerical Analysis", group: "Mathematics" },
    { cat: "math.OA", label: "Operator Algebras", group: "Mathematics" },
    { cat: "math.OC", label: "Optimization and Control", group: "Mathematics" },
    { cat: "math.PR", label: "Probability", group: "Mathematics" },
    { cat: "math.QA", label: "Quantum Algebra", group: "Mathematics" },
    { cat: "math.RT", label: "Representation Theory", group: "Mathematics" },
    { cat: "math.RA", label: "Rings and Algebras", group: "Mathematics" },
    { cat: "math.SP", label: "Spectral Theory", group: "Mathematics" },
    { cat: "math.ST", label: "Statistics Theory", group: "Mathematics" },
    { cat: "math.SG", label: "Symplectic Geometry", group: "Mathematics" },
    // Quantitative Biology
    { cat: "q-bio.BM", label: "Biomolecules", group: "Quantitative Biology" },
    { cat: "q-bio.CB", label: "Cell Behavior", group: "Quantitative Biology" },
    { cat: "q-bio.GN", label: "Genomics", group: "Quantitative Biology" },
    { cat: "q-bio.MN", label: "Molecular Networks", group: "Quantitative Biology" },
    { cat: "q-bio.NC", label: "Neurons and Cognition", group: "Quantitative Biology" },
    { cat: "q-bio.OT", label: "Other Quantitative Biology", group: "Quantitative Biology" },
    { cat: "q-bio.PE", label: "Populations and Evolution", group: "Quantitative Biology" },
    { cat: "q-bio.QM", label: "Quantitative Methods", group: "Quantitative Biology" },
    { cat: "q-bio.SC", label: "Subcellular Processes", group: "Quantitative Biology" },
    { cat: "q-bio.TO", label: "Tissues and Organs", group: "Quantitative Biology" },
    // Quantitative Finance
    { cat: "q-fin.CP", label: "Computational Finance", group: "Quantitative Finance" },
    { cat: "q-fin.EC", label: "Economics", group: "Quantitative Finance" },
    { cat: "q-fin.GN", label: "General Finance", group: "Quantitative Finance" },
    { cat: "q-fin.MF", label: "Mathematical Finance", group: "Quantitative Finance" },
    { cat: "q-fin.PM", label: "Portfolio Management", group: "Quantitative Finance" },
    { cat: "q-fin.PR", label: "Pricing of Securities", group: "Quantitative Finance" },
    { cat: "q-fin.RM", label: "Risk Management", group: "Quantitative Finance" },
    { cat: "q-fin.ST", label: "Statistical Finance", group: "Quantitative Finance" },
    { cat: "q-fin.TR", label: "Trading and Market Microstructure", group: "Quantitative Finance" },
    // Statistics
    { cat: "stat.AP", label: "Applications", group: "Statistics" },
    { cat: "stat.CO", label: "Computation", group: "Statistics" },
    { cat: "stat.ML", label: "Machine Learning", group: "Statistics" },
    { cat: "stat.ME", label: "Methodology", group: "Statistics" },
    { cat: "stat.OT", label: "Other Statistics", group: "Statistics" },
    { cat: "stat.TH", label: "Theory", group: "Statistics" },
    // Electrical Engineering
    { cat: "eess.AS", label: "Audio and Speech Processing", group: "Electrical Engineering" },
    { cat: "eess.IV", label: "Image and Video Processing", group: "Electrical Engineering" },
    { cat: "eess.SP", label: "Signal Processing", group: "Electrical Engineering" },
    { cat: "eess.SY", label: "Systems and Control", group: "Electrical Engineering" },
    // Economics
    { cat: "econ.EM", label: "Econometrics", group: "Economics" },
    { cat: "econ.GN", label: "General Economics", group: "Economics" },
    { cat: "econ.TH", label: "Theoretical Economics", group: "Economics" },
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

let _triggerTimers = {};

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
            if (typeof showToast === 'function') showToast('订阅已保存');
            // Debounce: 3s window for same source, only trigger crawl once
            if (_triggerTimers[changedSource]) clearTimeout(_triggerTimers[changedSource]);
            _triggerTimers[changedSource] = setTimeout(() => {
                delete _triggerTimers[changedSource];
                fetch(`/api/trigger/${changedSource}`, { method: 'POST' }).catch(() => {});
                if (typeof showToast === 'function') showToast('正在爬取...');
            }, 3000);
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
    loadProfileKeywords().then(() => renderKeywordChips());
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
        html += `<div style="font-size:0.75rem;color:var(--text-2);margin:8px 0 4px;font-weight:500">${domain}</div>`;
        html += '<div style="display:flex;flex-wrap:wrap;gap:4px">';
        for (const j of journals) {
            const sel = subscribedIssns.has(j.issn);
            const tierCls = j.tier ? ` badge--ccf` : '';
            const tierTag = `<span class="badge badge--ccf">${j.tier}</span>`;
            const hasIssn = j.issn && j.issn !== 'undefined';
            const noIssnStyle = hasIssn ? '' : 'opacity:0.45;cursor:not-allowed';
            html += `<label class="badge badge--secondary${tierCls}${sel ? ' selected' : ''}" data-ccf-jtier="${j.tier}" data-ccf-jissn="${j.issn || ''}" data-ccf-jname="${j.name}" title="${j.name} (${j.publisher})${hasIssn ? '' : ' — 缺少ISSN'}" style="display:inline-flex;align-items:center;gap:3px;cursor:${hasIssn ? 'pointer' : 'not-allowed'};${noIssnStyle}">
                <input type="checkbox" ${sel ? 'checked' : ''} ${hasIssn ? '' : 'disabled'} data-ccf-jissn="${j.issn || ''}" data-ccf-jname="${j.name}" style="display:none">
                ${tierTag}<span style="font-size:0.8rem">${j.abbr}</span>
            </label>`;
        }
        html += '</div>';
    }

    container.innerHTML = html;

    // Tier filter — rebind each render since buttons are recreated
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

    // Bind change handler once via delegation flag on container
    if (!container._ccfJournalBound) {
        container._ccfJournalBound = true;
        container.addEventListener('change', (e) => {
            const cb = e.target.closest('input[data-ccf-jissn]');
            if (!cb) return;
            const issn = cb.dataset.ccfJissn;
            const name = cb.dataset.ccfJname;
            if (!issn || issn === 'undefined') {
                cb.checked = false;
                if (typeof showToast === 'function') showToast(`"${name}" 缺少 ISSN，暂无法订阅`);
                return;
            }
            toggleCCFJournal(issn, name, cb.checked);
        });
    }
}

function toggleCCFJournal(issn, name, checked) {
    if (!subscriptions.crossref) subscriptions.crossref = { journals: [] };
    if (!subscriptions.crossref.journals) subscriptions.crossref.journals = [];
    if (checked) {
        if (!subscriptions.crossref.journals.some(j => j.issn === issn)) {
            subscriptions.crossref.journals.push({ issn, name, lastUpdated: null });
        }
    } else {
        subscriptions.crossref.journals = subscriptions.crossref.journals.filter(j => j.issn !== issn);
    }
    saveSubscriptions(subscriptions, 'crossref');
    renderCCFJournals();
    renderQuickJournals();
    renderCrossrefJournals();
    renderSubStats();
}

function renderQuickJournals() {
    const container = document.getElementById('quick-journal-chips');
    if (!container) return;
    const subscribed = new Set((subscriptions.crossref?.journals || []).map(j => j.issn));
    container.innerHTML = QUICK_JOURNALS.map(j => {
        const sub = subscribed.has(j.issn);
        return `<button class="badge badge--secondary ${sub ? 'selected' : ''}" data-quick-issn="${j.issn}" data-quick-name="${j.name}" style="cursor:pointer">${j.name}</button>`;
    }).join('');

    if (!container._quickJournalBound) {
        container._quickJournalBound = true;
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
        });
    }
}

function renderArxivCategories(filter = '') {
    const container = document.getElementById('arxiv-category-chips');
    if (!container) return;
    const selected = new Set(subscriptions.arxiv?.categories || []);
    const filterLower = filter.toLowerCase();

    // Search bar
    let html = '<div style="margin-bottom:8px"><input type="text" id="arxiv-cat-search" placeholder="搜索分类..." value="' + filter.replace(/"/g, '&quot;') + '" style="width:100%;padding:6px 8px;border:1px solid var(--border);border-radius:4px;background:var(--surface-0);color:var(--text-0);font-size:0.85rem;outline:none"></div>';

    // Group filter buttons
    const groups = [...new Set(ARXIV_CATEGORIES.map(c => c.group))];
    html += '<div style="margin-bottom:8px;display:flex;gap:4px;flex-wrap:wrap"><button class="ccf-tier-filter active" data-arxiv-group="all">全部</button>';
    for (const g of groups) {
        const count = ARXIV_CATEGORIES.filter(c => c.group === g).length;
        html += `<button class="ccf-tier-filter" data-arxiv-group="${g}">${g} (${count})</button>`;
    }
    html += '</div>';

    // Category chips
    let currentGroup = '';
    let shown = 0;
    for (const item of ARXIV_CATEGORIES) {
        if (filterLower && !item.cat.toLowerCase().includes(filterLower) && !item.label.toLowerCase().includes(filterLower) && !item.group.toLowerCase().includes(filterLower)) continue;
        if (item.group !== currentGroup) {
            if (currentGroup) html += '<div style="height:8px"></div>';
            html += `<div style="font-size:0.75rem;color:var(--text-2);margin-bottom:4px;font-weight:500">${item.group}</div>`;
            currentGroup = item.group;
        }
        const sel = selected.has(item.cat);
        html += `<label class="badge badge--secondary ${sel ? 'selected' : ''}" style="display:inline-flex;align-items:center;margin:2px 4px" title="${item.cat}">
            <input type="checkbox" ${sel ? 'checked' : ''} data-arxiv-cat="${item.cat}" style="display:none">
            ${item.label}
        </label>`;
        shown++;
    }
    if (!shown) html += '<div style="color:var(--text-2);font-size:0.85rem">无匹配分类</div>';
    container.innerHTML = html;

    // Search handler
    const searchInput = document.getElementById('arxiv-cat-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(window._arxivSearchTimer);
            window._arxivSearchTimer = setTimeout(() => renderArxivCategories(e.target.value), 200);
        });
        // Keep focus and cursor position
        if (filter) { searchInput.focus(); searchInput.setSelectionRange(filter.length, filter.length); }
    }

    // Group filter handler
    container.querySelectorAll('[data-arxiv-group]').forEach(btn => {
        btn.addEventListener('click', () => {
            container.querySelectorAll('[data-arxiv-group]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const group = btn.dataset.arxivGroup;
            container.querySelectorAll('[data-arxiv-cat]').forEach(chip => {
                if (group === 'all') { chip.closest('label').style.display = ''; return; }
                const item = ARXIV_CATEGORIES.find(c => c.cat === chip.dataset.arxivCat);
                chip.closest('label').style.display = item && item.group === group ? '' : 'none';
            });
        });
    });

    // Checkbox handler
    if (!container._arxivCatBound) {
        container._arxivCatBound = true;
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
            const currentFilter = document.getElementById('arxiv-cat-search')?.value || '';
            saveSubscriptions(subscriptions, 'arxiv');
            renderArxivCategories(currentFilter);
        });
    }
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
            html += `<div style="font-size:0.75rem;color:var(--text-2);margin:6px 0 4px;font-weight:500">${conf.group}</div>`;
            currentGroup = conf.group;
        }
        const sel = selected.has(conf.venue);
        const tierCls = conf.tier ? ` badge--ccf` : '';
        const tierTag = conf.tier ? `<span class="badge badge--ccf">${conf.tier}</span>` : '';
        html += `<label class="badge badge--secondary${tierCls}${sel ? ' selected' : ''}" style="display:inline-flex;align-items:center;gap:3px;margin:2px 4px" data-ccf-tier="${conf.tier || ''}">
            <input type="checkbox" ${sel ? 'checked' : ''} data-conf-venue="${conf.venue}" style="display:none">
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
            container.querySelectorAll('.badge.badge--secondary[data-ccf-tier]').forEach(chip => {
                chip.style.display = (tier === 'all' || chip.dataset.ccfTier === tier) ? '' : 'none';
            });
        });
    });

    if (!container._confBound) {
        container._confBound = true;
        container.addEventListener('change', (e) => {
            const cb = e.target.closest('[data-conf-venue]');
            if (!cb) return;
            toggleConference(cb.dataset.confVenue, cb.checked);
        });
    }
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
    const countEl = document.getElementById('journal-count');
    const journals = subscriptions.crossref?.journals || [];
    if (countEl) countEl.textContent = journals.length ? `${journals.length} 本` : '';
    if (!journals.length) {
        container.innerHTML = '<p class="empty-hint">暂无已订阅期刊。在上方添加。</p>';
        return;
    }
    container.innerHTML = journals.map(j => `
        <div class="journal-item">
            <span class="journal-name">${j.name}</span>
            <span class="journal-issn">${j.issn}</span>
            <button class="unfollow-btn" data-unfollow-issn="${j.issn}">取消订阅</button>
        </div>
    `).join('');

    // Use delegation flag to avoid stacking listeners
    if (!container._unfollowBound) {
        container._unfollowBound = true;
        container.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-unfollow-issn]');
            if (!btn) return;
            unfollowJournal(btn.dataset.unfollowIssn);
        });
    }
}

function unfollowJournal(issn) {
    subscriptions.crossref.journals = subscriptions.crossref.journals.filter(
        j => j.issn !== issn
    );
    saveSubscriptions(subscriptions, 'crossref');
    renderCrossrefJournals();
    renderCCFJournals();
    renderQuickJournals();
    renderSubStats();
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
    document.getElementById('custom-keywords-section').style.display = useProfile ? 'none' : 'block';
    renderKeywordChips();
}

function parseKeywords(text) {
    return text.split(/[,\n;]/).map(k => k.trim()).filter(k => k);
}

function addKeywords() {
    const input = document.getElementById('custom-keywords');
    const newKws = parseKeywords(input.value);
    if (!newKws.length) return;
    const existing = subscriptions.search?.keywords || [];
    const merged = [...existing];
    for (const kw of newKws) {
        if (!merged.includes(kw)) merged.push(kw);
    }
    subscriptions.search = { keywords: merged, useProfile: false };
    input.value = '';
    saveSubscriptions(subscriptions, 's2');
    renderKeywordChips();
}

function removeKeyword(kw) {
    const keywords = (subscriptions.search?.keywords || []).filter(k => k !== kw);
    subscriptions.search = { keywords, useProfile: false };
    saveSubscriptions(subscriptions, 's2');
    renderKeywordChips();
}

let _profileKeywords = [];
let _enabledKeywords = null; // null = all enabled, Set = specific set

async function loadProfileKeywords() {
    try {
        const resp = await fetch('/api/profile');
        if (resp.ok) {
            const profile = await resp.json();
            _profileKeywords = profile.keywords || [];
            const dirInput = document.getElementById('inline-profile-direction');
            if (dirInput) dirInput.value = profile.direction || '';
            // Restore enabled set from saved search keywords
            const saved = subscriptions.search?.keywords;
            if (saved && saved.length > 0) {
                _enabledKeywords = new Set(saved);
            } else {
                _enabledKeywords = new Set(_profileKeywords);
            }
        }
    } catch {}
}

async function saveProfileInline() {
    const direction = document.getElementById('inline-profile-direction')?.value || '';
    const useProfile = document.getElementById('use-profile-keywords').checked;
    const keywords = useProfile ? [...(_enabledKeywords || _profileKeywords)] : (subscriptions.search?.keywords || []);
    const quality_criteria = '';
    try {
        await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ direction, keywords: _profileKeywords, quality_criteria }),
        });
        const origDir = document.getElementById('profile-direction');
        if (origDir) origDir.value = direction;
        const origKw = document.getElementById('profile-keywords');
        if (origKw) origKw.value = _profileKeywords.join(', ');
        // Save enabled keywords to subscriptions
        if (useProfile) {
            subscriptions.search = { keywords: keywords, useProfile: true };
        }
        await saveSubscriptions(subscriptions, 's2');
        await loadProfileKeywords();
        renderKeywordChips();
        fetch('/api/trigger/s2', { method: 'POST' }).catch(() => {});
        if (typeof showToast === 'function') showToast('已保存，正在搜索...');
    } catch (e) {
        console.error('Failed to save profile inline:', e);
        if (typeof showToast === 'function') showToast('保存失败');
    }
}

function toggleProfileKeyword(kw) {
    if (!_enabledKeywords) _enabledKeywords = new Set(_profileKeywords);
    if (_enabledKeywords.has(kw)) _enabledKeywords.delete(kw);
    else _enabledKeywords.add(kw);
    const enabled = _profileKeywords.filter(k => _enabledKeywords.has(k));
    subscriptions.search = { keywords: enabled, useProfile: true };
    saveSubscriptions(subscriptions, 's2');
    renderKeywordChips();
}

function renderKeywordChips() {
    const container = document.getElementById('keyword-chips');
    if (!container) return;
    const useProfile = subscriptions.search?.useProfile !== false;

    if (useProfile) {
        if (!_profileKeywords.length) {
            container.innerHTML = '<span style="color:var(--text-3);font-size:0.82rem">请在下方描述研究方向并保存</span>';
            return;
        }
        container.innerHTML = _profileKeywords.map(kw => {
            const enabled = !_enabledKeywords || _enabledKeywords.has(kw);
            return `<span class="badge badge--secondary ${enabled ? 'selected' : ''}" data-toggle-kw="${kw}" style="display:inline-flex;align-items:center;gap:4px;cursor:pointer;padding:4px 10px;font-size:0.82rem;${enabled ? '' : 'opacity:0.4'}">${kw}</span>`;
        }).join('');
        return;
    }

    const keywords = subscriptions.search?.keywords || [];
    if (!keywords.length) {
        container.innerHTML = '<span style="color:var(--text-3);font-size:0.82rem">输入关键词后点击添加</span>';
        return;
    }
    container.innerHTML = keywords.map(kw =>
        `<span class="badge badge--secondary selected" style="display:inline-flex;align-items:center;gap:4px;cursor:default;padding:4px 10px;font-size:0.82rem">
            ${kw}
            <button data-remove-kw="${kw}" style="background:none;border:none;color:var(--text-3);cursor:pointer;font-size:0.9rem;padding:0 2px;line-height:1">&times;</button>
        </span>`
    ).join('');
}

async function saveSearchKeywords() {
    const useProfile = document.getElementById('use-profile-keywords').checked;
    if (useProfile) {
        subscriptions.search = { keywords: [], useProfile: true };
    }
    // Custom keywords are saved via addKeywords/removeKeyword, no separate save needed
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
    resultsEl.innerHTML = '<div style="color:var(--text-2);font-size:0.85rem">搜索中...</div>';
    try {
        const resp = await fetch(`/api/author/search?query=${encodeURIComponent(query)}`);
        if (!resp.ok) throw new Error('search failed');
        const data = await resp.json();
        const authors = data.authors || [];
        if (!authors.length) {
            resultsEl.innerHTML = '<div style="color:var(--text-2);font-size:0.85rem">未找到匹配作者</div>';
            return;
        }
        const subscribedIds = new Set((subscriptions.authors || []).map(a => a.authorId));
        resultsEl.innerHTML = authors.map(a => {
            const subbed = subscribedIds.has(a.authorId);
            const aff = a.affiliations?.[0] || '';
            const orcid = a.externalIds?.ORCID || a._orcid || '';
            const orcidTag = orcid ? `<span style="font-size:0.7rem;background:rgba(168,85,247,0.15);color:#a855f7;padding:1px 5px;border-radius:3px;margin-left:4px">ORCID</span>` : '';
            return `<div class="author-search-item" style="display:flex;justify-content:space-between;align-items:center;padding:6px 8px;border-bottom:1px solid var(--border)">
                <div style="min-width:0;flex:1">
                    <div style="font-size:0.88rem;font-weight:500">${a.name}${orcidTag}</div>
                    <div style="font-size:0.75rem;color:var(--text-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${aff}${aff ? ' · ' : ''}${a.paperCount || 0} 篇论文${orcid ? ' · ' + orcid : ''}</div>
                </div>
                <button class="btn btn--secondary ${subbed ? 'followed' : ''}" data-author-id="${a.authorId}" data-author-name="${a.name}" data-author-aff="${aff}" data-author-papers="${a.paperCount || 0}" style="font-size:0.78rem;padding:4px 10px;flex-shrink:0">${subbed ? '✓ 已关注' : '+ 关注'}</button>
            </div>`;
        }).join('');
    } catch (e) {
        resultsEl.innerHTML = '<div style="color:var(--text-2);font-size:0.85rem">搜索失败，请重试</div>';
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
        <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
            <div>
                <div style="font-size:0.88rem;font-weight:500">${a.name}</div>
                <div style="font-size:0.75rem;color:var(--text-2)">${a.affiliation || ''}${a.affiliation ? ' · ' : ''}${a.paperCount || 0} 篇</div>
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

    // Journal tab view switcher
    document.querySelectorAll('[data-journal-view]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-journal-view]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const view = btn.dataset.journalView;
            document.getElementById('ccf-journal-section').style.display = view === 'ccf' ? '' : 'none';
            document.getElementById('quick-journal-section').style.display = view === 'quick' ? '' : 'none';
            document.getElementById('journal-search-section').style.display = view === 'search' ? '' : 'none';
        });
    });

    // Keyword chip events
    document.getElementById('btn-add-keyword')?.addEventListener('click', addKeywords);
    document.getElementById('use-profile-keywords')?.addEventListener('change', toggleCustomKeywords);
    document.getElementById('custom-keywords')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); addKeywords(); }
    });
    document.getElementById('keyword-chips')?.addEventListener('click', (e) => {
        const toggleBtn = e.target.closest('[data-toggle-kw]');
        if (toggleBtn) { toggleProfileKeyword(toggleBtn.dataset.toggleKw); return; }
        const removeBtn = e.target.closest('[data-remove-kw]');
        if (removeBtn) removeKeyword(removeBtn.dataset.removeKw);
    });
    document.getElementById('btn-save-profile-inline')?.addEventListener('click', saveProfileInline);
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
    let direction = '';
    let keywords = [];
    try {
        const resp = await fetch('/api/profile');
        if (resp.ok) {
            const profile = await resp.json();
            direction = profile.direction || '';
            keywords = profile.keywords || [];
        }
    } catch {}
    if (!direction && !keywords.length) {
        if (typeof showToast === 'function') showToast('请先设置研究方向关键词');
        return;
    }

    if (typeof showToast === 'function') showToast('正在分析研究方向，推荐分类...');
    try {
        const resp = await fetch('/api/recommend-categories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ direction, keywords }),
        });
        if (!resp.ok) throw new Error('recommendation failed');
        const data = await resp.json();

        const recommended = new Set(subscriptions.arxiv?.categories || []);
        (data.primary || []).forEach(c => recommended.add(c));
        (data.secondary || []).forEach(c => recommended.add(c));

        subscriptions.arxiv = subscriptions.arxiv || { categories: [] };
        subscriptions.arxiv.categories = [...recommended];
        await saveSubscriptions(subscriptions, 'arxiv');
        renderArxivCategories();
        if (typeof showToast === 'function') showToast(`智能推荐完成：${recommended.size} 个分类（核心 ${data.primary?.length || 0}，相关 ${data.secondary?.length || 0}）`);
    } catch (e) {
        console.error('Smart recommend failed:', e);
        if (typeof showToast === 'function') showToast('推荐失败，请稍后重试');
    }
}
