// js/trend.js — trend radar rendering

export async function loadTrendRadar() {
    const emptyEl = document.getElementById('trend-empty');
    const contentEl = document.getElementById('trend-content');
    if (!contentEl) return;

    // Show loading state
    if (emptyEl) {
        emptyEl.innerHTML = '<div class="spinner"></div><p style="margin-top:12px">正在加载趋势报告...</p>';
        emptyEl.style.display = '';
    }
    contentEl.innerHTML = '';

    const resp = await fetch('/api/trend-radar');
    if (!resp.ok) {
        if (emptyEl) {
            emptyEl.innerHTML = '<p>加载失败</p><p class="hint">请稍后重试</p>';
        }
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

    // Hide empty state, render report
    if (emptyEl) emptyEl.style.display = 'none';

    const sections = [
        { title: '新方法涌现', content: report.new_methods, color: '#22c55e' },
        { title: '问题进展', content: report.solved_problems, color: '#3b82f6' },
        { title: '争议点', content: report.controversies, color: '#eab308' },
        { title: '机会点', content: report.opportunities, color: '#a855f7' },
    ];
    contentEl.innerHTML = `<p style="color:var(--text-3);margin-bottom:12px">周报: ${report.week_start} | ${report.paper_count} 篇论文</p>`
        + sections.map(s => `<div style="margin-bottom:12px"><h3 style="color:${s.color}">${s.title}</h3><p style="font-size:0.88rem;white-space:pre-wrap">${s.content}</p></div>`).join('');
}
