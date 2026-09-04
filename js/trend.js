// js/trend.js — trend radar with structured report rendering

const SECTION_META = {
  new_methods:     { title: '新方法涌现', icon: '◆', color: 'var(--success)',  bg: 'rgba(52,211,153,0.06)' },
  solved_problems: { title: '问题进展',   icon: '▲', color: 'var(--info)',     bg: 'rgba(96,165,250,0.06)' },
  controversies:   { title: '争议点',     icon: '●', color: 'var(--warning)',  bg: 'rgba(251,191,36,0.06)' },
  opportunities:   { title: '机会点',     icon: '★', color: '#a78bfa',         bg: 'rgba(167,139,250,0.06)' },
};

export async function loadTrendRadar(week) {
  const emptyEl = document.getElementById('trend-empty');
  const contentEl = document.getElementById('trend-content');
  if (!contentEl) return;

  if (emptyEl) {
    emptyEl.innerHTML = '<div class="spinner"></div><p style="margin-top:12px">正在加载趋势报告...</p>';
    emptyEl.style.display = '';
  }
  contentEl.innerHTML = '';

  // 历史周选择器（有历史数据时显示）
  const sel = document.getElementById('trend-week-select');
  if (sel && sel.dataset.bound !== '1') {
    sel.dataset.bound = '1';
    try {
      const listResp = await fetch('/api/trend-radars');
      const { weeks } = await listResp.json();
      if (weeks && weeks.length > 1) {
        sel.style.display = '';
        sel.innerHTML = weeks.map(w => `<option value="${w}">${w} 周</option>`).join('');
        sel.addEventListener('change', () => loadTrendRadar(sel.value));
      }
    } catch { /* 历史列表失败不影响最新报告 */ }
  }
  if (sel && week) sel.value = week;

  const url = week ? `/api/trend-radar/${week}` : '/api/trend-radar';
  const resp = await fetch(url);
  if (!resp.ok) {
    if (emptyEl) emptyEl.innerHTML = '<p>加载失败</p><p class="hint">请稍后重试</p>';
    return;
  }
  const { report } = await resp.json();

  if (!report) {
    if (emptyEl) {
      emptyEl.innerHTML = '<p>暂无趋势报告</p><p class="hint">点击"生成报告"创建本周趋势雷达</p>';
      emptyEl.style.display = '';
    }
    return;
  }

  if (emptyEl) emptyEl.style.display = 'none';
  renderReport(report);
}

function renderReport(r) {
  const el = document.getElementById('trend-content');
  const paperCount = r.paper_count || 0;
  const weekStart = r.week_start || '';

  // Metric row
  let html = `
    <div class="trend-metrics">
      <div class="trend-metric">
        <span class="trend-metric-value">${paperCount}</span>
        <span class="trend-metric-label">本周论文</span>
      </div>
      <div class="trend-metric">
        <span class="trend-metric-value">${weekStart}</span>
        <span class="trend-metric-label">报告周期</span>
      </div>
    </div>
  `;

  // Section cards
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
            ? '<ul class="trend-list">' + bullets.map(b => `<li>${b}</li>`).join('') + '</ul>'
            : `<p class="trend-paragraph">${content}</p>`}
        </div>
      </div>
    `;
  }
  html += '</div>';

  el.innerHTML = html;

  // Stagger animation
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
