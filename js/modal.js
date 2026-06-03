// js/modal.js — paper detail and profile modals

import { markRead, escAttr, showToast, setAllPapers, getFeedbackForPaper } from './state.js';
import { exportBibtex, fetchKnowledgeCard, fetchFulltextAnalysis, deletePaper } from './api.js';
import { renderPapers } from './render.js';

export function openPaperDetail(paper) {
    const wasRead = markRead(paper.id);
    if (wasRead) renderPapers();
    const modal = document.getElementById('paper-modal');
    const detail = document.getElementById('paper-detail');

    const aiTitle = (paper.AI || {}).title_zh || '';
    const titleZh = aiTitle || paper.title_zh || '';
    const titleEn = paper.title || '';
    const title = titleZh || titleEn;
    const origTitle = (titleZh && titleEn && titleZh !== titleEn) ? `<div style="color:var(--text-secondary);font-size:0.85rem;margin-top:4px">${titleEn}</div>` : '';
    const sourceBadge = paper.source === 'crossref'
        ? `<span class="source-badge crossref">${paper.journal_title || 'Journal'}</span>`
        : paper.source === 'dblp'
        ? `<span class="source-badge dblp">DBLP</span>`
        : paper.source === 'semantic_scholar'
        ? `<span class="source-badge s2">S2</span>`
        : `<span class="source-badge arxiv">arXiv</span>`;
    const venueInfo = paper.venue ? ` <span class="venue-badge">${paper.venue}</span>` : '';
    const ccfInfo = paper.ccf_tier ? ` <span class="ccf-badge ${window.ccfTierClass?.(paper.ccf_tier) || 'ccf-' + paper.ccf_tier}">${paper.ccf_tier}</span>` : '';
    const accInfo = paper.acceptance ? ` <span class="acc-badge ${paper.acceptance}">${paper.acceptance}</span>` : '';
    const citeInfo = paper.citation_count ? `<div style="margin-bottom:8px;font-size:0.85rem;color:var(--text-secondary)">&#9733; ${paper.citation_count} citations</div>` : '';

    const aiFields = paper.AI || {};
    const sections = [];
    const aiParts = [];
    if (aiFields.tldr) aiParts.push(`<b>TL;DR</b> ${aiFields.tldr}`);
    if (aiFields.motivation) aiParts.push(`<b>Motivation</b> ${aiFields.motivation}`);
    if (aiFields.method) aiParts.push(`<b>Method</b> ${aiFields.method}`);
    if (aiFields.result) aiParts.push(`<b>Result</b> ${aiFields.result}`);
    if (aiFields.conclusion) aiParts.push(`<b>Conclusion</b> ${aiFields.conclusion}`);
    if (aiParts.length) sections.push(`<h3>AI 解读</h3><p>${aiParts.join('<br><br>')}</p>`);

    if (!aiParts.length) {
        const fallbackParts = [];
        if (paper.tldr) fallbackParts.push(`<b>TL;DR</b> ${paper.tldr}`);
        if (paper.motivation) fallbackParts.push(`<b>Motivation</b> ${paper.motivation}`);
        if (paper.method) fallbackParts.push(`<b>Method</b> ${paper.method}`);
        if (paper.result) fallbackParts.push(`<b>Result</b> ${paper.result}`);
        if (paper.conclusion) fallbackParts.push(`<b>Conclusion</b> ${paper.conclusion}`);
        if (fallbackParts.length) sections.push(`<h3>解读</h3><p>${fallbackParts.join('<br><br>')}</p>`);
    }

    const summaryZh = aiFields.summary_zh || paper.summary_zh || '';
    if (summaryZh) sections.push(`<h3>中文摘要</h3><p>${summaryZh}</p>`);
    const abstractEn = paper.summary || '';
    if (abstractEn) sections.push(`<h3>Abstract</h3><p>${abstractEn}</p>`);
    if (!sections.length) sections.push(`<p style="color:var(--text-secondary)">暂无摘要</p>`);

    const codeUrl = paper.code_url || '';
    const codeStars = paper.code_stars ? ` (${paper.code_stars} stars)` : '';

    const fb = getFeedbackForPaper(paper.id);
    const userRating = fb.rating || '';
    const userRel = fb.relevance || 0;
    const userNov = fb.novelty || 0;
    const hasFeedback = userRating || userRel || userNov;

    detail.innerHTML = `
        <div class="paper-header">${sourceBadge}${venueInfo}${ccfInfo}${accInfo}
            <span class="paper-cat">${paper.published_date || ''}</span>
        </div>
        <h2 style="margin:12px 0">${title}</h2>
        ${origTitle}
        <p style="color:var(--text-secondary);font-size:0.85rem;margin-bottom:12px">
            ${(paper.authors || []).map(a => `<span class="author-link" data-author-name="${escAttr(a)}">${a}</span>`).join(', ')}
        </p>
        ${citeInfo}
        ${sections.join('')}
        <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap">
            ${paper.url ? `<a href="${paper.url}" target="_blank" class="follow-btn">论文链接</a>` : ''}
            ${paper.pdf ? `<a href="${paper.pdf}" target="_blank" class="follow-btn">PDF</a>` : ''}
            ${paper.doi ? `<a href="https://doi.org/${paper.doi}" target="_blank" class="follow-btn">DOI</a>` : ''}
            ${codeUrl ? `<a href="${codeUrl}" target="_blank" class="follow-btn" style="border-color:#22c55e;color:#22c55e">Code${codeStars}</a>` : ''}
            <button class="follow-btn" data-export-bibtex="${escAttr(paper.id)}">BibTeX</button>
            <button class="follow-btn ${userRating === 'like' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-action="like" style="border-color:#22c55e;color:#22c55e">${userRating === 'like' ? '★ 有用' : '有用'}</button>
            <button class="follow-btn ${userRating === 'dislike' ? 'voted' : ''}" data-feedback-id="${escAttr(paper.id)}" data-feedback-action="dislike" style="border-color:#ef4444;color:#ef4444">${userRating === 'dislike' ? '★ 没用' : '没用'}</button>
            <div class="modal-feedback-sliders" style="margin-top:12px">
                <div class="feedback-slider-row"><span class="feedback-label">相关性</span><input type="range" min="1" max="5" value="${userRel || 3}" class="feedback-slider" data-slider-type="relevance" data-slider-id="${escAttr(paper.id)}"><span class="feedback-val">${userRel || '-'}</span></div>
                <div class="feedback-slider-row"><span class="feedback-label">新颖性</span><input type="range" min="1" max="5" value="${userNov || 3}" class="feedback-slider" data-slider-type="novelty" data-slider-id="${escAttr(paper.id)}"><span class="feedback-val">${userNov || '-'}</span></div>
            </div>
            <button class="follow-btn" data-delete-id="${escAttr(paper.id)}" style="border-color:#ef4444;color:#ef4444;margin-left:auto">删除</button>
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
            <div style="margin:8px 0;padding:12px;background:var(--accent-bg);border-radius:8px">
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">Problem</span><p style="margin:4px 0;font-size:0.88rem">${card.problem || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">Method</span><p style="margin:4px 0;font-size:0.88rem">${card.method_extracted || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">Result</span><p style="margin:4px 0;font-size:0.88rem">${card.result_extracted || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">Keywords</span>
                    <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px">${(card.keywords || []).map(k => `<span style="padding:2px 8px;border-radius:3px;font-size:0.75rem;background:var(--badge-bg);color:var(--accent-light)">${k}</span>`).join('')}</div>
                </div>
                ${card.relation_to_profile ? `<div><span style="color:var(--accent-light);font-weight:600">Profile Relation</span><p style="margin:4px 0;font-size:0.85rem;color:var(--text-secondary)">${card.relation_to_profile}</p></div>` : ''}
            </div>`;
    });
    fetchFulltextAnalysis(paper.id).then(analysis => {
        if (!analysis) return;
        const el = document.getElementById('fulltext-analysis-section');
        if (!el) return;
        el.innerHTML = `
            <h3 style="margin-top:16px">正文深度分析</h3>
            <div style="margin:8px 0;padding:12px;background:var(--accent-bg);border-radius:8px">
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">方法实现</span><p style="margin:4px 0;font-size:0.88rem">${analysis.method_implementation || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">实验设计</span><p style="margin:4px 0;font-size:0.88rem">${analysis.experimental_design || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">关键结果</span><p style="margin:4px 0;font-size:0.88rem">${analysis.key_results_detail || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">局限性</span><p style="margin:4px 0;font-size:0.88rem">${analysis.limitations || 'N/A'}</p></div>
                <div style="margin-bottom:8px"><span style="color:var(--accent-light);font-weight:600">可复现性</span><p style="margin:4px 0;font-size:0.88rem">${analysis.reproducibility || 'N/A'}</p></div>
                ${analysis.relevance_to_profile ? `<div><span style="color:var(--accent-light);font-weight:600">与研究方向的关系</span><p style="margin:4px 0;font-size:0.85rem;color:var(--text-secondary)">${analysis.relevance_to_profile}</p></div>` : ''}
            </div>`;
    });

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

export function closePaperModal() {
    document.getElementById('paper-modal').classList.remove('active');
    document.body.style.overflow = '';
}

export async function openProfileModal() {
    try {
        const resp = await fetch('/api/profile');
        if (resp.ok) {
            const data = await resp.json();
            document.getElementById('profile-direction').value = data.direction || '';
            document.getElementById('profile-keywords').value = (data.keywords || []).join(', ');
            document.getElementById('profile-quality').value = data.quality_criteria || '';
        }
    } catch {}
    document.getElementById('profile-modal').classList.add('active');
}

export function closeProfileModal() {
    document.getElementById('profile-modal').classList.remove('active');
}

export async function saveProfile() {
    const direction = document.getElementById('profile-direction').value;
    const keywords = document.getElementById('profile-keywords').value.split(',').map(k => k.trim()).filter(k => k);
    const quality_criteria = document.getElementById('profile-quality').value;
    try {
        await fetch('/api/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ direction, keywords, quality_criteria }),
        });
        closeProfileModal();
    } catch (e) {
        console.error('Failed to save profile:', e);
    }
}
