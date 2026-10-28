"""
Integration tests executing all 5 example programs end-to-end
and validating all Flask REST API endpoints.
"""

from pathlib import Path
import pytest
from compiler.pipeline import CompilerPipeline
from web.app import app

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def test_example_01_hello_end_to_end():
    file_path = EXAMPLES_DIR / "01_hello.mlang"
    code = file_path.read_text(encoding="utf-8")
    pipeline = CompilerPipeline()
    res = pipeline.compile(code, execute=True)

    assert res.success is True
    assert "Hello, Compiler World!" in res.execution["output"]
    assert "19" in res.execution["output"]


def test_example_02_factorial_end_to_end():
    file_path = EXAMPLES_DIR / "02_factorial.mlang"
    code = file_path.read_text(encoding="utf-8")
    pipeline = CompilerPipeline()
    res = pipeline.compile(code, execute=True)

    assert res.success is True
    # 5! is 120
    assert "120" in res.execution["output"]
    assert "Verification succeeded: both implementations match!" in res.execution["output"]


def test_example_03_fibonacci_end_to_end():
    file_path = EXAMPLES_DIR / "03_fibonacci.mlang"
    code = file_path.read_text(encoding="utf-8")
    pipeline = CompilerPipeline()
    res = pipeline.compile(code, execute=True)

    assert res.success is True
    assert any("fib(" in line for line in res.execution["output"])


def test_example_04_prime_check_end_to_end():
    file_path = EXAMPLES_DIR / "04_prime_check.mlang"
    code = file_path.read_text(encoding="utf-8")
    pipeline = CompilerPipeline()
    res = pipeline.compile(code, execute=True)

    assert res.success is True
    assert "Total primes found up to 25: 9" in " ".join(res.execution["output"]) or "9" in res.execution["output"]


def test_example_05_nested_loops_end_to_end():
    file_path = EXAMPLES_DIR / "05_nested_loops.mlang"
    code = file_path.read_text(encoding="utf-8")
    pipeline = CompilerPipeline()
    res = pipeline.compile(code, execute=True)

    assert res.success is True
    # Total sum of 5x5 multiplication table is 225
    assert "Total sum of multiplication matrix: 225" in " ".join(res.execution["output"]) or "225" in res.execution["output"]


def test_flask_api_endpoints():
    client = app.test_client()

    # GET /api/examples
    resp = client.get("/api/examples")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "examples" in data
    assert len(data["examples"]) >= 5

    # POST /api/compile
    resp = client.post("/api/compile", json={"code": "let a = 10; print(a);"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["tokens"]) > 0
    assert data["ast"] is not None

    # POST /api/run
    resp = client.post("/api/run", json={"code": "let a = 5 * 6; print(a);"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "30" in data["execution"]["output"]

    # POST /api/step
    resp = client.post("/api/step", json={"code": "let x = 1; let y = 2;", "reset": True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] in ("RUNNING", "PAUSED")

    # POST /api/ai/explain-error
    resp = client.post("/api/ai/explain-error", json={
        "code": "let x = 10",
        "error": {"stage": "parser", "message": "Expected ';'", "line": 1, "column": 10}
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "explanation" in data

    # POST /api/ai/explain-stage
    resp = client.post("/api/ai/explain-stage", json={
        "code": "let x = 10;",
        "stage": "lexer",
        "stage_data": {}
    })
    assert resp.status_code == 200
    assert "summary" in resp.get_json()

    # POST /api/ai/generate
    resp = client.post("/api/ai/generate", json={"prompt": "calculate factorial"})
    assert resp.status_code == 200
    assert "code" in resp.get_json()
