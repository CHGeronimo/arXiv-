// js/graph.js — force-directed knowledge graph with cluster coloring

function _esc(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

const CLUSTER_PALETTE = [
  '#818cf8', '#34d399', '#f472b6', '#fbbf24', '#60a5fa',
  '#a78bfa', '#fb923c', '#2dd4bf', '#e879f9', '#4ade80',
  '#f87171', '#38bdf8', '#c084fc', '#facc15', '#22d3ee',
  '#fb7185', '#a3e635', '#818cf8', '#f97316', '#2dd4bf',
  '#e11d48', '#06b6d4', '#84cc16', '#8b5cf6', '#ef4444',
  '#14b8a6', '#eab308', '#6366f1', '#ec4899', '#10b981',
];

let _graphZoom = null;

export async function loadGraph() {
  const emptyEl = document.getElementById('graph-empty');
  const layoutEl = document.getElementById('graph-layout');

  if (emptyEl) emptyEl.innerHTML = '<div class="spinner"></div><p style="margin-top:12px">正在加载图谱...</p>';
  if (emptyEl) emptyEl.style.display = '';
  if (layoutEl) layoutEl.style.display = 'none';

  let resp, data;
  try {
    resp = await fetch('/api/knowledge-graph');
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    data = await resp.json();
  } catch {
    if (emptyEl) emptyEl.innerHTML = '<p>加载失败</p><p class="hint">网络或服务异常，刷新重试</p>';
    return;
  }
  const { nodes, edges } = data;

  if (!nodes || nodes.length === 0) {
    if (emptyEl) {
      emptyEl.innerHTML = '<p>暂无知识图谱数据</p><p class="hint">先触发知识卡片提取和聚类，然后刷新图谱</p>';
      emptyEl.style.display = '';
    }
    if (layoutEl) layoutEl.style.display = 'none';
    return;
  }

  if (emptyEl) emptyEl.style.display = 'none';
  if (layoutEl) layoutEl.style.display = 'grid';

  // Reset detail panel
  const detailContent = document.getElementById('graph-detail-content');
  if (detailContent) detailContent.innerHTML = '<p class="graph-detail-hint">悬停节点查看详情</p>';
  const detailEl = document.getElementById('graph-detail');
  if (detailEl) detailEl.style.display = '';

  renderGraph(nodes, edges);
}

function renderGraph(nodes, edges) {
  const svg = d3.select('#graph-svg');
  svg.selectAll('*').remove();

  const vb = svg.attr('viewBox');
  let w, h;
  if (vb) {
    const parts = vb.split(/[\s,]+/).map(Number);
    w = parts[2] || 960; h = parts[3] || 600;
  } else {
    const rect = svg.node().getBoundingClientRect();
    w = rect.width || 960; h = rect.height || 600;
  }

  // Assign cluster color
  nodes.forEach((n, i) => { n.color = CLUSTER_PALETTE[i % CLUSTER_PALETTE.length]; });

  // Zoom + pan
  const g = svg.append('g');
  _graphZoom = d3.zoom()
    .scaleExtent([0.3, 4])
    .on('zoom', (e) => g.attr('transform', e.transform));
  svg.call(_graphZoom);

  // Defs for glow filter
  const defs = svg.append('defs');
  const glow = defs.append('filter').attr('id', 'node-glow');
  glow.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur');
  glow.append('feComposite').attr('in', 'SourceGraphic').attr('in2', 'blur').attr('operator', 'over');

  // Links
  const link = g.append('g').selectAll('line').data(edges).join('line')
    .attr('stroke', 'var(--border)').attr('stroke-width', d => Math.min(d.weight * 0.8, 4))
    .attr('stroke-opacity', 0.4);

  // Node groups
  const node = g.append('g').selectAll('g').data(nodes).join('g')
    .attr('class', 'graph-node')
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

  // Outer glow circle
  node.append('circle')
    .attr('r', d => Math.max(10, Math.sqrt(d.size) * 4))
    .attr('fill', d => d.color)
    .attr('opacity', 0.12)
    .attr('filter', 'url(#node-glow)');

  // Main circle
  node.append('circle')
    .attr('r', d => Math.max(6, Math.sqrt(d.size) * 2.5))
    .attr('fill', d => d.color)
    .attr('opacity', 0.85)
    .attr('stroke', d => d.color)
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.5);

  // Label
  node.append('text')
    .text(d => _truncate(d.name, 18))
    .attr('dy', d => -Math.max(8, Math.sqrt(d.size) * 2.5) - 4)
    .attr('text-anchor', 'middle')
    .attr('fill', 'var(--text-1)')
    .attr('font-size', '0.7rem')
    .attr('font-family', 'var(--font-body)')
    .attr('font-weight', 500);

  // Size badge (paper count)
  node.append('text')
    .text(d => d.size)
    .attr('dy', 4)
    .attr('text-anchor', 'middle')
    .attr('fill', 'var(--surface-0)')
    .attr('font-size', '0.6rem')
    .attr('font-family', 'var(--font-mono)')
    .attr('font-weight', 600);

  // Hover interaction
  node.on('mouseenter', (e, d) => {
    link.attr('stroke', l =>
      (l.source.id === d.id || l.target.id === d.id) ? d.color : 'var(--border)'
    ).attr('stroke-opacity', l =>
      (l.source.id === d.id || l.target.id === d.id) ? 0.7 : 0.1
    ).attr('stroke-width', l =>
      (l.source.id === d.id || l.target.id === d.id) ? Math.min(l.weight, 5) : Math.min(l.weight * 0.5, 2)
    );
    node.attr('opacity', n => (n.id === d.id || edges.some(e =>
      (e.source.id === d.id && e.target.id === n.id) ||
      (e.target.id === d.id && e.source.id === n.id)
    )) ? 1 : 0.25);
    _showDetail(d);
  }).on('mouseleave', () => {
    link.attr('stroke', 'var(--border)').attr('stroke-opacity', 0.4)
      .attr('stroke-width', d => Math.min(d.weight * 0.8, 4));
    node.attr('opacity', 1);
    _hideDetail();
  }).on('click', (e, d) => {
    e.stopPropagation();
    window._openClusterPapers?.(d.name);
  });

  // Simulation
  const sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(160).strength(0.15))
    .force('charge', d3.forceManyBody().strength(-400))
    .force('center', d3.forceCenter(w / 2, h / 2))
    .force('collision', d3.forceCollide().radius(d => Math.max(20, Math.sqrt(d.size) * 4)));

  sim.on('tick', () => {
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });
}

