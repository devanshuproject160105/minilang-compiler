"""
Unit tests for MiniLang Recursive Descent Parser.
Verifies AST node construction, operator precedence, and panic-mode error recovery.
"""

import pytest
from compiler.lexer import Lexer
from compiler.parser import Parser
from compiler.ast_nodes import (
    ProgramNode,
    VarDeclNode,
    AssignNode,
    IfNode,
    WhileNode,
    ForNode,
    FnDeclNode,
    BinaryOpNode,
    LiteralNode,
    IdentifierNode,
    CallNode,
)


def parse_source(source: str):
    tokens, lex_errs = Lexer(source).tokenize()
    assert len(lex_errs) == 0
    parser = Parser(tokens)
    return parser.parse()


def test_parser_variable_declarations():
    source = """
    let a: int = 10;
    let b = 20.5;
    let c: string;
    """
    program, errors = parse_source(source)
    assert len(errors) == 0
    assert len(program.statements) == 3

    assert isinstance(program.statements[0], VarDeclNode)
    assert program.statements[0].name == "a"
    assert program.statements[0].type_name == "int"

    assert isinstance(program.statements[1], VarDeclNode)
    assert program.statements[1].name == "b"
    assert program.statements[1].type_name is None
    assert isinstance(program.statements[1].init_expr, LiteralNode)

    assert isinstance(program.statements[2], VarDeclNode)
    assert program.statements[2].name == "c"
    assert program.statements[2].init_expr is None


def test_parser_operator_precedence():
    # 2 + 3 * 4 should parse as 2 + (3 * 4)
    source = "let result = 2 + 3 * 4;"
    program, errors = parse_source(source)
    assert len(errors) == 0

    decl = program.statements[0]
    binop = decl.init_expr
    assert isinstance(binop, BinaryOpNode)
    assert binop.op == "+"
    assert isinstance(binop.left, LiteralNode) and binop.left.value == 2
    assert isinstance(binop.right, BinaryOpNode) and binop.right.op == "*"


def test_parser_parentheses_override_precedence():
    # (2 + 3) * 4
    source = "let result = (2 + 3) * 4;"
    program, errors = parse_source(source)
    assert len(errors) == 0

    decl = program.statements[0]
    binop = decl.init_expr
    assert isinstance(binop, BinaryOpNode)
    assert binop.op == "*"
    assert isinstance(binop.left, BinaryOpNode) and binop.left.op == "+"


def test_parser_if_else_statement():
    source = """
    if (x > 0) {
        y = 1;
    } else {
        y = -1;
    }
    """
    program, errors = parse_source(source)
    assert len(errors) == 0
    assert len(program.statements) == 1
    if_stmt = program.statements[0]
    assert isinstance(if_stmt, IfNode)
    assert isinstance(if_stmt.condition, BinaryOpNode)
    assert if_stmt.else_branch is not None


def test_parser_while_and_for_loops():
    source = """
    while (i < 10) {
        i = i + 1;
    }
    for (let j = 0; j < 5; j = j + 1) {
        print(j);
    }
    """
    program, errors = parse_source(source)
    assert len(errors) == 0
    assert len(program.statements) == 2
    assert isinstance(program.statements[0], WhileNode)
    assert isinstance(program.statements[1], ForNode)


def test_parser_function_declaration_and_call():
    source = """
    fn multiply(x: int, y: int) -> int {
        return x * y;
    }
    let ans = multiply(4, 5);
    """
    program, errors = parse_source(source)
    assert len(errors) == 0
    assert len(program.statements) == 2

    fn_node = program.statements[0]
    assert isinstance(fn_node, FnDeclNode)
    assert fn_node.name == "multiply"
    assert len(fn_node.params) == 2
    assert fn_node.return_type == "int"

    call_decl = program.statements[1]
    call_expr = call_decl.init_expr
    assert isinstance(call_expr, CallNode)
    assert call_expr.callee == "multiply"
    assert len(call_expr.args) == 2


def test_parser_missing_semicolon_error():
    source = "let x = 10"  # Missing semicolon at EOF
    tokens, _ = Lexer(source).tokenize()
    parser = Parser(tokens)
    program, errors = parser.parse()
    assert len(errors) >= 1
    assert "Expected ';'" in errors[0].message


def test_parser_multi_error_recovery():
    # Multiple deliberate syntax errors across separate lines
    source = """
    let a = ;
    let b = 20;
    let c = (30 + ;
    let d = 40;
    """
    tokens, _ = Lexer(source).tokenize()
    parser = Parser(tokens)
    program, errors = parser.parse()

    # The parser must NOT stop at the first error!
    assert len(errors) >= 2
    # Verify that valid statements following errors ('b' and 'd') were parsed into AST!
    var_names = [stmt.name for stmt in program.statements if isinstance(stmt, VarDeclNode)]
    assert "b" in var_names
    assert "d" in var_names
