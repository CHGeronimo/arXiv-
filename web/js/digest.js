// js/digest.js — daily digest page with a tiny offline markdown renderer

function _esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function _inline(t) {
    return t
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // 链接协议白名单：LLM 输出不可信，javascript: 等伪协议只保留文字
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (m, text, href) =>
            /^https?:\/\//i.test(href) || href.startsWith('#')
                ? `<a href="${href}" target="_blank" rel="noopener">${text}</a>`
                : text);
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
    _bindGenerateButton();
    const sel = document.getElementById('digest-date-select');
    if (!sel || sel.dataset.bound === '1') { if (sel?.value) loadDigest(sel.value); return; }
    sel.dataset.bound = '1';
    sel.addEventListener('change', () => loadDigest(sel.value));
    try {
        const resp = await fetch('/api/digests');
        const { digests } = await resp.json();
        if (!digests?.length) {
            document.getElementById('digest-empty').innerHTML =
                '<p>暂无简报</p><p class="hint">点击上方「生成今日简报」立即生成</p>';
            return;
        }
        sel.innerHTML = digests.map(d => `<option value="${d}">${d}</option>`).join('');
        await loadDigest(digests[0]);
    } catch {
        document.getElementById('digest-empty').innerHTML = '<p>加载日期列表失败</p>';
    }
}

/** 「生成今日简报」按钮：触发后台任务，轮询日期列表出现新日期即加载。
 * digest 任务不写 /api/jobs 状态，按"新生成日期出现"判定完成更稳。 */
function _bindGenerateButton() {
    const btn = document.getElementById('btn-gen-digest');
    if (!btn || btn.dataset.bound === '1') return;
    btn.dataset.bound = '1';
    btn.addEventListener('click', async () => {
        // 基线：日期集合 + 最新一期内容长度（重新生成同日期时无新日期，靠长度变化判定）
        const before = new Set();
        let baselineLen = -1;
        try {
            const r = await fetch('/api/digests');
            const list = (await r.json()).digests || [];
            list.forEach(d => before.add(d));
            if (list[0]) {
                const d = await fetch(`/api/digest/${list[0]}`);
                if (d.ok) baselineLen = (await d.text()).length;
            }
        } catch { /* 起点拿不到也能工作 */ }
        btn.disabled = true;
        try {
            const resp = await fetch('/api/trigger/digest', { method: 'POST' });
            if (!resp.ok) { showToast?.('简报触发失败'); btn.disabled = false; return; }
        } catch { showToast?.('简报触发失败'); btn.disabled = false; return; }
        btn.disabled = true;
        const original = btn.textContent;
        btn.textContent = '生成中…（约1-2分钟）';
        const t0 = Date.now();
        const timer = setInterval(async () => {
            try {
                const r = await fetch('/api/digests');
                const list = (await r.json()).digests || [];
                const fresh = list.filter(d => !before.has(d));
                let regen = false;
                if (!fresh.length && list[0]) {
                    const d = await fetch(`/api/digest/${list[0]}`);
                    if (d.ok && baselineLen >= 0 && (await d.text()).length !== baselineLen) regen = true;
                }
                if (fresh.length || regen || Date.now() - t0 > 180000) {
                    clearInterval(timer);
                    btn.disabled = false;
                    btn.textContent = original;
                    if (!fresh.length && !regen) return;
                    const target = fresh[0] || list[0];
                    const sel = document.getElementById('digest-date-select');
                    sel.innerHTML = list.map(d => `<option value="${d}">${d}</option>`).join('');
                    sel.value = target;
                    loadDigest(target);
                }
            } catch { /* 瞬时失败继续轮询 */ }
        }, 3000);
    });
}
