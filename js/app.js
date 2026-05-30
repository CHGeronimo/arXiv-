// js/app.js
let allPapers = [];
let filteredPapers = [];
let currentSourceFilter = 'all';
let searchQuery = '';
let refreshTimer = null;
let currentPage = 1;
const PAGE_SIZE = 30;

document.addEventListener('DOMContentLoaded', () => {
    loadPapers();
    startAutoRefresh();

    // Event delegation for paper cards
    document.getElementById('paper-container').addEventListener('click', (e) => {
        const card = e.target.closest('.paper-card[data-idx]');
        if (card) {
            const idx = parseInt(card.dataset.idx);
            if (filteredPapers[idx]) openPaperDetail(filteredPapers[idx]);
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closePaperModal();
            closeSubscriptionModal();
        }
    });
});

async function loadPapers() {
    try {
        const resp = await fetch('/api/papers');
        if (resp.ok) {
            const data = await resp.json();
            allPapers = data.papers || [];
        }
    } catch (e) {
        console.error('Failed to load papers:', e);
    }
    renderPapers();
}

function filterBySource(source) {
    currentSourceFilter = source;
    document.querySelectorAll('.source-filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    renderPapers();
}

function handleSearch() {
    searchQuery = document.getElementById('search-input').value.trim().toLowerCase();
    renderPapers();
}

function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(async () => {
        try {
            const resp = await fetch('/api/papers');
            if (resp.ok) {
                const data = await resp.json();
                const newPapers = data.papers || [];
                if (newPapers.length !== allPapers.length) {
                    allPapers = newPapers;
                    renderPapers();
                }
            }
        } catch {}
    }, 15000);
}

function renderPapers() {
    const container = document.getElementById('paper-container');
    filteredPapers = allPapers;

    if (currentSourceFilter !== 'all') {
        filteredPapers = filteredPapers.filter(p => p.source === currentSourceFilter);
    }

    if (searchQuery) {
        filteredPapers = filteredPapers.filter(p => {
            const text = ((p.title_zh || p.title || '') + ' ' + (p.summary_zh || p.summary || '') + ' ' + (p.authors || []).join(' ')).toLowerCase();
            return text.includes(searchQuery);
        });
    }

    if (!filteredPapers.length) {
        container.innerHTML = '<div class="empty-state">暂无论文数据。请先配置订阅并等待爬取。</div>';
        updatePaperCount();
        return;
    }

    updatePaperCount();

    const totalPages = Math.ceil(filteredPapers.length / PAGE_SIZE);
    if (currentPage > totalPages) currentPage = totalPages || 1;
    const start = (currentPage - 1) * PAGE_SIZE;
    const pagePapers = filteredPapers.slice(start, start + PAGE_SIZE);

    container.innerHTML = pagePapers.map(paper => {
        const ai = paper.AI || {};
        const hasAi = !!(ai.tldr || paper.tldr);
        const sourceBadge = paper.source === 'crossref'
            ? `<span class="source-badge crossref">${paper.journal_title || 'Journal'}</span>`
            : `<span class="source-badge arxiv">arXiv</span>`;
        const aiBadge = hasAi ? '<span class="ai-badge">AI</span>' : '';

        const categories = (paper.categories || []).map(c =>
            `<span class="paper-cat">${c}</span>`
        ).join('');

        const authors = (paper.authors || []).slice(0, 3).join(', ') +
            ((paper.authors || []).length > 3 ? ' et al.' : '');

        const summary = ai.summary_zh || paper.summary_zh || paper.summary || '';
        const title = ai.title_zh || paper.title_zh || paper.title || '';

        const tldr = (ai.tldr || paper.tldr) ? `<div class="paper-tldr">${ai.tldr || paper.tldr}</div>` : '';
        const codeBadge = paper.code_url ? `<span class="paper-cat" style="background:rgba(34,197,94,0.2);color:#22c55e">Code</span>` : '';

        const idx = start + pagePapers.indexOf(paper);
        return `
            <div class="paper-card" data-idx="${idx}">
                <div class="paper-header">
                    ${sourceBadge}${aiBadge}
                    <div class="paper-categories">${categories}${codeBadge}</div>
                </div>
                <div class="paper-title">${title}</div>
                <div class="paper-authors">${authors}</div>
                <div class="paper-summary">${summary.substring(0, 200)}...</div>
                ${tldr}
                <div class="paper-meta">
                    <span>${paper.published_date || ''}</span>
                    <span>${paper.publisher || ''}</span>
                </div>
            </div>
        `;
    }).join('');

    // Pagination
    if (totalPages > 1) {
        container.innerHTML += `
            <div class="pagination" style="grid-column:1/-1;display:flex;justify-content:center;gap:8px;padding:16px">
                <button class="follow-btn" onclick="changePage(-1)" ${currentPage <= 1 ? 'disabled style="opacity:0.5"' : ''}>上一页</button>
                <span style="padding:6px 12px;color:var(--text-secondary)">${currentPage}/${totalPages}</span>
                <button class="follow-btn" onclick="changePage(1)" ${currentPage >= totalPages ? 'disabled style="opacity:0.5"' : ''}>下一页</button>
            </div>
        `;
    }
}

