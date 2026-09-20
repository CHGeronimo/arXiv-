// js/modal.js — paper detail and profile modals

import { markRead, escAttr, showToast, setAllPapers, getFeedbackForPaper, filteredPapers, PAGE_SIZE, currentPage } from './state.js';
import { exportBibtex, fetchKnowledgeCard, fetchFulltextAnalysis, fetchFullPaper, deletePaper } from './api.js';
import { renderPapers } from './render.js';

let _navIdx = -1;

export function navigateModal(delta) {
    const fp = filteredPapers;
    if (!fp || !fp.length) return;
    const max = fp.length - 1;
    const next = Math.max(0, Math.min(max, _navIdx + delta));
    if (next === _navIdx) { showToast(delta > 0 ? '已是最后一篇' : '已是第一篇'); return; }
    openPaperDetail(fp[next], next);
}

export async function openPaperDetail(paper, navIdx) {
    if (navIdx !== undefined && navIdx !== null) _navIdx = navIdx;
    else _navIdx = filteredPapers.findIndex(p => p.id === paper.id);
    const wasRead = markRead(paper.id);
    if (wasRead) renderPapers();
    // 列表是轻字段，打开详情时懒加载完整 AI 解读/摘要
    const full = await fetchFullPaper(paper.id);
    if (full && full.id) {
        paper = { ...paper, ...full, AI: { ...(paper.AI || {}), ...(full.AI || {}) } };
    }
    const modal = document.getElementById('paper-modal');
    const detail = document.getElementById('paper-detail');

    const aiTitle = (paper.AI || {}).title_zh || '';
    const titleZh = aiTitle || paper.title_zh || '';
    const titleEn = paper.title || '';
    const title = titleZh || titleEn;
    const origTitle = (titleZh && titleEn && titleZh !== titleEn) ? `<div style="color:var(--text-2);font-size:0.85rem;margin-top:4px">${titleEn}</div>` : '';
    const sourceBadge = paper.source === 'crossref'
        ? `<span class="badge badge--source-crossref">${escAttr(paper.journal_title || '期刊')}</span>`
        : paper.source === 'dblp'
        ? `<span class="badge badge--source-dblp">DBLP</span>`
        : paper.source === 'semantic_scholar'
        ? `<span class="badge badge--source-s2">S2</span>`
        : `<span class="badge badge--source-arxiv">arXiv</span>`;
    const venueInfo = paper.venue ? ` <span class="badge badge--venue">${escAttr(paper.venue)}</span>` : '';
    const ccfInfo = paper.ccf_tier ? ` <span class="badge badge--ccf">${paper.ccf_tier}</span>` : '';
    const citeInfo = paper.citation_count ? `<div style="margin-bottom:8px;font-size:0.85rem;color:var(--text-2)">&#9733; ${paper.citation_count} citations</div>` : '';

    const aiFields = paper.AI || {};
    const sections = [];
    const aiParts = [];
    if (aiFields.tldr) aiParts.push(`<b>TL;DR</b> ${escAttr(aiFields.tldr)}`);
    if (aiFields.motivation) aiParts.push(`<b>Motivation</b> ${escAttr(aiFields.motivation)}`);
    if (aiFields.method) aiParts.push(`<b>Method</b> ${escAttr(aiFields.method)}`);
    if (aiFields.result) aiParts.push(`<b>Result</b> ${escAttr(aiFields.result)}`);
    if (aiFields.conclusion) aiParts.push(`<b>Conclusion</b> ${escAttr(aiFields.conclusion)}`);
    if (aiParts.length) sections.push(`<h3>AI 解读</h3><p>${aiParts.join('<br><br>')}</p>`);

    const summaryZh = aiFields.summary_zh || paper.summary_zh || '';
    if (summaryZh) sections.push(`<h3>中文摘要</h3><p>${escAttr(summaryZh)}</p>`);
    const abstractEn = paper.summary || '';
    if (abstractEn) sections.push(`<h3>Abstract</h3><p>${escAttr(abstractEn)}</p>`);
    if (!sections.length) sections.push(`<p style="color:var(--text-2)">暂无摘要</p>`);

    const codeUrl = paper.code_url || '';

    // 🎯 评分归因：为什么推荐（匹配了哪些反馈学到的偏好主题）
    const pref = paper.preference || {};
    const prefHtml = ((pref.liked || []).length || (pref.disliked || []).length) ? `
        <div style="margin:0 0 12px;padding:8px 12px;background:var(--accent-muted);border-radius:8px;font-size:0.8rem">
            ${(pref.liked || []).length ? `<div style="color:var(--success)">🎯 匹配你的偏好主题：${escAttr((pref.liked || []).join('、'))} <span style="color:var(--text-3)">（来自你的点赞/手动添加，正在影响评分）</span></div>` : ''}
            ${(pref.disliked || []).length ? `<div style="color:var(--danger);margin-top:4px">⊘ 命中你的负偏好：${escAttr((pref.disliked || []).join('、'))}</div>` : ''}
        </div>` : '';


    const fb = getFeedbackForPaper(paper.id);
    const userRating = fb.rating || '';
    const userRel = fb.relevance || 0;
    const userNov = fb.novelty || 0;
    const hasFeedback = userRating || userRel || userNov;

    detail.innerHTML = `
        <div style="position:sticky;top:-25px;z-index:5;display:flex;justify-content:space-between;align-items:center;background:var(--surface-1);padding:2px 0 8px;margin-bottom:4px">
            <div style="display:flex;gap:6px;align-items:center">
                <button class="btn btn--secondary" id="modal-prev" title="上一篇 (J)" style="font-size:0.9rem;padding:2px 12px">‹</button>
                <span style="font-size:0.75rem;color:var(--text-3)">${_navIdx + 1} / ${filteredPapers.length}</span>
                <button class="btn btn--secondary" id="modal-next" title="下一篇 (K)" style="font-size:0.9rem;padding:2px 12px">›</button>
            </div>
        </div>
        <div class="paper-header">${sourceBadge}${venueInfo}${ccfInfo}
            <span class="paper-cat">${paper.published_date || ''}</span>
        </div>
        <h2 style="margin:12px 0">${escAttr(title)}</h2>
        ${escAttr(titleEn)}
        <p style="color:var(--text-2);font-size:0.85rem;margin-bottom:12px">
            ${(paper.authors || []).map(a => `<span class="author-link" data-author-name="${escAttr(a)}">${escAttr(a)}</span>`).join(', ')}
        </p>
        ${citeInfo}
        ${prefHtml}
        ${sections.join('')}
        <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap">
            ${paper.url ? `<a href="${escAttr(paper.url)}" target="_blank" rel="noopener" class="btn btn--secondary">论文链接</a>` : ''}
            ${paper.pdf ? `<a href="${escAttr(paper.pdf)}" target="_blank" rel="noopener" class="btn btn--secondary">PDF</a>` : ''}
            ${paper.doi ? `<a href="${escAttr(paper.doi ? 'https://doi.org/' + paper.doi : '')}" target="_blank" rel="noopener" class="btn btn--secondary">DOI</a>` : ''}
            ${codeUrl ? `<a href="${escAttr(codeUrl)}" target="_blank" rel="noopener" class="btn btn--secondary" style="border-color:#22c55e;color:#22c55e">Code</a>` : ''}
            <button class="btn btn--secondary" data-export-bibtex="${escAttr(paper.id)}">BibTeX</button>
            <button class="btn btn--secondary ${userRating === 'like' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-action="like" style="border-color:#22c55e;color:#22c55e;font-size:0.95rem;padding:8px 18px">&#9757; 有用</button>
            <button class="btn btn--secondary ${userRating === 'dislike' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-action="dislike" style="border-color:#ef4444;color:#ef4444;font-size:0.95rem;padding:8px 18px">&#9759; 没用</button>
            <div class="modal-feedback-sliders" style="margin-top:12px">
                <div class="feedback-slider-row"><span class="feedback-label">相关性</span><input type="range" min="1" max="5" value="${userRel || 3}" class="feedback-slider" data-slider-type="relevance" data-slider-id="${escAttr(paper.id)}"><span class="feedback-val">${userRel || '-'}</span></div>
                <div class="feedback-slider-row"><span class="feedback-label">新颖性</span><input type="range" min="1" max="5" value="${userNov || 3}" class="feedback-slider" data-slider-type="novelty" data-slider-id="${escAttr(paper.id)}"><span class="feedback-val">${userNov || '-'}</span></div>
                <div class="feedback-note-row"><input type="text" class="feedback-note" data-note-id="${escAttr(paper.id)}" value="${escAttr(fb.note || '')}" placeholder="评语（可选）：为什么有用/没用？会直接影响 AI 评分"></div>
            </div>
            <button class="btn btn--secondary" data-delete-id="${escAttr(paper.id)}" style="border-color:#ef4444;color:#ef4444;margin-left:auto">删除</button>
        </div>
            <div id="knowledge-card-section"></div>
            <div id="fulltext-analysis-section"></div>`;

    // Knowledge card (L1)
    fetchKnowledgeCard(paper.id).then(card => {
        if (!card) return;
        const el = document.getElementById('knowledge-card-section');
        if (!el) return;
        el.innerHTML = `
            <h3 style="margin-top:16px">知识卡片</h3>
            <div style="margin:8px 0;padding:12px;background:var(--accent-muted);border-radius:8px">
                <div style="margin-bottom:8px"><span style="color:var(--accent-primary);font-weight:600">Problem</span><p style="margin:4px 0;font-size:0.88rem">${escAttr(card.problem || 'N/A')}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-primary);font-weight:600">Method</span><p style="margin:4px 0;font-size:0.88rem">${escAttr(card.method_extracted || 'N/A')}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-primary);font-weight:600">Result</span><p style="margin:4px 0;font-size:0.88rem">${escAttr(card.result_extracted || 'N/A')}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-primary);font-weight:600">Keywords</span>
                    <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px">${(card.keywords || []).map(k => `<span style="padding:2px 8px;border-radius:3px;font-size:0.75rem;background:var(--surface-2);color:var(--accent-primary)">${escAttr(k)}</span>`).join('')}</div>
                </div>
                ${card.relation_to_profile ? `<div><span style="color:var(--accent-primary);font-weight:600">Profile Relation</span><p style="margin:4px 0;font-size:0.85rem;color:var(--text-2)">${escAttr(card.relation_to_profile)}</p></div>` : ''}
            </div>`;
    });
    fetchFulltextAnalysis(paper.id).then(analysis => {
        if (!analysis) return;
        const el = document.getElementById('fulltext-analysis-section');
        if (!el) return;
        el.innerHTML = `
            <h3 style="margin-top:16px">正文深度分析</h3>
            <div style="margin:8px 0;padding:12px;background:var(--accent-muted);border-radius:8px">
                <div style="margin-bottom:8px"><span style="color:var(--accent-primary);font-weight:600">方法实现</span><p style="margin:4px 0;font-size:0.88rem">${escAttr(analysis.method_implementation || 'N/A')}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-primary);font-weight:600">实验设计</span><p style="margin:4px 0;font-size:0.88rem">${escAttr(analysis.experimental_design || 'N/A')}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-primary);font-weight:600">关键结果</span><p style="margin:4px 0;font-size:0.88rem">${escAttr(analysis.key_results_detail || 'N/A')}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-primary);font-weight:600">局限性</span><p style="margin:4px 0;font-size:0.88rem">${escAttr(analysis.limitations || 'N/A')}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-primary);font-weight:600">可复现性</span><p style="margin:4px 0;font-size:0.88rem">${escAttr(analysis.reproducibility || 'N/A')}</p></div>
                ${analysis.relevance_to_profile ? `<div><span style="color:var(--accent-primary);font-weight:600">与研究方向的关系</span><p style="margin:4px 0;font-size:0.85rem;color:var(--text-2)">${escAttr(analysis.relevance_to_profile)}</p></div>` : ''}
            </div>`;
    });

    document.getElementById('modal-prev')?.addEventListener('click', () => navigateModal(-1));
    document.getElementById('modal-next')?.addEventListener('click', () => navigateModal(1));
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

export function closePaperModal() {
    document.getElementById('paper-modal').classList.remove('active');
    document.body.style.overflow = '';
}

// 注：profile 编辑入口已统一到订阅面板"研究方向"tab（subscriptions.js），
// 旧的 profile-modal（openProfileModal/saveProfile）已移除。
