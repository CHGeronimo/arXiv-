// js/render.js — paper card rendering and pagination

import {
    filteredPapers, allPapers, activeFilters, sortOrder, currentPage, PAGE_SIZE,
    _bookmarks, _readPapers, escAttr, inferType, showToast,
    setCurrentPage,
} from './state.js';
import { applyFiltersAndSort, updateFilterBadges } from './filters.js';

export function renderPapers() {
    const container = document.getElementById('paper-container');
    const result = applyFiltersAndSort();

    if (!result.length) {
        container.innerHTML = '<div class="empty-state">暂无匹配论文。尝试调整筛选条件。</div>';
        updatePaperCount();
        return;
    }

    updatePaperCount();
    const totalPages = Math.ceil(result.length / PAGE_SIZE);
    const page = Math.max(1, Math.min(currentPage, totalPages || 1));
    setCurrentPage(page);
    const start = (page - 1) * PAGE_SIZE;
    const pagePapers = result.slice(start, start + PAGE_SIZE);

    container.innerHTML = pagePapers.map((paper, i) => {
        const ai = paper.AI || {};
        const hasAi = !!(ai.tldr || paper.tldr);
        const sourceBadge = paper.source === 'crossref'
            ? `<span class="source-badge crossref">${paper.journal_title || 'Journal'}</span>`
            : paper.source === 'dblp'
            ? `<span class="source-badge dblp">DBLP</span>`
            : paper.source === 'semantic_scholar'
            ? `<span class="source-badge s2">S2</span>`
            : `<span class="source-badge arxiv">arXiv</span>`;
        const venueBadge = paper.venue ? `<span class="venue-badge">${paper.venue}</span>` : '';
        const accBadge = paper.acceptance ? `<span class="acc-badge ${paper.acceptance}">${paper.acceptance}</span>` : '';
        const citeBadge = paper.citation_count ? `<span class="cite-badge">&#9733; ${paper.citation_count}</span>` : '';
        const articleType = paper.article_type || inferType(paper);
        const typeTag = articleType === 'news' ? '<span class="paper-cat" style="background:rgba(249,115,22,0.2);color:#f97316">新闻</span>' : '';
        const aiBadge = hasAi ? '<span class="ai-badge">AI</span>' : '';
        const rec = ai.recommendation || '';
        const recLabels = { 'must-read': 'Must Read', 'recommended': 'Recommended', 'reference': 'Reference' };
        const recBadge = rec && recLabels[rec] ? `<span class="rec-badge ${rec}">${recLabels[rec]}</span>` : '';
        const tldr = ai.tldr || paper.tldr || '';
        const cardTldr = tldr ? `<div class="card-tldr">${tldr}</div>` : '';
        const categories = (paper.categories || []).map(c => `<span class="paper-cat">${c}</span>`).join('');
        const authorList = (paper.authors || []).slice(0, 3).map(a =>
            `<span class="author-link" data-author-name="${escAttr(a)}">${a}</span>`
        ).join(', ');
        const authors = authorList + ((paper.authors || []).length > 3 ? ' et al.' : '');
        const title = ai.title_zh || paper.title_zh || paper.title || '';
        const codeBadge = paper.code_url ? `<span class="paper-cat" style="background:rgba(34,197,94,0.2);color:#22c55e">Code</span>` : '';
        const idx = start + i;
        const isBookmarked = _bookmarks.has(paper.id);
        const isRead = _readPapers.has(paper.id);
        const feedback = paper.feedback_rating || '';
        return `
            <div class="paper-card ${isRead ? 'is-read' : ''}" data-idx="${idx}" data-rec="${rec}">
                <div class="paper-header">
                    ${sourceBadge}${venueBadge}${accBadge}${aiBadge}${recBadge}${typeTag}
                    <div class="paper-categories">${categories}${codeBadge}</div>
                    <button class="bookmark-btn ${isBookmarked ? 'active' : ''}" data-bm-id="${escAttr(paper.id)}" title="${isBookmarked ? '取消收藏' : '收藏'}">${isBookmarked ? '★' : '☆'}</button>
                </div>
                <div class="paper-title">${title}</div>
                ${cardTldr}
                <div class="paper-footer">
                    <span class="paper-authors">${authors}</span>
                    <div class="card-actions">
                        <button class="card-vote-btn ${feedback === 'useful' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-rating="useful" title="有用">&#9757;</button>
                        <button class="card-vote-btn ${feedback === 'not_useful' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-rating="not_useful" title="没用">&#9759;</button>
                        <span class="paper-meta-date">${paper.published_date || ''} ${citeBadge}</span>
                    </div>
                </div>
            </div>`;
    }).join('');

    if (totalPages > 1) {
        container.innerHTML += `
            <div class="pagination" style="grid-column:1/-1;display:flex;justify-content:center;gap:8px;padding:16px">
                <button class="follow-btn" onclick="window._changePage(-1)" ${page <= 1 ? 'disabled style="opacity:0.5"' : ''}>上一页</button>
                <span style="padding:6px 12px;color:var(--text-secondary)">${page}/${totalPages}</span>
                <button class="follow-btn" onclick="window._changePage(1)" ${page >= totalPages ? 'disabled style="opacity:0.5"' : ''}>下一页</button>
            </div>`;
    }
}

export function changePage(delta) {
    setCurrentPage(currentPage + delta);
    renderPapers();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

export function updatePaperCount() {
    const el = document.getElementById('paper-count');
    if (!el) return;
    const sq = document.getElementById('sidebar-search-input')?.value?.trim() || '';
    const df = document.getElementById('sidebar-date-filter')?.value || '';
    const total = allPapers.length;
    const shown = filteredPapers.length;
    const hasFilter = sq || df || Object.values(activeFilters).some(s => s.size > 0);
    el.textContent = hasFilter ? `${shown}/${total} 篇` : `${total} 篇`;
}
