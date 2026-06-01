// js/trend.js — trend radar rendering

export async function loadTrendRadar() {
    const resp = await fetch('/api/trend-radar');
    if (!resp.ok) return;
    const { report } = await resp.json();
    const el = document.getElementById('trend-content');
    if (!el) return;
    if (!report) { el.innerHTML = '<p style="color:var(--text-secondary)">暂无趋势报告。点击"生成报告"触发。</p>'; return; }
    const sections = [
        { title: '新方法涌现', content: report.new_methods, color: '#22c55e' },
        { title: '问题进展', content: report.solved_problems, color: '#3b82f6' },
        { title: '争议点', content: report.controversies, color: '#eab308' },
        { title: '机会点', content: report.opportunities, color: '#a855f7' },
    ];
    el.innerHTML = `<p style="color:var(--text-muted);margin-bottom:12px">周报: ${report.week_start} | ${report.paper_count} 篇论文</p>`
        + sections.map(s => `<div style="margin-bottom:12px"><h3 style="color:${s.color}">${s.title}</h3><p style="font-size:0.88rem;white-space:pre-wrap">${s.content}</p></div>`).join('');
}
