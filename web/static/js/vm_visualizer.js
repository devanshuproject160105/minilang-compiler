/**
 * VM Debugger Visualizer: Interactive step debugger with animated stack,
 * environment variable tables, instruction pointer tracking, and console logging.
 */

class VMVisualizer {
  constructor(elements) {
    this.bytecodeContainer = document.getElementById(elements.bytecodeListId);
    this.stackContainer = document.getElementById(elements.stackDisplayId);
    this.varsContainer = document.getElementById(elements.varTableId);
    this.callStackContainer = document.getElementById(elements.callStackId);
    this.consoleContainer = document.getElementById(elements.consoleId);
    this.statusBadge = document.getElementById(elements.statusBadgeId);

    this.instructions = [];
    this.autoStepInterval = null;
    this.isAutoStepping = false;
  }

  setBytecode(instructions) {
    this.instructions = instructions || [];
    this._renderBytecodeList(0);
  }

  updateState(state) {
    if (!state) return;

    // Update Status Badge
    if (this.statusBadge) {
      this.statusBadge.innerText = state.status || 'READY';
      this.statusBadge.className = 'badge ' + (state.status === 'ERROR' ? 'failed' : state.status === 'FINISHED' ? 'success' : 'active');
    }

    // Highlight current IP
    this._highlightIP(state.ip);

    // Render Operand Stack
    this._renderStack(state.stack || []);

    // Render Variables
    this._renderVariables(state.variables || {});

    // Render Call Stack
    this._renderCallStack(state.call_stack || []);

    // Render Output
    this._renderOutput(state.output || [], state.error);

    // Stop auto-step if finished or errored
    if (state.status === 'FINISHED' || state.status === 'ERROR') {
      this.stopAutoStep();
    }
  }

  _renderBytecodeList(currentIp) {
    if (!this.bytecodeContainer) return;
    if (!this.instructions || this.instructions.length === 0) {
      this.bytecodeContainer.innerHTML = '<div class="empty-state" style="padding:20px;">No bytecode instructions loaded.</div>';
      return;
    }

    let html = '';
    this.instructions.forEach((instr, idx) => {
      const isActive = idx === currentIp;
      html += `
        <div id="bc-row-${idx}" class="bytecode-row ${isActive ? 'active' : ''}">
          <span style="color:var(--text-muted); width:40px;">${String(instr.ip).padStart(4, '0')}:</span>
          <span style="color:var(--accent-color); font-weight:bold; width:130px;">${instr.op}</span>
          <span style="flex:1; color:var(--text-bright);">${instr.arg1 !== null ? instr.arg1 : ''}${instr.arg2 !== null ? ', ' + instr.arg2 : ''}</span>
          ${instr.comment ? `<span style="color:var(--text-muted); font-size:0.75rem;">// ${instr.comment}</span>` : ''}
        </div>`;
    });
    this.bytecodeContainer.innerHTML = html;
  }

  _highlightIP(ip) {
    if (!this.bytecodeContainer) return;
    const prevActive = this.bytecodeContainer.querySelector('.bytecode-row.active');
    if (prevActive) prevActive.classList.remove('active');

    const nextActive = document.getElementById(`bc-row-${ip}`);
    if (nextActive) {
      nextActive.classList.add('active');
      nextActive.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }

  _renderStack(stack) {
    if (!this.stackContainer) return;
    if (stack.length === 0) {
      this.stackContainer.innerHTML = '<div class="empty-state">Stack is empty</div>';
      return;
    }

    let html = '';
    stack.forEach((val, idx) => {
      html += `
        <div class="stack-item">
          <span style="color:var(--text-muted); font-size:0.72rem; margin-right:8px;">[${idx}]</span>
          <span>${val}</span>
        </div>`;
    });
    this.stackContainer.innerHTML = html;
  }

  _renderVariables(variables) {
    if (!this.varsContainer) return;
    const keys = Object.keys(variables);
    if (keys.length === 0) {
      this.varsContainer.innerHTML = '<tr><td colspan="2" class="empty-state" style="padding:15px; text-align:center;">No variables allocated</td></tr>';
      return;
    }

    let html = '';
    keys.forEach(k => {
      html += `
        <tr>
          <td style="color:var(--cyan-color); font-weight:600;">${k}</td>
          <td style="color:var(--text-bright);">${variables[k]}</td>
        </tr>`;
    });
    this.varsContainer.innerHTML = html;
  }

  _renderCallStack(callStack) {
    if (!this.callStackContainer) return;
    if (callStack.length === 0) {
      this.callStackContainer.innerHTML = '<div style="padding:10px; color:var(--text-muted); font-size:0.8rem;">[Global / Main Frame]</div>';
      return;
    }

    let html = '';
    callStack.forEach((frame, idx) => {
      html += `
        <div style="background:var(--bg-tertiary); padding:6px 10px; border-radius:4px; margin-bottom:4px; font-size:0.8rem; border-left:3px solid var(--purple-color);">
          <strong style="color:var(--purple-color);">${frame.func_name}()</strong> (Return to IP: ${frame.return_ip})
        </div>`;
    });
    this.callStackContainer.innerHTML = html;
  }

  _renderOutput(output, error) {
    if (!this.consoleContainer) return;
    let text = output.join('\n');
    if (error) {
      text += (text ? '\n' : '') + `[RUNTIME ERROR]: ${error}`;
    }
    this.consoleContainer.innerText = text || '(No output yet)';
    this.consoleContainer.scrollTop = this.consoleContainer.scrollHeight;
  }

  stopAutoStep() {
    if (this.autoStepInterval) {
      clearInterval(this.autoStepInterval);
      this.autoStepInterval = null;
    }
    this.isAutoStepping = false;
    const btn = document.getElementById('btn-auto-step');
    if (btn) btn.innerHTML = '<i class="fas fa-play"></i> Auto Step';
  }
}
