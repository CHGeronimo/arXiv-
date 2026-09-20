// js/trend.js — weekly/monthly trend radar with history browsers
import { showToast , escAttr} from './state.js';

const SECTION_META = {
  new_methods:     { title: '新方法涌现', icon: '◆', color: 'var(--success)',  bg: 'rgba(52,211,153,0.06)' },
  solved_problems: { title: '问题进展',   icon: '▲', color: 'var(--info)',     bg: 'rgba(96,165,250,0.06)' },
  controversies:   { title: '争议点',     icon: '●', color: 'var(--warning)',  bg: 'rgba(251,191,36,0.06)' },
  opportunities:   { title: '机会点',     icon: '★', color: '#a78bfa',         bg: 'rgba(167,139,250,0.06)' },
};

let _scope = 'weekly';

export function currentTrendScope() { return _scope; }

function _applyScopeUI() {
  const wBtn = document.getElementById('trend-scope-weekly');
  const mBtn = document.getElementById('trend-scope-monthly');
  const wSel = document.getElementById('trend-week-select');
  const mSel = document.getElementById('trend-month-select');
  const gen = document.getElementById('btn-generate-trend');
  wBtn?.classList.toggle('active', _scope === 'weekly');
  mBtn?.classList.toggle('active', _scope === 'monthly');
  if (wSel) wSel.style.display = _scope === 'weekly' ? '' : 'none';
  if (mSel) mSel.style.display = _scope === 'monthly' ? '' : 'none';
  if (gen) gen.textContent = _scope === 'weekly' ? '生成周报' : '生成月报';
}

function _bindOnce() {
  const page = document.getElementById('trend-page');
  if (!page || page.dataset.bound === '1') return;
  page.dataset.bound = '1';
  document.getElementById('trend-scope-weekly')?.addEventListener('click', () => { _scope = 'weekly'; _applyScopeUI(); loadTrendRadar(); });
  document.getElementById('trend-scope-monthly')?.addEventListener('click', () => { _scope = 'monthly'; _applyScopeUI(); loadTrendRadar(); });
  document.getElementById('trend-week-select')?.addEventListener('change', (e) => loadTrendRadar(e.target.value));
  document.getElementById('trend-month-select')?.addEventListener('change', (e) => loadTrendRadar(e.target.value));
  document.getElementById('btn-generate-trend')?.addEventListener('click', generateTrend);
}

async function _fillSelectors() {
  const wSel = document.getElementById('trend-week-select');
  const mSel = document.getElementById('trend-month-select');
  if (!wSel || !mSel || wSel.dataset.loaded === '1') return;
  try {
    const resp = await fetch('/api/trend-radars');
    const { weeks = [], months = [] } = await resp.json();
    if (weeks.length) {
      wSel.style.display = '';
      wSel.innerHTML = weeks.map(w => `<option value="${w}">${w} 周</option>`).join('');
    }
    if (months.length) {
      mSel.style.display = '';
      mSel.innerHTML = months.map(m => `<option value="${m}">${m} 月</option>`).join('');
    }
    wSel.dataset.loaded = '1';
  } catch { /* 历史列表失败不影响最新报告 */ }
}

