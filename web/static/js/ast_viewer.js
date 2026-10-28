/**
 * Interactive Collapsible AST Tree Visualizer using D3.js v7.
 * Supports collapse/expand toggling, tooltips showing inferred types, and zoom/pan.
 */

class ASTViewer {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.tooltip = null;
    this.root = null;
    this.svg = null;
    this.g = null;
    this.treeLayout = null;
    this._initTooltip();
  }

  _initTooltip() {
    let tip = document.getElementById('ast-tooltip');
    if (!tip) {
      tip = document.createElement('div');
      tip.id = 'ast-tooltip';
      tip.className = 'd3-tooltip';
      document.body.appendChild(tip);
    }
    this.tooltip = tip;
  }

  render(astData) {
    if (!this.container) return;
    this.container.innerHTML = '';

    if (!astData) {
      this.container.innerHTML = '<div class="empty-state" style="padding: 40px; text-align: center;">No AST available. Compile a valid MiniLang program first.</div>';
      return;
    }

    const width = this.container.clientWidth || 700;
    const height = this.container.clientHeight || 500;

    const svg = d3.select(this.container)
      .append('svg')
      .attr('width', '100%')
      .attr('height', '100%')
      .attr('viewBox', [0, 0, width, height]);

    const g = svg.append('g').attr('transform', 'translate(80, 50)');

    // Zoom and pan
    const zoom = d3.zoom().scaleExtent([0.1, 3]).on('zoom', (event) => {
      g.attr('transform', event.transform);
    });
    svg.call(zoom);

    this.svg = svg;
    this.g = g;

    // Build hierarchy
    this.root = d3.hierarchy(astData, d => d.children);
    this.root.x0 = height / 2;
    this.root.y0 = 0;

    // Tree layout
    this.treeLayout = d3.tree().nodeSize([36, 180]);

    this._update(this.root);
  }

  _update(source) {
    const duration = 250;
    const nodes = this.root.descendants();
    const links = this.root.links();

    this.treeLayout(this.root);

    let left = this.root;
    let right = this.root;
    this.root.eachBefore(node => {
      if (node.x < left.x) left = node;
      if (node.x > right.x) right = node;
    });

    // --- NODES ---
    let i = 0;
    const node = this.g.selectAll('g.node')
      .data(nodes, d => d.id || (d.id = ++i));

    // Enter new nodes
    const nodeEnter = node.enter().append('g')
      .attr('class', 'node')
      .attr('transform', d => `translate(${source.y0 || 0},${source.x0 || 0})`)
      .on('click', (event, d) => {
        if (d.children) {
          d._children = d.children;
          d.children = null;
        } else if (d._children) {
          d.children = d._children;
          d._children = null;
        }
        this._update(d);
      })
      .on('mouseover', (event, d) => {
        const data = d.data;
        let html = `<strong>${data.name}</strong><br/>`;
        if (data.node_type) html += `Type: <em>${data.node_type}</em><br/>`;
        if (data.inferred_type) html += `Inferred: <span style="color:#61afef">${data.inferred_type}</span><br/>`;
        if (data.line) html += `Line: ${data.line}, Col: ${data.column}`;

        this.tooltip.innerHTML = html;
        this.tooltip.style.left = (event.pageX + 14) + 'px';
        this.tooltip.style.top = (event.pageY - 10) + 'px';
        this.tooltip.style.opacity = '1';
      })
      .on('mouseout', () => {
        this.tooltip.style.opacity = '0';
      });

    nodeEnter.append('circle')
      .attr('r', 6)
      .style('fill', d => d._children ? '#61afef' : '#2d3139')
      .style('stroke', '#61afef')
      .style('stroke-width', 2);

    nodeEnter.append('text')
      .attr('dy', '.35em')
      .attr('x', d => (d.children || d._children) ? -10 : 10)
      .attr('text-anchor', d => (d.children || d._children) ? 'end' : 'start')
      .text(d => d.data.name);

    // Transition nodes to their new position
    const nodeUpdate = node.merge(nodeEnter).transition().duration(duration)
      .attr('transform', d => `translate(${d.y},${d.x})`);

    nodeUpdate.select('circle')
      .attr('r', 6)
      .style('fill', d => d._children ? '#61afef' : '#2d3139');

    // Transition exiting nodes
    const nodeExit = node.exit().transition().duration(duration)
      .attr('transform', d => `translate(${source.y},${source.x})`)
      .remove();

    nodeExit.select('circle').attr('r', 1e-6);
    nodeExit.select('text').style('fill-opacity', 1e-6);

    // --- LINKS ---
    const link = this.g.selectAll('path.link')
      .data(links, d => d.target.id);

    const linkEnter = link.enter().insert('path', 'g')
      .attr('class', 'link')
      .attr('d', d => {
        const o = { x: source.x0 || 0, y: source.y0 || 0 };
        return this._diagonal(o, o);
      });

    link.merge(linkEnter).transition().duration(duration)
      .attr('d', d => this._diagonal(d.source, d.target));

    link.exit().transition().duration(duration)
      .attr('d', d => {
        const o = { x: source.x, y: source.y };
        return this._diagonal(o, o);
      })
      .remove();

    // Store old positions for smooth transitions
    nodes.forEach(d => {
      d.x0 = d.x;
      d.y0 = d.y;
    });
  }

  _diagonal(s, d) {
    return `M ${s.y} ${s.x}
            C ${(s.y + d.y) / 2} ${s.x},
              ${(s.y + d.y) / 2} ${d.x},
              ${d.y} ${d.x}`;
  }
}
