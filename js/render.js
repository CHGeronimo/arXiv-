// js/render.js — paper card rendering and pagination

import {
    filteredPapers, allPapers, activeFilters, sortOrder, currentPage, PAGE_SIZE, dateWithinDays,
    _bookmarks, _readPapers, escAttr, inferType, showToast, saveUIState,
    setCurrentPage, getFeedbackForPaper,
} from './state.js';
import { applyFiltersAndSort, updateFilterBadges } from './filters.js';
import { isSelected } from './compare.js';

export function renderPapers() {
    const container = document.getElementById('paper-container');
    const result = applyFiltersAndSort();
    saveUIState();  // 任何渲染都同步持久化 UI 状态（F5 可恢复）
    // 同步日期快捷按钮的激活态
    document.querySelectorAll('.within-btn').forEach(b =>
        b.classList.toggle('active', parseInt(b.dataset.within) === dateWithinDays));

    const chipsRow = _renderActiveChips(result.length);
    if (!result.length) {
        container.innerHTML = `${chipsRow}<div class="empty-state">暂无匹配论文。尝试调整筛选条件。</div>`;
        updatePaperCount();
        return;
    }

    updatePaperCount();
    const totalPages = Math.ceil(result.length / PAGE_SIZE);
    const page = Math.max(1, Math.min(currentPage, totalPages || 1));
    setCurrentPage(page);
    const start = (page - 1) * PAGE_SIZE;
    const pagePapers = result.slice(start, start + PAGE_SIZE);

    container.innerHTML = chipsRow + pagePapers.map((paper, i) => {
        const ai = paper.AI || {};
        const hasAi = !!(ai.tldr || paper.tldr);
        const sourceBadge = paper.source === 'crossref'
            ? `<span class="badge badge--source-crossref">${paper.journal_title || 'Journal'}</span>`
            : paper.source === 'dblp'
            ? `<span class="badge badge--source-dblp">DBLP</span>`
            : paper.source === 'semantic_scholar'
            ? `<span class="badge badge--source-s2">S2</span>`
            : paper.source === 'citation'
            ? `<span class="badge badge--venue">🔗 引文</span>`
            : paper.source === 'openalex'
            ? `<span class="badge badge--source-s2">OA</span>`
            : paper.source === 'author_s2'
            ? `<span class="badge badge--source-s2">作者</span>`
            : `<span class="badge badge--source-arxiv">arXiv</span>`;
        const venueBadge = paper.venue ? `<span class="badge badge--venue">${paper.venue}</span>` : '';

        const citeBadge = paper.citation_count ? `<span class="cite-badge">&#9733; ${paper.citation_count}</span>` : '';
        const articleType = paper.article_type || inferType(paper);
        const typeTag = articleType === 'news' ? '<span class="paper-cat" style="background:rgba(249,115,22,0.2);color:#f97316">新闻</span>' : '';
        const aiBadge = hasAi ? '<span class="ai-badge">AI</span>' : '';
        const rec = ai.recommendation || '';
        const relScore = ai.relevance_score || 0;
        const recLabels = { 'must-read': 'Must Read', 'recommended': 'Recommended', 'reference': 'Reference' };
        // Split reference into high (7+) and low (6) priority
        let recBadge = '';
        if (rec === 'reference') {
            if (relScore >= 7) {
                recBadge = `<span class="badge badge--reference">Reference</span>`;
            } else {
                recBadge = `<span class="badge badge--ref-low">浅参考</span>`;
            }
        } else if (rec && recLabels[rec]) {
            recBadge = `<span class="badge badge--${rec === 'must-read' ? 'must' : 'recommend'}">${recLabels[rec]}</span>`;
        }
        const ccfBadge = paper.ccf_tier ? `<span class="badge badge--ccf">${paper.ccf_tier}</span>` : '';
        const tldr = ai.tldr || paper.tldr || '';
        const cardTldr = tldr ? `<div class="card-tldr">${tldr}</div>` : '';
        const relation = paper.relation
            ? `<div class="card-relation" title="${escAttr(paper.relation)}">🧭 ${escAttr(paper.relation)}</div>`
            : '';
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
        const fb = getFeedbackForPaper(paper.id);
        const userRating = fb.rating || '';
        const userRel = fb.relevance || 0;
        const userNov = fb.novelty || 0;
        const showFb = !!(userRating || userRel || userNov);  // 投过票才展开滑杆
        const qualScore = ai.quality_score || 0;
        const scoreChipCls = (n) => n >= 8 ? 'score--hi' : n >= 6 ? 'score--mid' : 'score--lo';
        const scoreChips = hasAi && (relScore || qualScore)
            ? `<span class="score-chip ${scoreChipCls(relScore)}" title="相关性 ${relScore}/10">R${relScore}</span><span class="score-chip ${scoreChipCls(qualScore)}" title="质量 ${qualScore}/10">Q${qualScore}</span>`
            : '';
        return `
            <div class="paper-card ${isRead ? 'is-read' : ''}" data-idx="${idx}" data-rec="${rec === 'reference' && relScore < 7 ? 'ref-low' : rec}">
                <div class="paper-header">
                    ${sourceBadge}${venueBadge}${ccfBadge}${aiBadge}${recBadge}${scoreChips}${typeTag}
                    <div class="paper-categories">${categories}${codeBadge}</div>
                    <button class="bookmark-btn ${isBookmarked ? 'active' : ''}" data-bm-id="${escAttr(paper.id)}" title="${isBookmarked ? '取消收藏' : '收藏'}">${isBookmarked ? '★' : '☆'}</button>
                </div>
                <div class="paper-title">${title}</div>
                ${cardTldr}
                ${relation}
                <div class="paper-footer">
                    <span class="paper-authors">${authors}</span>
                    <div class="card-actions">
                        <button class="card-vote-btn up ${userRating === 'like' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-action="like" title="有用">&#9757;</button>
                        <button class="card-vote-btn down ${userRating === 'dislike' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-action="dislike" title="没用">&#9759;</button>
                        <button class="card-vote-btn compare-btn ${isSelected(paper.id) ? 'active' : ''}" data-compare-id="${escAttr(paper.id)}" title="加入对比（最多3篇）">⇄</button>
                        <button class="card-vote-btn delete" data-delete-id="${escAttr(paper.id)}" title="删除">✕</button>
                        <span class="paper-meta-date">${paper.published_date || ''} ${citeBadge}</span>
                    </div>
                </div>
                <div class="card-feedback-detail ${showFb ? 'visible' : ''}" data-feedback-detail="${escAttr(paper.id)}">
                    <div class="feedback-slider-row"><span class="feedback-label">相关性</span><input type="range" min="1" max="5" value="${userRel || 3}" class="feedback-slider" data-slider-type="relevance" data-slider-id="${escAttr(paper.id)}"><span class="feedback-val">${userRel || '-'}</span></div>
                    <div class="feedback-slider-row"><span class="feedback-label">新颖性</span><input type="range" min="1" max="5" value="${userNov || 3}" class="feedback-slider" data-slider-type="novelty" data-slider-id="${escAttr(paper.id)}"><span class="feedback-val">${userNov || '-'}</span></div>
                    <div class="feedback-note-row"><input type="text" class="feedback-note" data-note-id="${escAttr(paper.id)}" value="${escAttr(fb.note || '')}" placeholder="评语（可选）：为什么有用/没用？会直接影响 AI 评分"></div>
                </div>
            </div>`;
    }).join('');

    if (totalPages > 1) {
        const pageBtns = [];
        const maxBtns = 7;
        let startP = Math.max(1, page - 3);
        let endP = Math.min(totalPages, startP + maxBtns - 1);
        if (endP - startP < maxBtns - 1) startP = Math.max(1, endP - maxBtns + 1);

        if (startP > 1) { pageBtns.push(`<button class="page-btn" data-goto="1">1</button>`); if (startP > 2) pageBtns.push(`<span class="page-ellipsis">...</span>`); }
        for (let p = startP; p <= endP; p++) { pageBtns.push(`<button class="page-btn${p === page ? ' active' : ''}" data-goto="${p}">${p}</button>`); }
        if (endP < totalPages) { if (endP < totalPages - 1) pageBtns.push(`<span class="page-ellipsis">...</span>`); pageBtns.push(`<button class="page-btn" data-goto="${totalPages}">${totalPages}</button>`); }

        container.innerHTML += `
            <div class="pagination" style="grid-column:1/-1;display:flex;justify-content:center;align-items:center;gap:6px;padding:16px;flex-wrap:wrap">
                <button class="btn btn--secondary" onclick="window._changePage(-1)" ${page <= 1 ? 'disabled style="opacity:0.5"' : ''}>上一页</button>
                ${pageBtns.join('')}
                <button class="btn btn--secondary" onclick="window._changePage(1)" ${page >= totalPages ? 'disabled style="opacity:0.5"' : ''}>下一页</button>
                <span style="margin-left:8px;color:var(--text-3);font-size:0.8rem">跳至</span>
                <input id="page-jump" type="number" min="1" max="${totalPages}" value="${page}" style="width:48px;padding:2px 6px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--surface-1);color:var(--text-0);font-size:0.85rem;text-align:center" />
                <span style="color:var(--text-3);font-size:0.8rem">/${totalPages}</span>
            </div>`;
    }
}