function _showDetail(d) {
  const el = document.getElementById('graph-detail-content');
  if (!el) return;
  const panel = document.getElementById('graph-detail');
  if (panel) panel.style.display = '';
  el.innerHTML = `
    <div class="graph-detail-header">
      <span class="graph-detail-dot" style="background:${d.color}"></span>
      <span class="graph-detail-name">${_esc(d.name)}</span>
    </div>
    ${d.domains && d.domains.length ? `
    <div class="graph-detail-stat">
      <span class="graph-detail-label">问题域</span>
      <span class="graph-detail-value">${_esc(d.domains.join('、'))}</span>
    </div>` : ''}
    <div class="graph-detail-stat">
      <span class="graph-detail-label">论文数</span>
      <span class="graph-detail-value">${d.size}</span>
    </div>
    ${d.keywords && d.keywords.length ? `
    <div class="graph-detail-kws">
      <span class="graph-detail-label">关键词</span>
      <div class="graph-detail-kw-list">
        ${d.keywords.map(k => `<span class="graph-detail-kw-tag">${_esc(k)}</span>`).join('')}
      </div>
    </div>` : ''}
    <button class="btn btn--primary" style="margin-top:12px;width:100%;font-size:0.78rem;padding:5px 0"
      data-cluster-drill="${String(d.name).replace(/"/g, '&quot;').replace(/</g, '&lt;')}">📄 查看论文列表（${d.size} 篇）</button>
  `;
  const drill = el.querySelector('[data-cluster-drill]');
  if (drill) drill.addEventListener('click', () => window._openClusterPapers?.(d.name));
}

function _hideDetail() {
  const el = document.getElementById('graph-detail-content');
  if (el) el.innerHTML = '<p class="graph-detail-hint">悬停节点查看详情</p>';
}

function _truncate(s, max) {
  return s.length > max ? s.slice(0, max - 1) + '…' : s;
}

// Expose zoom reset
window._graphZoomReset = () => {
  const svg = d3.select('#graph-svg');
  if (_graphZoom) svg.transition().duration(500).call(_graphZoom.transform, d3.zoomIdentity);
};
