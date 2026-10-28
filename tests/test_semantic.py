"""
Unit tests for MiniLang Semantic Analyzer and Symbol Table.
Verifies static typing, scoping, redeclaration rules, and function signatures.
"""

import pytest
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.semantic import SemanticAnalyzer


def analyze_source(source: str):
    tokens, _ = Lexer(source).tokenize()
    program, parse_errs = Parser(tokens).parse()
    assert len(parse_errs) == 0, f"Parse errors: {parse_errs}"
    analyzer = SemanticAnalyzer()
    errors, sym_table = analyzer.analyze(program)
    return errors, sym_table


def test_semantic_valid_program():
    source = """
    let x: int = 10;
    let y = 20;
    let z = x + y;
    print(z);
    """
    errors, _ = analyze_source(source)
    assert len(errors) == 0


def test_semantic_undefined_variable():
    source = "let a = b + 5;"
    errors, _ = analyze_source(source)
    assert len(errors) == 1
    assert "undeclared variable 'b'" in errors[0].message


def test_semantic_redeclaration_in_same_scope():
    source = """
    let x: int = 10;
    let x: int = 20;
    """
    errors, _ = analyze_source(source)
    assert len(errors) == 1
    assert "Redeclaration of variable 'x'" in errors[0].message


def test_semantic_scope_shadowing_allowed():
    source = """
    let x: int = 100;
    if (x > 50) {
        let x: string = "shadowed";
        print(x);
    }
    print(x);
    """
    errors, _ = analyze_source(source)
    assert len(errors) == 0  # Shadowing in nested child scope is completely valid!


def test_semantic_type_mismatch_in_declaration():
    source = 'let x: int = "hello";'
    errors, _ = analyze_source(source)
    assert len(errors) == 1
    assert "Type mismatch" in errors[0].message


def test_semantic_invalid_binary_operator_types():
    source = 'let x = "text" - 5;'
    errors, _ = analyze_source(source)
    assert len(errors) == 1
    assert "not supported between 'string' and 'int'" in errors[0].message


def test_semantic_condition_must_be_bool():
    source = """
    let num = 42;
    if (num) {
        print("invalid condition");
    }
    """
    errors, _ = analyze_source(source)
    assert len(errors) == 1
    assert "must be 'bool'" in errors[0].message


def test_semantic_function_arg_count_and_types():
    source = """
    fn add(a: int, b: int) -> int {
        return a + b;
    }
    let res1 = add(1);           // Missing argument
    let res2 = add(1, "bad");    // Type mismatch argument
    """
    errors, _ = analyze_source(source)
    assert len(errors) == 2
    assert "expects 2 arguments, but got 1" in errors[0].message
    assert "expects type 'int', but got 'string'" in errors[1].message


def test_semantic_missing_return_check():
    source = """
    fn compute(x: int) -> int {
        if (x > 0) {
            return x;
        }
        // Missing return in else path!
    }
    """
    errors, _ = analyze_source(source)
    assert len(errors) == 1
    assert "missing a return statement" in errors[0].message
