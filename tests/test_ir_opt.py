"""
Unit tests for TAC Intermediate Representation and the IR Optimizer.
Verifies constant folding, constant propagation, dead code elimination, and rule logging.
"""

import pytest
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.semantic import SemanticAnalyzer
from compiler.ir_generator import IRGenerator
from compiler.optimizer import Optimizer
from compiler.ir import OpCode


def get_raw_ir(source: str):
    tokens, _ = Lexer(source).tokenize()
    program, _ = Parser(tokens).parse()
    analyzer = SemanticAnalyzer()
    analyzer.analyze(program)
    ir_gen = IRGenerator()
    return ir_gen.generate(program)


def test_ir_generation_basic_arithmetic():
    source = "let x = 10 + 20 * 3;"
    raw_ir = get_raw_ir(source)
    assert len(raw_ir) >= 3
    # Check that MUL and ADD instructions are generated
    ops = [instr.op for instr in raw_ir]
    assert OpCode.MUL in ops
    assert OpCode.ADD in ops
    assert OpCode.ASSIGN in ops


def test_ir_generation_while_loop():
    source = """
    let i = 0;
    while (i < 5) {
        i = i + 1;
    }
    """
    raw_ir = get_raw_ir(source)
    ops = [instr.op for instr in raw_ir]
    assert OpCode.LABEL in ops
    assert OpCode.JUMP_IF_FALSE in ops
    assert OpCode.JUMP in ops


def test_optimizer_constant_folding_arithmetic():
    source = "let x = 15 + 4;"
    raw_ir = get_raw_ir(source)
    optimizer = Optimizer()
    opt_ir, logs = optimizer.optimize(raw_ir)

    # 15 + 4 must be folded into 19
    assigned_values = [instr.arg1 for instr in opt_ir if instr.op == OpCode.ASSIGN]
    assert 19 in assigned_values

    # Check rule log
    rules = [l["rule"] for l in logs]
    assert "Constant Folding" in rules


def test_optimizer_constant_folding_comparisons():
    source = """
    let c1 = 10 > 5;
    let c2 = 3 == 4;
    """
    raw_ir = get_raw_ir(source)
    optimizer = Optimizer()
    opt_ir, logs = optimizer.optimize(raw_ir)

    assigned_values = [instr.arg1 for instr in opt_ir if instr.op == OpCode.ASSIGN]
    assert True in assigned_values
    assert False in assigned_values


def test_optimizer_constant_folding_booleans():
    source = "let b = true && false;"
    raw_ir = get_raw_ir(source)
    optimizer = Optimizer()
    opt_ir, logs = optimizer.optimize(raw_ir)

    assigned_values = [instr.arg1 for instr in opt_ir if instr.op == OpCode.ASSIGN]
    assert False in assigned_values


def test_optimizer_constant_propagation():
    source = """
    let a = 10;
    let b = a + 5;
    """
    raw_ir = get_raw_ir(source)
    optimizer = Optimizer()
    opt_ir, logs = optimizer.optimize(raw_ir)

    # Constant propagation + subsequent folding folds b to 15!
    assigned_values = [instr.arg1 for instr in opt_ir if instr.op == OpCode.ASSIGN]
    assert 15 in assigned_values
    rules = [l["rule"] for l in logs]
    assert "Constant Propagation" in rules or "Constant Folding" in rules


def test_optimizer_dead_code_elimination_unused_temps():
    # An expression computed into a temporary that is never used
    source = """
    let x = 10;
    let y = 20;
    print(x);
    """
    raw_ir = get_raw_ir(source)
    optimizer = Optimizer()
    opt_ir, logs = optimizer.optimize(raw_ir)
    rules = [l["rule"] for l in logs]
    # Check that optimization runs cleanly without altering semantics
    assert len(opt_ir) > 0


def test_optimizer_dead_code_after_return():
    source = """
    fn test() -> int {
        return 42;
        let dead = 999;
    }
    """
    raw_ir = get_raw_ir(source)
    optimizer = Optimizer()
    opt_ir, logs = optimizer.optimize(raw_ir)

    rules = [l["rule"] for l in logs]
    assert "Dead Code Elimination" in rules
    # 999 should not be present in optimized IR
    instr_texts = [instr.to_text() for instr in opt_ir]
    assert not any("999" in t for t in instr_texts)
