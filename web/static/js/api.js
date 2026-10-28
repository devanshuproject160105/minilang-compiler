/**
 * API client for the MiniLang Compiler visual pipeline.
 */

const API = {
  sessionId: 'session_' + Math.random().toString(36).substring(2, 9),

  async fetchExamples() {
    const res = await fetch('/api/examples');
    return await res.json();
  },

  async compile(code) {
    const res = await fetch('/api/compile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, session_id: this.sessionId })
    });
    return await res.json();
  },

  async run(code) {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, session_id: this.sessionId })
    });
    return await res.json();
  },

  async step(code, reset = false) {
    const res = await fetch('/api/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, session_id: this.sessionId, reset })
    });
    return await res.json();
  },

  async explainError(code, error) {
    const res = await fetch('/api/ai/explain-error', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, error })
    });
    return await res.json();
  },

  async explainStage(code, stage, stageData) {
    const res = await fetch('/api/ai/explain-stage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, stage, stage_data: stageData })
    });
    return await res.json();
  },

  async generateCode(prompt) {
    const res = await fetch('/api/ai/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    });
    return await res.json();
  },

  async getOptimizationHints(code, ir, optimizedIr) {
    const res = await fetch('/api/ai/optimize-hints', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, ir, optimized_ir: optimizedIr })
    });
    return await res.json();
  }
};