export async function loadTrendRadar(key) {
  const emptyEl = document.getElementById('trend-empty');
  const contentEl = document.getElementById('trend-content');
  if (!contentEl) return;
  _bindOnce();
  _applyScopeUI();
  _fillSelectors();

  if (emptyEl) {
    emptyEl.innerHTML = '<div class="spinner"></div><p style="margin-top:12px">正在加载趋势报告...</p>';
    emptyEl.style.display = '';
  }
  contentEl.innerHTML = '';

  const url = key ? `/api/trend-radar/${key}` : `/api/trend-radar?scope=${_scope}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    if (emptyEl) emptyEl.innerHTML = '<p>加载失败</p><p class="hint">请稍后重试</p>';
    return;
  }
  const { report } = await resp.json();

  if (!report) {
    if (emptyEl) {
      emptyEl.innerHTML = `<p>暂无${_scope === 'weekly' ? '周' : '月'}报</p><p class="hint">点击"生成${_scope === 'weekly' ? '周' : '月'}报"创建（自动任务也会在每周一/每月1日沉淀）</p>`;
      emptyEl.style.display = '';
    }
    return;
  }

  if (emptyEl) emptyEl.style.display = 'none';
  renderReport(report);
}

export async function generateTrend() {
  const btn = document.getElementById('btn-generate-trend');
  const orig = btn?.innerHTML;
  if (btn) { btn.disabled = true; btn.innerHTML = '⏳ 生成中...'; }
  const emptyEl = document.getElementById('trend-empty');
  const contentEl = document.getElementById('trend-content');
  if (emptyEl) { emptyEl.style.display = ''; emptyEl.innerHTML = '<div class="spinner"></div><p style="margin-top:12px">AI 正在分析论文（思考模式约 1-3 分钟）...</p>'; }
  if (contentEl) contentEl.innerHTML = '';
  try {
    const resp = await fetch('/api/trigger/trend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope: _scope }),
    });
    if (!resp.ok) throw new Error();
  } catch {
    showToast('触发失败，请稍后重试');
    if (btn) { btn.disabled = false; btn.innerHTML = orig; }
    return;
  }
  let tries = 0;
  const poll = setInterval(async () => {
    tries++;
    try {
      const resp = await fetch('/api/jobs');
      if (!resp.ok) return;
      const status = await resp.json();
      const t = status.trend;
      if (!t || t.status === 'running') {
        if (tries > 110) { clearInterval(poll); finish('超时，请稍后刷新查看'); }
        return;
      }
      clearInterval(poll);
      finish(t.status === 'error' ? `生成失败: ${t.message || ''}` : (t.message || '生成完成'));
    } catch { /* 网络抖动继续轮询 */ }
  }, 3000);
  function finish(msg) {
    if (btn) { btn.disabled = false; btn.innerHTML = orig; }
    showToast(msg, 4000);
    document.getElementById('trend-week-select')?.removeAttribute('data-loaded');
    loadTrendRadar();
  }
}

function renderReport(r) {
  const el = document.getElementById('trend-content');
  const paperCount = r.paper_count || 0;
  const periodStart = r.week_start || '';
  const periodLabel = r.period_type === 'monthly' ? `${periodStart} 月` : `${periodStart} 周`;

  let html = `
    <div class="trend-metrics">
      <div class="trend-metric">
        <span class="trend-metric-value">${paperCount}</span>
        <span class="trend-metric-label">论文数</span>
      </div>
      <div class="trend-metric">
        <span class="trend-metric-value">${periodLabel}</span>
        <span class="trend-metric-label">报告周期</span>
      </div>
    </div>
  `;

  const sections = ['new_methods', 'solved_problems', 'controversies', 'opportunities'];
  html += '<div class="trend-grid">';
  for (const key of sections) {
    const meta = SECTION_META[key];
    const content = r[key];
    if (!content) continue;
    const bullets = _parseBullets(content);
    html += `
      <div class="trend-card" style="border-left:3px solid ${meta.color}; background:${meta.bg}">
        <div class="trend-card-header">
          <span class="trend-card-icon" style="color:${meta.color}">${meta.icon}</span>
          <span class="trend-card-title">${meta.title}</span>
        </div>
        <div class="trend-card-body">
          ${bullets.length > 0
            ? '<ul class="trend-list">' + bullets.map(b => `<li>${escAttr(b)}</li>`).join('') + '</ul>'
            : `<p class="trend-paragraph">${escAttr(content)}</p>`}
        </div>
      </div>
    `;
  }
  html += '</div>';

  el.innerHTML = html;

  el.querySelectorAll('.trend-card').forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(12px)';
    card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
    setTimeout(() => { card.style.opacity = '1'; card.style.transform = 'translateY(0)'; }, 80 * i);
  });
}

function _parseBullets(text) {
  if (!text) return [];
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  if (lines.length <= 1) return [];
  return lines.map(l => l.replace(/^[-•*]\s*/, '').replace(/^\d+[.)]\s*/, ''));
}