export function changePage(delta) {
    setCurrentPage(currentPage + delta);
    renderPapers();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── 已选条件 chips 行：激活的筛选一眼可见，可单个移除 ──
const GROUP_LABELS = { source: '来源', venue: '会议', journal: '期刊', category: '领域', type: '推荐', bookmarked: '收藏', ccf: 'CCF', today: '时效', code: '代码' };

function _renderActiveChips(shownCount) {
    const chips = [];
    const push = (group, value, label) =>
        chips.push(`<span class="active-chip" data-chip-group="${escAttr(group)}" data-chip-value="${escAttr(value)}">${escAttr(label)} <b>×</b></span>`);
    for (const [group, set] of Object.entries(activeFilters)) {
        for (const v of set) {
            if (group === 'bookmarked') push(group, 'yes', '⭐ 收藏');
            else if (group === 'today') push(group, 'yes', '🌅 今日新到');
            else if (group === 'code') push(group, 'yes', '🐙 有代码');
            else push(group, v, `${GROUP_LABELS[group] || group}: ${v}`);
        }
    }
    const sq = document.getElementById('sidebar-search-input')?.value?.trim();
    if (sq) chips.push(`<span class="active-chip" data-chip-group="search">🔍 ${escAttr(sq)} <b>×</b></span>`);
    const df = document.getElementById('sidebar-date-filter')?.value;
    if (df) chips.push(`<span class="active-chip" data-chip-group="date">📅 ${escAttr(df)} <b>×</b></span>`);
    if (dateWithinDays > 0) chips.push(`<span class="active-chip" data-chip-group="within">${dateWithinDays === 1 ? '今天' : `${dateWithinDays}天内`} <b>×</b></span>`);
    if (!chips.length) return '';
    return `<div class="active-chips" style="grid-column:1/-1;display:flex;flex-wrap:wrap;gap:4px;align-items:center">
        <span style="font-size:0.72rem;color:var(--text-3)">已选 ${chips.length} 项 · ${shownCount} 篇：</span>${chips.join('')}
    </div>`;
}

export function updatePaperCount() {
    const el = document.getElementById('paper-count');
    if (!el) return;
    const sq = document.getElementById('sidebar-search-input')?.value?.trim() || '';
    const df = document.getElementById('sidebar-date-filter')?.value || '';
    const active = allPapers.filter(p => {
        const ai = p.AI || {};
        if (ai.recommendation === 'ignore') return false;
        if (ai.recommendation === 'reference' && (ai.relevance_score || 0) < 7) return false;
        return true;
    }).length;
    const shown = filteredPapers.length;
    const hasFilter = sq || df || Object.values(activeFilters).some(s => s.size > 0);
    el.textContent = hasFilter ? `${shown}/${active} 篇` : `${active} 篇`;
    // 动态标题：后台标签页一眼可见新必读
    const mustRead = allPapers.filter(p => (p.AI || {}).recommendation === 'must-read').length;
    document.title = `${mustRead ? `(${mustRead}🔥) ` : ''}arxivSCI-daily`;
}