function changePage(delta) {
    currentPage += delta;
    renderPapers();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function openPaperDetail(paper) {
    const modal = document.getElementById('paper-modal');
    const detail = document.getElementById('paper-detail');

    const title = paper.title_zh || paper.title;
    const origTitle = (paper.title_zh && paper.title) ? `<div style="color:var(--text-secondary);font-size:0.85rem;margin-top:4px">${paper.title}</div>` : '';
    const sourceBadge = paper.source === 'crossref'
        ? `<span class="source-badge crossref">${paper.journal_title || 'Journal'}</span>`
        : `<span class="source-badge arxiv">arXiv</span>`;

    const aiFields = paper.AI || {};
    const sections = [];
    if (aiFields.tldr) sections.push(`<h3>TL;DR</h3><p>${aiFields.tldr}</p>`);
    if (aiFields.motivation) sections.push(`<h3>Motivation</h3><p>${aiFields.motivation}</p>`);
    if (aiFields.method) sections.push(`<h3>Method</h3><p>${aiFields.method}</p>`);
    if (aiFields.result) sections.push(`<h3>Result</h3><p>${aiFields.result}</p>`);
    if (aiFields.conclusion) sections.push(`<h3>Conclusion</h3><p>${aiFields.conclusion}</p>`);

    // Fallback to top-level fields (non-AI enhanced)
    if (!sections.length) {
        if (paper.tldr) sections.push(`<h3>TL;DR</h3><p>${paper.tldr}</p>`);
        if (paper.motivation) sections.push(`<h3>Motivation</h3><p>${paper.motivation}</p>`);
        if (paper.method) sections.push(`<h3>Method</h3><p>${paper.method}</p>`);
        if (paper.result) sections.push(`<h3>Result</h3><p>${paper.result}</p>`);
        if (paper.conclusion) sections.push(`<h3>Conclusion</h3><p>${paper.conclusion}</p>`);
    }

    const abstract = paper.summary_zh || aiFields.summary_zh || paper.summary || '';
    if (abstract && !sections.length) sections.push(`<h3>Abstract</h3><p>${abstract}</p>`);

    const codeUrl = paper.code_url || '';
    const codeStars = paper.code_stars ? ` (${paper.code_stars} stars)` : '';

    detail.innerHTML = `
        <div class="paper-header">${sourceBadge}
            <span class="paper-cat">${paper.published_date || ''}</span>
        </div>
        <h2 style="margin:12px 0">${title}</h2>
        ${origTitle}
        <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:12px">
            ${(paper.authors || []).join(', ')}
        </p>
        ${sections.join('<hr style="border-color:var(--border-color);margin:12px 0">')}
        <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap">
            ${paper.url ? `<a href="${paper.url}" target="_blank" class="follow-btn">论文链接</a>` : ''}
            ${paper.pdf ? `<a href="${paper.pdf}" target="_blank" class="follow-btn">PDF</a>` : ''}
            ${paper.doi ? `<a href="https://doi.org/${paper.doi}" target="_blank" class="follow-btn">DOI</a>` : ''}
            ${codeUrl ? `<a href="${codeUrl}" target="_blank" class="follow-btn" style="border-color:#22c55e;color:#22c55e">Code${codeStars}</a>` : ''}
        </div>
    `;

    modal.classList.add('active');
}

function closePaperModal() {
    document.getElementById('paper-modal').classList.remove('active');
}

function updatePaperCount() {
    const el = document.getElementById('paper-count');
    if (el) {
        const total = allPapers.length;
        const shown = filteredPapers.length;
        el.textContent = searchQuery || currentSourceFilter !== 'all'
            ? `${shown}/${total} 篇`
            : `${total} 篇`;
    }
}
