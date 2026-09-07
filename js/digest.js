// js/digest.js — daily digest page with a tiny offline markdown renderer

function _esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function _inline(t) {
    return t
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}

/** Render the markdown subset the digest LLM produces: headers, bold/italic,
 * links, bullet/numbered lists, hr, GFM tables, paragraphs. No external lib. */
export function renderMarkdown(src) {
    const lines = _esc(src).split('\n');
    let html = '';
    let inList = false;

    const isTableRow = (l) => /^\|.*\|$/.test(l);
    const isSepRow = (l) => /^\|[\s:\-|]+\|$/.test(l) && l.includes('-');
    const parseRow = (l) => l.replace(/^\||\|$/g, '').split('|').map(c => _inline(c.trim()));

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // GFM 表格：表头行 + 分隔行 + 数据行
        if (isTableRow(line) && i + 1 < lines.length && isSepRow(lines[i + 1].trim())) {
            const head = parseRow(line);
            let j = i + 2;
            const bodyRows = [];
            while (j < lines.length && isTableRow(lines[j].trim())) {
                bodyRows.push(parseRow(lines[j].trim()));
                j++;
            }
            html += `<table class="digest-table"><thead><tr>${head.map(h => `<th>${h}</th>`).join('')}</tr></thead>` +
                `<tbody>${bodyRows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
            i = j - 1;
            continue;
        }

        const bullet = line.match(/^[-*]\s+(.*)/);
        const num = line.match(/^\d+[.)]\s+(.*)/);
        if (bullet || num) {
            if (!inList) { html += '<ul class="digest-list">'; inList = true; }
            html += `<li>${_inline((bullet || num)[1])}</li>`;
            continue;
        }
        if (inList) { html += '</ul>'; inList = false; }
        const h = line.match(/^(#{1,4})\s+(.*)/);
        if (h) {
            const lvl = Math.min(h[1].length + 1, 5);
            html += `<h${lvl} class="digest-h">${_inline(h[2])}</h${lvl}>`;
            continue;
        }
        if (/^---+$/.test(line)) { html += '<hr>'; continue; }
        if (!line) continue;
        html += `<p>${_inline(line)}</p>`;
    }
    if (inList) html += '</ul>';
    return html;
}

export async function loadDigest(dateStr) {
    const emptyEl = document.getElementById('digest-empty');
    const contentEl = document.getElementById('digest-content');
    if (!contentEl) return;
    emptyEl.style.display = '';
    emptyEl.innerHTML = '<div class="spinner"></div><p style="margin-top:12px">正在加载简报...</p>';
    contentEl.style.display = 'none';
    try {
        const resp = await fetch(`/api/digest/${dateStr}`);
        if (!resp.ok) throw new Error('not found');
        const md = await resp.text();
        contentEl.innerHTML = renderMarkdown(md);
        contentEl.style.display = '';
        emptyEl.style.display = 'none';
    } catch {
        emptyEl.innerHTML = `<p>无 ${dateStr} 的简报</p><p class="hint">简报随凌晨自动跑批生成</p>`;
    }
}

export async function initDigestPage() {
    const sel = document.getElementById('digest-date-select');
    if (!sel || sel.dataset.bound === '1') { if (sel?.value) loadDigest(sel.value); return; }
    sel.dataset.bound = '1';
    sel.addEventListener('change', () => loadDigest(sel.value));
    try {
        const resp = await fetch('/api/digests');
        const { digests } = await resp.json();
        if (!digests?.length) {
            document.getElementById('digest-empty').innerHTML =
                '<p>暂无简报</p><p class="hint">简报每天凌晨随自动跑批生成</p>';
            return;
        }
        sel.innerHTML = digests.map(d => `<option value="${d}">${d}</option>`).join('');
        await loadDigest(digests[0]);
    } catch {
        document.getElementById('digest-empty').innerHTML = '<p>加载日期列表失败</p>';
    }
}
