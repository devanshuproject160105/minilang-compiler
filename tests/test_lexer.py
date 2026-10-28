"""
Unit tests for MiniLang Lexer (Scanner).
Verifies token recognition, literals, comments, position tracking, and error recovery.
"""

import pytest
from compiler.lexer import Lexer, LexicalError
from compiler.tokens import TokenType


def test_lexer_empty_and_whitespace():
    source = "   \t\n\r  "
    lexer = Lexer(source)
    tokens, errors = lexer.tokenize()
    assert len(errors) == 0
    assert len(tokens) == 1
    assert tokens[0].type == TokenType.EOF


def test_lexer_comments():
    source = """
    // First line comment
    let x = 42; // Inline comment
    // Trailing comment
    """
    lexer = Lexer(source)
    tokens, errors = lexer.tokenize()
    assert len(errors) == 0
    token_types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert token_types == [TokenType.LET, TokenType.IDENTIFIER, TokenType.ASSIGN, TokenType.INT_LIT, TokenType.SEMI]


def test_lexer_keywords_and_types():
    source = "let fn return if else while for print int float bool string void true false"
    lexer = Lexer(source)
    tokens, errors = lexer.tokenize()
    assert len(errors) == 0
    assert tokens[0].type == TokenType.LET
    assert tokens[1].type == TokenType.FN
    assert tokens[2].type == TokenType.RETURN
    assert tokens[3].type == TokenType.IF
    assert tokens[4].type == TokenType.ELSE
    assert tokens[5].type == TokenType.WHILE
    assert tokens[6].type == TokenType.FOR
    assert tokens[7].type == TokenType.PRINT
    assert tokens[8].type == TokenType.TYPE_INT
    assert tokens[9].type == TokenType.TYPE_FLOAT
    assert tokens[10].type == TokenType.TYPE_BOOL
    assert tokens[11].type == TokenType.TYPE_STRING
    assert tokens[12].type == TokenType.TYPE_VOID
    assert tokens[13].type == TokenType.BOOL_LIT and tokens[13].value is True
    assert tokens[14].type == TokenType.BOOL_LIT and tokens[14].value is False


def test_lexer_number_literals():
    source = "0 123 3.14159 0.005 9999"
    lexer = Lexer(source)
    tokens, errors = lexer.tokenize()
    assert len(errors) == 0
    assert tokens[0].type == TokenType.INT_LIT and tokens[0].value == 0
    assert tokens[1].type == TokenType.INT_LIT and tokens[1].value == 123
    assert tokens[2].type == TokenType.FLOAT_LIT and tokens[2].value == 3.14159
    assert tokens[3].type == TokenType.FLOAT_LIT and tokens[3].value == 0.005
    assert tokens[4].type == TokenType.INT_LIT and tokens[4].value == 9999


def test_lexer_string_literals_with_escapes():
    source = r'"Hello, World!" "Line1\nLine2\tTabbed" "Escaped \"quotes\""'
    lexer = Lexer(source)
    tokens, errors = lexer.tokenize()
    assert len(errors) == 0
    assert tokens[0].type == TokenType.STRING_LIT and tokens[0].value == "Hello, World!"
    assert tokens[1].type == TokenType.STRING_LIT and tokens[1].value == "Line1\nLine2\tTabbed"
    assert tokens[2].type == TokenType.STRING_LIT and tokens[2].value == 'Escaped "quotes"'


def test_lexer_operators():
    source = "+ - * / % == != < <= > >= && || ! = ->"
    lexer = Lexer(source)
    tokens, errors = lexer.tokenize()
    assert len(errors) == 0
    expected_ops = [
        TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.PERCENT,
        TokenType.EQEQ, TokenType.NEQ, TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE,
        TokenType.AND, TokenType.OR, TokenType.NOT, TokenType.ASSIGN, TokenType.ARROW
    ]
    actual_ops = [t.type for t in tokens if t.type != TokenType.EOF]
    assert actual_ops == expected_ops


def test_lexer_line_and_column_tracking():
    source = "let a = 10;\nlet b = 20;"
    lexer = Lexer(source)
    tokens, errors = lexer.tokenize()
    assert len(errors) == 0

    # 'let' line 1, col 1
    assert tokens[0].line == 1 and tokens[0].column == 1
    # 'a' line 1, col 5
    assert tokens[1].line == 1 and tokens[1].column == 5
    # second 'let' line 2, col 1
    assert tokens[5].line == 2 and tokens[5].column == 1


def test_lexer_error_recovery_invalid_characters():
    source = "let x = 10 @ 5 # 3; let y = 20;"
    lexer = Lexer(source)
    tokens, errors = lexer.tokenize()

    # Recovery: reports errors for @ and #, but continues tokenizing the remaining valid tokens
    assert len(errors) == 2
    assert errors[0].character == "@"
    assert errors[1].character == "#"

    token_types = [t.type for t in tokens if t.type != TokenType.EOF]
    assert TokenType.LET in token_types
    assert token_types[-5:] == [TokenType.LET, TokenType.IDENTIFIER, TokenType.ASSIGN, TokenType.INT_LIT, TokenType.SEMI]
