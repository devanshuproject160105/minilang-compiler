/**
 * IR Diff Visualizer: Compares unoptimized vs optimized Three-Address Code (TAC)
 * and displays rule firing telemetry with color-coded diff badges.
 */

class IRDiffViewer {
  constructor(containerId, ruleLogsContainerId) {
    this.container = document.getElementById(containerId);
    this.ruleLogsContainer = document.getElementById(ruleLogsContainerId);
  }

  render(rawIr, optimizedIr, optimizationLogs) {
    if (!this.container) return;

    if (!rawIr || rawIr.length === 0) {
      this.container.innerHTML = '<div class="empty-state" style="padding: 40px; text-align: center;">No IR generated. Compile a valid MiniLang program first.</div>';
      if (this.ruleLogsContainer) this.ruleLogsContainer.innerHTML = '';
      return;
    }

    // Build raw text sets to identify modified or removed lines
    const optTexts = new Set((optimizedIr || []).map(i => i.text));
    const rawTexts = new Set(rawIr.map(i => i.text));

    let rawHtml = '<div class="ir-panel"><div class="pane-header"><span>Raw TAC IR</span><span class="badge">' + rawIr.length + ' instrs</span></div><div class="ir-code">';
    rawIr.forEach((instr, idx) => {
      const isRemoved = !optTexts.has(instr.text);
      const lineClass = isRemoved ? 'ir-line removed' : 'ir-line';
      rawHtml += `<div class="${lineClass}"><span style="color:var(--text-muted);width:36px;user-select:none;">${idx}:</span> <span>${this._escape(instr.text)}</span></div>`;
    });
    rawHtml += '</div></div>';

    let optHtml = '<div class="ir-panel"><div class="pane-header"><span>Optimized TAC IR</span><span class="badge" style="color:var(--success-color);">' + (optimizedIr ? optimizedIr.length : 0) + ' instrs</span></div><div class="ir-code">';
    (optimizedIr || []).forEach((instr, idx) => {
      const isChanged = !rawTexts.has(instr.text);
      const lineClass = isChanged ? 'ir-line changed' : 'ir-line';
      optHtml += `<div class="${lineClass}"><span style="color:var(--text-muted);width:36px;user-select:none;">${idx}:</span> <span>${this._escape(instr.text)}</span></div>`;
    });
    optHtml += '</div></div>';

    this.container.innerHTML = rawHtml + optHtml;

    // Render rule firings
    if (this.ruleLogsContainer) {
      if (!optimizationLogs || optimizationLogs.length === 0) {
        this.ruleLogsContainer.innerHTML = '<div style="padding:10px; color:var(--text-muted); font-size:0.8rem;">No optimization rules fired (code already canonical or trivial).</div>';
      } else {
        let logsHtml = '<div style="padding: 8px 12px; font-size: 0.82rem;"><strong>Fired Optimization Rules (' + optimizationLogs.length + '):</strong><div style="margin-top:6px; display:flex; flex-direction:column; gap:6px;">';
        optimizationLogs.forEach(log => {
          logsHtml += `
            <div style="background:var(--bg-tertiary); padding:6px 10px; border-radius:4px; border:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <span class="rule-badge">${log.rule}</span>
                <span style="margin-left:8px; font-family:var(--font-mono); font-size:0.78rem; color:var(--text-bright);">${this._escape(log.description)}</span>
              </div>
              <div style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted);">
                <code>${this._escape(log.original_text)}</code> &rarr; <code style="color:var(--success-color);">${this._escape(log.optimized_text)}</code>
              </div>
            </div>`;
        });
        logsHtml += '</div></div>';
        this.ruleLogsContainer.innerHTML = logsHtml;
      }
    }
  }

  _escape(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}
