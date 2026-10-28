"""
Unit tests for the MiniLang Stack-based Virtual Machine.
Verifies bytecode execution, control flow, functions, recursion, division-by-zero protection,
instruction limit infinite loop protection, and step-by-step debugging.
"""

import pytest
from compiler.pipeline import CompilerPipeline
from compiler.vm import VMError


def run_code(source: str):
    pipeline = CompilerPipeline()
    res = pipeline.compile(source, execute=True)
    return res


def test_vm_arithmetic_execution():
    source = """
    let a = 15;
    let b = 4;
    print(a + b);
    print(a - b);
    print(a * b);
    print(a / b);
    print(a % b);
    """
    res = run_code(source)
    assert res.success is True
    assert res.execution["output"] == ["19", "11", "60", "3", "3"]


def test_vm_string_concatenation():
    source = """
    let greeting = "Hello, " + "World!";
    print(greeting);
    """
    res = run_code(source)
    assert res.success is True
    assert res.execution["output"] == ["Hello, World!"]


def test_vm_if_else_branching():
    source = """
    let score = 85;
    if (score >= 90) {
        print("Grade A");
    } else if (score >= 80) {
        print("Grade B");
    } else {
        print("Grade C");
    }
    """
    res = run_code(source)
    assert res.success is True
    assert res.execution["output"] == ["Grade B"]


def test_vm_while_loop_accumulator():
    source = """
    let i = 1;
    let sum = 0;
    while (i <= 5) {
        sum = sum + i;
        i = i + 1;
    }
    print(sum);
    """
    res = run_code(source)
    assert res.success is True
    assert res.execution["output"] == ["15"]


def test_vm_for_loop():
    source = """
    let product = 1;
    for (let k = 1; k <= 4; k = k + 1) {
        product = product * k;
    }
    print(product);
    """
    res = run_code(source)
    assert res.success is True
    assert res.execution["output"] == ["24"]


def test_vm_function_call_and_return():
    source = """
    fn square(x: int) -> int {
        return x * x;
    }
    let val = square(7);
    print(val);
    """
    res = run_code(source)
    assert res.success is True
    assert res.execution["output"] == ["49"]


def test_vm_recursive_function():
    source = """
    fn fib(n: int) -> int {
        if (n <= 0) { return 0; }
        if (n == 1) { return 1; }
        return fib(n - 1) + fib(n - 2);
    }
    print(fib(6));
    """
    res = run_code(source)
    assert res.success is True
    assert res.execution["output"] == ["8"]


def test_vm_division_by_zero_runtime_error():
    source = """
    let x = 10;
    let y = 0;
    let z = x / y;
    print(z);
    """
    res = run_code(source)
    assert res.success is False
    assert res.first_error is not None
    assert "division by zero" in res.first_error["message"].lower()


def test_vm_infinite_loop_protection():
    source = """
    let x = 0;
    while (true) {
        x = x + 1;
    }
    """
    # Compile and execute with infinite loop protection
    pipeline = CompilerPipeline()
    res = pipeline.compile(source, execute=False)
    assert res.success is True

    # Run VM with small limit to test protection
    pipeline.vm.max_steps = 100
    state = pipeline.vm.run()
    assert state.status == "ERROR"
    assert "infinite loop detected" in state.error.lower()


def test_vm_step_by_step_mode():
    source = """
    let a = 5;
    let b = 10;
    let c = a + b;
    """
    pipeline = CompilerPipeline()
    res = pipeline.compile(source, execute=False)
    assert res.success is True

    # Take 3 steps
    s1 = pipeline.vm.step()
    assert s1.status == "PAUSED"
    assert s1.step_count == 1

    s2 = pipeline.vm.step()
    assert s2.step_count == 2

    s3 = pipeline.vm.step()
    assert s3.step_count == 3
    assert s3.ip > 0
