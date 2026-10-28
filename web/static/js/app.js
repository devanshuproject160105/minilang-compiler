/**
 * Main Application Orchestrator for MiniLang Visual Compiler Pipeline.
 */

document.addEventListener('DOMContentLoaded', async () => {
  // DOM Elements
  const codeEditor = document.getElementById('code-editor');
  const lineNumbers = document.getElementById('line-numbers');
  const exampleSelect = document.getElementById('example-select');
  const errorBanner = document.getElementById('error-banner');
  const errorMessage = document.getElementById('error-message');
  const errorTitle = document.getElementById('error-title');

  // Toolbar Buttons
  const btnCompile = document.getElementById('btn-compile');
  const btnRun = document.getElementById('btn-run');
  const btnStep = document.getElementById('btn-step');
  const btnAutoStep = document.getElementById('btn-auto-step');
  const btnResetVM = document.getElementById('btn-reset-vm');

  // AI Buttons
  const btnExplainError = document.getElementById('btn-explain-error');
  const btnExplainStage = document.getElementById('btn-explain-stage');
  const btnAiGenerate = document.getElementById('btn-ai-generate');
  const btnOptimizationHints = document.getElementById('btn-opt-hints');

  // Modals
  const aiModal = document.getElementById('ai-modal');
  const aiModalTitle = document.getElementById('ai-modal-title');
  const aiModalBody = document.getElementById('ai-modal-body');
  const btnCloseModal = document.getElementById('btn-close-modal');

  // Stage steps
  const stageSteps = document.querySelectorAll('.stage-step');
  const tabPanes = document.querySelectorAll('.tab-pane');

  // Initialize visualizer components
  const astViewer = new ASTViewer('ast-tree-container');
  const irDiffViewer = new IRDiffViewer('ir-diff-view', 'ir-rule-logs');
  const vmVisualizer = new VMVisualizer({
    bytecodeListId: 'vm-bytecode-list',
    stackDisplayId: 'vm-stack-display',
    varTableId: 'vm-var-table-body',
    callStackId: 'vm-call-stack',
    consoleId: 'vm-console-output',
    statusBadgeId: 'vm-status-badge'
  });

  let currentPipelineResult = null;
  let currentActiveStage = 'tokens';
  let examplesData = [];

  // 1. Sync line numbers with textarea
  function updateLineNumbers(errorLine = null) {
    const lines = codeEditor.value.split('\n');
    let html = '';
    for (let i = 1; i <= lines.length; i++) {
      if (errorLine && i === errorLine) {
        html += `<div class="error-marker" title="Error at line ${i}">&gt; ${i}</div>`;
      } else {
        html += `<div>${i}</div>`;
      }
    }
    lineNumbers.innerHTML = html;
  }

  codeEditor.addEventListener('input', () => updateLineNumbers());
  codeEditor.addEventListener('scroll', () => {
    lineNumbers.scrollTop = codeEditor.scrollTop;
  });

  // Handle Tab key in editor
  codeEditor.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = codeEditor.selectionStart;
      const end = codeEditor.selectionEnd;
      codeEditor.value = codeEditor.value.substring(0, start) + '    ' + codeEditor.value.substring(end);
      codeEditor.selectionStart = codeEditor.selectionEnd = start + 4;
      updateLineNumbers();
    }
  });

  // 2. Load examples from API
  try {
    const res = await API.fetchExamples();
    examplesData = res.examples || [];
    exampleSelect.innerHTML = '<option value="" disabled selected>Select an example program...</option>';
    examplesData.forEach(ex => {
      const opt = document.createElement('option');
      opt.value = ex.id;
      opt.innerText = ex.title || ex.filename;
      exampleSelect.appendChild(opt);
    });

    if (examplesData.length > 0) {
      exampleSelect.value = examplesData[0].id;
      codeEditor.value = examplesData[0].code;
      updateLineNumbers();
    }
  } catch (err) {
    console.error('Failed to load examples:', err);
  }

  exampleSelect.addEventListener('change', (e) => {
    const found = examplesData.find(ex => ex.id === e.target.value);
    if (found) {
      codeEditor.value = found.code;
      updateLineNumbers();
      hideError();
    }
  });

  // 3. Tab & Stage Switching
  function switchTab(stageName) {
    currentActiveStage = stageName;
    stageSteps.forEach(step => {
      step.classList.toggle('active', step.dataset.stage === stageName);
    });

    tabPanes.forEach(pane => {
      pane.classList.toggle('active', pane.id === `tab-${stageName}`);
    });

    // If switching to AST, trigger re-render to fit container
    if (stageName === 'ast' && currentPipelineResult && currentPipelineResult.ast) {
      astViewer.render(currentPipelineResult.ast);
    }
  }

  stageSteps.forEach(step => {
    step.addEventListener('click', () => switchTab(step.dataset.stage));
  });

  // 4. Update Pipeline Stage Status Bar
  function updatePipelineStages(stages, firstError) {
    if (!stages) return;

    stageSteps.forEach(step => {
      const st = step.dataset.stage;
      const status = stages[st] || 'pending';
      step.classList.remove('success', 'failed', 'active');
      const icon = step.querySelector('.stage-icon');

      if (status === 'success') {
        step.classList.add('success');
        if (icon) icon.className = 'fas fa-check-circle stage-icon';
      } else if (status === 'failed') {
        step.classList.add('failed');
        if (icon) icon.className = 'fas fa-times-circle stage-icon';
      } else {
        if (icon) icon.className = 'fas fa-circle-notch stage-icon';
      }
    });

    // Highlight current active tab
    const activeStep = document.querySelector(`.stage-step[data-stage="${currentActiveStage}"]`);
    if (activeStep) activeStep.classList.add('active');

    if (firstError) {
      showError(firstError);
      // Automatically switch to the failing stage tab
      if (firstError.stage) {
        switchTab(firstError.stage);
      }
    } else {
      hideError();
    }
  }

  function showError(err) {
    errorBanner.classList.add('visible');
    errorTitle.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Error in ${err.stage ? err.stage.toUpperCase() : 'COMPILER'} (Line ${err.line || 0}, Col ${err.column || 0})`;
    errorMessage.innerText = err.message;
    updateLineNumbers(err.line);
  }

  function hideError() {
    errorBanner.classList.remove('visible');
    updateLineNumbers(null);
  }

  // 5. Populate Tabs Data
  function populateTabs(result) {
    currentPipelineResult = result;

    // Tokens Table
    const tokensBody = document.getElementById('tokens-table-body');
    if (tokensBody && result.tokens) {
      let html = '';
      result.tokens.forEach((t, i) => {
        html += `
          <tr>
            <td style="color:var(--text-muted);">${i}</td>
            <td><span class="token-tag">${t.type}</span></td>
            <td><code>${escapeHtml(t.lexeme)}</code></td>
            <td>${t.line}</td>
            <td>${t.column}</td>
          </tr>`;
      });
      tokensBody.innerHTML = html;
    }

    // AST Tree
    if (result.ast) {
      astViewer.render(result.ast);
    }

    // Symbol Table Scopes
    const symContainer = document.getElementById('symbol-table-container');
    if (symContainer && result.symbol_table) {
      symContainer.innerHTML = renderSymbolTableHierarchy(result.symbol_table);
    }

    // IR & Diff
    irDiffViewer.render(result.ir, result.optimized_ir, result.optimization_logs);

    // Bytecode Table
    const bcBody = document.getElementById('bytecode-table-body');
    if (bcBody && result.bytecode) {
      let html = '';
      result.bytecode.forEach(b => {
        html += `
          <tr>
            <td style="color:var(--text-muted); font-weight:bold;">${String(b.ip).padStart(4, '0')}</td>
            <td style="color:var(--accent-color); font-weight:bold;">${b.op}</td>
            <td style="color:var(--text-bright);">${b.arg1 !== null ? b.arg1 : ''}${b.arg2 !== null ? ', ' + b.arg2 : ''}</td>
            <td style="color:var(--text-muted); font-size:0.75rem;">${b.comment ? '// ' + b.comment : ''}</td>
          </tr>`;
      });
      bcBody.innerHTML = html;
    }

    // Bytecode in VM Debugger
    vmVisualizer.setBytecode(result.bytecode || []);

    // Execution output if run
    if (result.execution) {
      vmVisualizer.updateState(result.execution);
    }
  }

  function renderSymbolTableHierarchy(scope) {
    if (!scope) return '';
    let html = `
      <div class="scope-card">
        <div class="scope-header">
          <span><i class="fas fa-folder-open" style="margin-right:6px;"></i> ${scope.scope_name} (Level ${scope.level})</span>
          <span style="font-size:0.75rem; color:var(--text-muted);">${scope.symbols.length} symbols</span>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>Symbol Name</th>
              <th>Kind</th>
              <th>Type Signature</th>
              <th>Line</th>
            </tr>
          </thead>
          <tbody>`;

    if (scope.symbols.length === 0) {
      html += '<tr><td colspan="4" style="color:var(--text-muted); text-align:center; padding:10px;">No symbols in this scope</td></tr>';
    } else {
      scope.symbols.forEach(sym => {
        html += `
          <tr>
            <td style="color:var(--cyan-color); font-weight:600;">${sym.name}</td>
            <td><span class="token-tag">${sym.kind}</span></td>
            <td style="color:var(--text-bright); font-family:var(--font-mono);">${sym.type}</td>
            <td>${sym.line}</td>
          </tr>`;
      });
    }

    html += '</tbody></table></div>';

    // Render child scopes
    if (scope.children && scope.children.length > 0) {
      scope.children.forEach(child => {
        html += renderSymbolTableHierarchy(child);
      });
    }

    return html;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // 6. Action Handlers

  // Compile
  btnCompile.addEventListener('click', async () => {
    btnCompile.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Compiling...';
    try {
      const res = await API.compile(codeEditor.value);
      updatePipelineStages(res.stages, res.first_error);
      populateTabs(res);
    } catch (err) {
      console.error(err);
    } finally {
      btnCompile.innerHTML = '<i class="fas fa-hammer"></i> Compile';
    }
  });

  // Run
  btnRun.addEventListener('click', async () => {
    btnRun.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
    try {
      const res = await API.run(codeEditor.value);
      updatePipelineStages(res.stages, res.first_error);
      populateTabs(res);
      switchTab('vm');
    } catch (err) {
      console.error(err);
    } finally {
      btnRun.innerHTML = '<i class="fas fa-play"></i> Run';
    }
  });

  // Step VM
  btnStep.addEventListener('click', async () => {
    try {
      const state = await API.step(codeEditor.value, false);
      vmVisualizer.updateState(state);
      switchTab('vm');
    } catch (err) {
      console.error(err);
    }
  });

  // Auto Step
  btnAutoStep.addEventListener('click', () => {
    if (vmVisualizer.isAutoStepping) {
      vmVisualizer.stopAutoStep();
    } else {
      vmVisualizer.isAutoStepping = true;
      btnAutoStep.innerHTML = '<i class="fas fa-pause"></i> Pause';
      switchTab('vm');
      vmVisualizer.autoStepInterval = setInterval(async () => {
        try {
          const state = await API.step(codeEditor.value, false);
          vmVisualizer.updateState(state);
          if (state.status === 'FINISHED' || state.status === 'ERROR') {
            vmVisualizer.stopAutoStep();
          }
        } catch (err) {
          vmVisualizer.stopAutoStep();
        }
      }, 250);
    }
  });

  // Reset VM
  btnResetVM.addEventListener('click', async () => {
    vmVisualizer.stopAutoStep();
    try {
      const state = await API.step(codeEditor.value, true);
      vmVisualizer.updateState(state);
    } catch (err) {
      console.error(err);
    }
  });

  // 7. AI Assistant Handlers
  function openModal(title, bodyHtml) {
    aiModalTitle.innerText = title;
    aiModalBody.innerHTML = bodyHtml;
    aiModal.classList.add('visible');
  }

  btnCloseModal.addEventListener('click', () => {
    aiModal.classList.remove('visible');
  });

  // Explain Error
  btnExplainError.addEventListener('click', async () => {
    if (!currentPipelineResult || !currentPipelineResult.first_error) {
      openModal('Compiler Status', '<p style="color:var(--success-color);">No errors detected in current compilation! Code is completely valid.</p>');
      return;
    }

    openModal('AI Error Explanation', '<div style="text-align:center; padding:20px;"><i class="fas fa-spinner fa-spin fa-2x"></i><p style="margin-top:10px;">Consulting AI Assistant...</p></div>');

    try {
      const res = await API.explainError(codeEditor.value, currentPipelineResult.first_error);
      let html = `
        <div style="font-size:0.85rem; line-height:1.6;">
          <div style="background:rgba(224,108,117,0.15); border-left:4px solid var(--error-color); padding:10px; border-radius:4px; margin-bottom:14px;">
            <strong>Error Line ${res.line_number}:</strong> <code>${escapeHtml(res.code_snippet)}</code>
          </div>
          <h4 style="color:var(--text-bright); margin-bottom:6px;">Analysis:</h4>
          <p style="margin-bottom:14px; white-space:pre-wrap;">${escapeHtml(res.explanation)}</p>
          <h4 style="color:var(--success-color); margin-bottom:6px;">Suggested Fix:</h4>
          <div style="background:var(--bg-tertiary); padding:10px; border-radius:4px; border:1px solid var(--border-color); font-family:var(--font-mono); white-space:pre-wrap;">${escapeHtml(res.suggested_fix)}</div>
          <div style="margin-top:12px; font-size:0.75rem; color:var(--text-muted); text-align:right;">Mode: ${res.mode}</div>
        </div>`;
      aiModalBody.innerHTML = html;
    } catch (err) {
      aiModalBody.innerHTML = '<p style="color:var(--error-color);">Failed to fetch AI explanation.</p>';
    }
  });

  // Explain Stage
  btnExplainStage.addEventListener('click', async () => {
    openModal(`Stage Walkthrough: ${currentActiveStage.toUpperCase()}`, '<div style="text-align:center; padding:20px;"><i class="fas fa-spinner fa-spin fa-2x"></i><p style="margin-top:10px;">Generating educational stage explanation...</p></div>');

    try {
      const res = await API.explainStage(codeEditor.value, currentActiveStage, currentPipelineResult ? currentPipelineResult[currentActiveStage] : {});
      let html = `
        <div style="font-size:0.85rem; line-height:1.6;">
          <h3 style="color:var(--accent-color); margin-bottom:8px;">${res.title}</h3>
          <p style="margin-bottom:12px; font-weight:500; color:var(--text-bright);">${escapeHtml(res.summary)}</p>
          <div style="background:var(--bg-tertiary); padding:12px; border-radius:6px; border:1px solid var(--border-color); margin-bottom:12px;">
            <strong style="color:var(--purple-color);">What Happened on This Program:</strong>
            <p style="margin-top:4px; white-space:pre-wrap;">${escapeHtml(res.what_happened)}</p>
          </div>
          <div style="font-size:0.8rem; color:var(--cyan-color);">
            <strong>Underlying Compiler Concepts:</strong> ${escapeHtml(res.compiler_concepts)}
          </div>
          <div style="margin-top:12px; font-size:0.75rem; color:var(--text-muted); text-align:right;">Mode: ${res.mode}</div>
        </div>`;
      aiModalBody.innerHTML = html;
    } catch (err) {
      aiModalBody.innerHTML = '<p style="color:var(--error-color);">Failed to fetch stage explanation.</p>';
    }
  });

  // Natural Language to Code
  btnAiGenerate.addEventListener('click', () => {
    let html = `
      <div>
        <p style="font-size:0.85rem; margin-bottom:10px; color:var(--text-bright);">Describe what program you want in plain English. The AI will write MiniLang and the compiler will validate it:</p>
        <textarea id="nl-prompt-input" rows="3" style="width:100%; background:var(--bg-primary); border:1px solid var(--border-color); color:#fff; padding:10px; border-radius:4px; font-family:var(--font-sans); font-size:0.85rem; outline:none;" placeholder="E.g. Check whether a number is prime using a while loop and print the result..."></textarea>
        <div style="margin-top:12px; display:flex; justify-content:flex-end;">
          <button id="btn-submit-nl" class="btn btn-primary"><i class="fas fa-magic"></i> Generate & Validate</button>
        </div>
        <div id="nl-result-area" style="margin-top:14px;"></div>
      </div>`;
    openModal('Natural Language to Code', html);

    document.getElementById('btn-submit-nl').addEventListener('click', async () => {
      const promptText = document.getElementById('nl-prompt-input').value.trim();
      if (!promptText) return;

      const resultArea = document.getElementById('nl-result-area');
      resultArea.innerHTML = '<div style="text-align:center; padding:14px;"><i class="fas fa-spinner fa-spin"></i> Generating MiniLang code and validating with compiler...</div>';

      try {
        const genRes = await API.generateCode(promptText);
        let resHtml = `
          <div style="background:var(--bg-tertiary); padding:10px; border-radius:4px; border:1px solid var(--border-color); margin-top:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span class="badge ${genRes.valid ? 'success' : 'failed'}">${genRes.valid ? '✓ Validated by MiniLang Compiler' : '⚠ Validation Issues'}</span>
              <span style="font-size:0.75rem; color:var(--text-muted);">${genRes.attempts} attempt(s)</span>
            </div>
            <pre style="background:var(--bg-primary); padding:10px; border-radius:4px; font-family:var(--font-mono); font-size:0.8rem; overflow-x:auto;"><code>${escapeHtml(genRes.code)}</code></pre>
            <div style="margin-top:10px; text-align:right;">
              <button id="btn-insert-code" class="btn btn-success"><i class="fas fa-paste"></i> Load into Editor</button>
            </div>
          </div>`;
        resultArea.innerHTML = resHtml;

        document.getElementById('btn-insert-code').addEventListener('click', () => {
          codeEditor.value = genRes.code;
          updateLineNumbers();
          aiModal.classList.remove('visible');
          btnCompile.click();
        });
      } catch (err) {
        resultArea.innerHTML = '<p style="color:var(--error-color);">Failed to generate code.</p>';
      }
    });
  });

  // Optimization Hints
  btnOptimizationHints.addEventListener('click', async () => {
    openModal('Compiler Optimization Hints', '<div style="text-align:center; padding:20px;"><i class="fas fa-spinner fa-spin fa-2x"></i><p style="margin-top:10px;">Analyzing IR and evaluating optimizations...</p></div>');

    try {
      const res = await API.getOptimizationHints(
        codeEditor.value,
        currentPipelineResult ? currentPipelineResult.ir : [],
        currentPipelineResult ? currentPipelineResult.optimized_ir : []
      );
      let html = '<div style="font-size:0.85rem; line-height:1.6;">';
      (res.hints || []).forEach(h => {
        html += `
          <div style="background:var(--bg-tertiary); padding:10px 14px; border-radius:6px; border:1px solid var(--border-color); margin-bottom:10px;">
            <strong style="color:var(--purple-color);">${h.category}:</strong>
            <p style="margin-top:4px;">${escapeHtml(h.hint)}</p>
          </div>`;
      });
      html += '</div>';
      aiModalBody.innerHTML = html;
    } catch (err) {
      aiModalBody.innerHTML = '<p style="color:var(--error-color);">Failed to fetch optimization hints.</p>';
    }
  });

  // Initial compilation on page load
  setTimeout(() => {
    btnCompile.click();
  }, 300);
});
