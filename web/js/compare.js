// js/compare.js — pick 2-3 papers and compare them side by side
import { fetchFullPaper, fetchKnowledgeCard } from './api.js';
import { escAttr, showToast } from './state.js';

const MAX = 3;
const selected = [];  // [{id, title}] — 刷新自动恢复（localStorage 持久化）
try {
    const saved = JSON.parse(localStorage.getItem('compareSel') || '[]');
    if (Array.isArray(saved)) selected.push(...saved.filter(x => x && x.id));
} catch { /* 损坏即弃 */ }
const _persist = () => { try { localStorage.setItem('compareSel', JSON.stringify(selected)); } catch {} };

export function isSelected(id) {
    return selected.some(p => p.id === id);
}

export function toggleCompare(paper) {
    const i = selected.findIndex(p => p.id === paper.id);
    if (i >= 0) {
        selected.splice(i, 1);
    } else {
        if (selected.length >= MAX) {
            showToast(`最多对比 ${MAX} 篇，先取消一篇`);
            return false;
        }
        selected.push({ id: paper.id, title: escAttr(paper.title || paper.id) });
    }
    _persist();
    _updateBar();
    _refreshButtons(paper.id);
    return true;
}

export function clearCompare() {
    const ids = selected.map(p => p.id);
    selected.length = 0;
    _updateBar();
    ids.forEach(_refreshButtons);
    _persist();
}

function _refreshButtons(id) {
    document.querySelectorAll(`[data-compare-id="${CSS.escape(id)}"]`).forEach(btn => {
        btn.classList.toggle('active', isSelected(id));
    });
}

function _updateBar() {
    const bar = document.getElementById('compare-bar');
    if (!bar) return;
    bar.style.display = selected.length ? 'flex' : 'none';
    document.getElementById('compare-count').textContent = `已选 ${selected.length}/${MAX} 篇`;
}

export async function openCompare() {
    if (selected.length < 2) {
        showToast('请至少选择 2 篇论文（卡片上的 ⇄ 按钮）');
        return;
    }
    const modal = document.getElementById('compare-modal');
    const content = document.getElementById('compare-content');
    content.innerHTML = '<div class="spinner"></div>';
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    const papers = await Promise.all(selected.map(async sel => {
        const [full, card] = await Promise.all([fetchFullPaper(sel.id), fetchKnowledgeCard(sel.id)]);
        return { ...sel, ...(full || {}), card: card || null };
    }));

    const row = (label, get) => {
        const cells = papers.map(p => `<td>${get(p) ?? '—'}</td>`).join('');
        return `<tr><th>${label}</th>${cells}</tr>`;
    };
    const ai = (p) => p.AI || {};
    content.innerHTML = `
        <div class="compare-table-wrap"><table class="compare-table">
            ${row('标题', p => escAttr(p.title || ''))}
            ${row('来源/年份', p => `${escAttr(p.source || '')} · ${p.published_date || ''}`)}
            ${row('推荐/评分', p => {
                const a = ai(p);
                return a.recommendation ? `${a.recommendation} · R${a.relevance_score ?? '-'} / Q${a.quality_score ?? '-'}` : '';
            })}
            ${row('TLDR', p => escAttr(ai(p).tldr || ''))}
            ${row('问题', p => escAttr(p.card?.problem || ai(p).motivation || ''))}
            ${row('方法', p => escAttr(p.card?.method_extracted || ai(p).method || ''))}
            ${row('结果', p => escAttr(p.card?.result_extracted || ai(p).result || ''))}
            ${row('与方向关系', p => escAttr(p.card?.relation_to_profile || ''))}
            ${row('引用数', p => String(p.citation_count ?? '0'))}
            ${row('代码', p => p.code_url ? `<a href="${p.code_url}" target="_blank" rel="noopener">${escAttr(p.code_url.split('/').slice(-2).join('/'))}</a>` : '')}
        </table></div>`;
}

export function closeCompare() {
    document.getElementById('compare-modal')?.classList.remove('active');
    document.body.style.overflow = '';
}
