"""
Flask Application and REST API for the MiniLang Visual Compiler Pipeline.
"""

import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify, render_template

# Ensure parent directory is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from compiler.pipeline import CompilerPipeline
from ai.assistant import AIAssistant

app = Flask(__name__, template_folder="templates", static_folder="static")

# Shared state for VM step sessions (in-memory, keyed by session_id or single-user default)
vm_sessions = {}
ai_assistant = AIAssistant()


def get_examples() -> list:
    examples_dir = ROOT_DIR / "examples"
    examples = []
    if examples_dir.exists():
        for file in sorted(examples_dir.glob("*.mlang")):
            try:
                content = file.read_text(encoding="utf-8")
                # First line might have title comment
                lines = content.strip().split("\n")
                title = lines[0].replace("//", "").strip() if lines else file.name
                examples.append({
                    "id": file.stem,
                    "filename": file.name,
                    "title": title,
                    "code": content,
                })
            except Exception:
                pass
    return examples


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/examples", methods=["GET"])
def api_examples():
    return jsonify({"examples": get_examples()})


@app.route("/api/compile", methods=["POST"])
def api_compile():
    data = request.get_json() or {}
    source_code = data.get("code", "")
    session_id = data.get("session_id", "default")

    pipeline = CompilerPipeline()
    result = pipeline.compile(source_code, execute=False)

    # Store VM instance for stepping if compilation succeeded
    if result.success and pipeline.vm:
        vm_sessions[session_id] = pipeline.vm

    return jsonify(result.to_dict())


@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json() or {}
    source_code = data.get("code", "")
    session_id = data.get("session_id", "default")

    pipeline = CompilerPipeline()
    result = pipeline.compile(source_code, execute=True)

    if result.success and pipeline.vm:
        vm_sessions[session_id] = pipeline.vm

    return jsonify(result.to_dict())


@app.route("/api/step", methods=["POST"])
def api_step():
    data = request.get_json() or {}
    session_id = data.get("session_id", "default")
    source_code = data.get("code", "")
    reset = data.get("reset", False)

    # If reset requested or session not found, initialize fresh VM
    if reset or session_id not in vm_sessions:
        pipeline = CompilerPipeline()
        result = pipeline.compile(source_code, execute=False)
        if not result.success:
            return jsonify({
                "status": "ERROR",
                "error": result.first_error.get("message") if result.first_error else "Compilation error",
                "stage": result.first_error.get("stage") if result.first_error else "compiler",
            }), 400
        vm_sessions[session_id] = pipeline.vm

    vm = vm_sessions[session_id]
    state = vm.step()
    return jsonify(state.to_dict())


@app.route("/api/ai/explain-error", methods=["POST"])
def api_explain_error():
    data = request.get_json() or {}
    code = data.get("code", "")
    error = data.get("error", {})
    explanation = ai_assistant.explain_error(code, error)
    return jsonify(explanation)


@app.route("/api/ai/explain-stage", methods=["POST"])
def api_explain_stage():
    data = request.get_json() or {}
    code = data.get("code", "")
    stage = data.get("stage", "lexer")
    stage_data = data.get("stage_data", {})
    explanation = ai_assistant.explain_stage(code, stage, stage_data)
    return jsonify(explanation)


@app.route("/api/ai/generate", methods=["POST"])
def api_generate():
    data = request.get_json() or {}
    prompt = data.get("prompt", "")
    result = ai_assistant.generate_code_with_validation(prompt, CompilerPipeline)
    return jsonify(result)


@app.route("/api/ai/optimize-hints", methods=["POST"])
def api_optimize_hints():
    data = request.get_json() or {}
    code = data.get("code", "")
    ir = data.get("ir", [])
    optimized_ir = data.get("optimized_ir", [])
    hints = ai_assistant.get_optimization_hints(code, ir, optimized_ir)
    return jsonify({"hints": hints})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
