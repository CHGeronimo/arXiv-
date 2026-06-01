// js/graph.js — force-directed knowledge graph

export async function loadGraph() {
    const resp = await fetch('/api/knowledge-graph');
    if (!resp.ok) return;
    const { nodes, edges } = await resp.json();
    renderGraph(nodes, edges);
}

function renderGraph(nodes, edges) {
    const svg = d3.select('#graph-svg');
    svg.selectAll('*').remove();
    // Derive dimensions from viewBox (responsive) rather than fixed width/height attributes
    const vb = svg.attr('viewBox');
    let w, h;
    if (vb) {
        const parts = vb.split(/[\s,]+/).map(Number);
        w = parts[2] || 960;
        h = parts[3] || 600;
    } else {
        const rect = svg.node().getBoundingClientRect();
        w = rect.width || 960;
        h = rect.height || 600;
    }

    const sim = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(edges).id(d => d.id).distance(80))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(w / 2, h / 2));

    const link = svg.append('g').selectAll('line').data(edges).join('line')
        .attr('stroke', 'var(--border-color)').attr('stroke-width', d => Math.min(d.weight, 5));

    const node = svg.append('g').selectAll('g').data(nodes).join('g').call(d3.drag()
        .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

    node.append('circle').attr('r', d => Math.max(8, d.size * 2))
        .attr('fill', 'var(--accent)').attr('opacity', 0.8);
    node.append('text').text(d => d.name.slice(0, 20)).attr('dy', -12)
        .attr('text-anchor', 'middle').attr('fill', 'var(--text-primary)').attr('font-size', '0.7rem');

    sim.on('tick', () => {
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });
}
