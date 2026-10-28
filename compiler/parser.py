"""
Recursive Descent Parser for MiniLang.
Constructs an AST and features robust panic-mode synchronization to report
multiple syntax errors with accurate line and column coordinates.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from .tokens import Token, TokenType
from .ast_nodes import (
    ASTNode,
    ProgramNode,
    VarDeclNode,
    AssignNode,
    IfNode,
    WhileNode,
    ForNode,
    PrintNode,
    ReturnNode,
    FnDeclNode,
    BlockNode,
    BinaryOpNode,
    UnaryOpNode,
    LiteralNode,
    IdentifierNode,
    CallNode,
)


@dataclass
class ParseError:
    message: str
    line: int
    column: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": "parser",
            "message": self.message,
            "line": self.line,
            "column": self.column,
        }


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens: List[Token] = tokens
        self.current: int = 0
        self.errors: List[ParseError] = []

    def _peek(self, offset: int = 0) -> Token:
        idx = self.current + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # Return EOF

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _previous(self) -> Token:
        if self.current > 0:
            return self.tokens[self.current - 1]
        return self.tokens[0]

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end():
            return token_type == TokenType.EOF
        return self._peek().type == token_type

    def _match(self, *token_types: TokenType) -> bool:
        for t in token_types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _consume(self, token_type: TokenType, error_message: str) -> Optional[Token]:
        if self._check(token_type):
            return self._advance()
        tok = self._peek()
        self._error(f"{error_message} (found '{tok.lexeme or tok.type.value}')", tok.line, tok.column)
        return None

    def _error(self, message: str, line: int, column: int):
        self.errors.append(ParseError(message, line, column))

    def _synchronize(self):
        """Panic-mode recovery: advances tokens until a plausible statement boundary."""
        if self._peek().type in (
            TokenType.LET,
            TokenType.FN,
            TokenType.IF,
            TokenType.WHILE,
            TokenType.FOR,
            TokenType.PRINT,
            TokenType.RETURN,
        ):
            return

        self._advance()
        while not self._is_at_end():
            if self._previous().type in (TokenType.SEMI, TokenType.RBRACE):
                return

            if self._peek().type in (
                TokenType.LET,
                TokenType.FN,
                TokenType.IF,
                TokenType.WHILE,
                TokenType.FOR,
                TokenType.PRINT,
                TokenType.RETURN,
                TokenType.LBRACE,
            ):
                return
            self._advance()

    def parse(self) -> Tuple[Optional[ProgramNode], List[ParseError]]:
        """Parses the entire token stream into a ProgramNode."""
        self.current = 0
        self.errors = []
        statements: List[ASTNode] = []

        while not self._is_at_end():
            try:
                stmt = self._parse_top_level()
                if stmt:
                    statements.append(stmt)
            except Exception as e:
                # Fallback safety
                tok = self._peek()
                self._error(f"Unexpected parsing failure: {str(e)}", tok.line, tok.column)
                self._synchronize()

        program = ProgramNode(statements, 1, 1)
        return program, self.errors

    def _parse_top_level(self) -> Optional[ASTNode]:
        if self._check(TokenType.FN):
            return self._parse_function_decl()
        return self._parse_statement()

    def _parse_function_decl(self) -> Optional[FnDeclNode]:
        fn_tok = self._advance()  # 'fn'
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected function name after 'fn'")
        if not name_tok:
            self._synchronize()
            return None

        if not self._consume(TokenType.LPAREN, "Expected '(' after function name"):
            self._synchronize()
            return None

        params: List[Dict[str, str]] = []
        if not self._check(TokenType.RPAREN):
            while True:
                p_name_tok = self._consume(TokenType.IDENTIFIER, "Expected parameter name")
                if not p_name_tok:
                    self._synchronize()
                    return None
                
                if not self._consume(TokenType.COLON, "Expected ':' after parameter name"):
                    self._synchronize()
                    return None

                p_type = self._parse_type()
                if not p_type:
                    self._synchronize()
                    return None

                params.append({"name": p_name_tok.lexeme, "type": p_type})

                if not self._match(TokenType.COMMA):
                    break

        if not self._consume(TokenType.RPAREN, "Expected ')' after parameter list"):
            self._synchronize()
            return None

        return_type = "void"
        if self._match(TokenType.ARROW):
            r_type = self._parse_type()
            if r_type:
                return_type = r_type

        if not self._check(TokenType.LBRACE):
            tok = self._peek()
            self._error("Expected '{' for function body", tok.line, tok.column)
            self._synchronize()
            return None

        body = self._parse_block()
        return FnDeclNode(name_tok.lexeme, params, return_type, body, fn_tok.line, fn_tok.column)

    def _parse_type(self) -> Optional[str]:
        if self._match(TokenType.TYPE_INT):
            return "int"
        if self._match(TokenType.TYPE_FLOAT):
            return "float"
        if self._match(TokenType.TYPE_BOOL):
            return "bool"
        if self._match(TokenType.TYPE_STRING):
            return "string"
        if self._match(TokenType.TYPE_VOID):
            return "void"
        tok = self._peek()
        self._error(f"Expected type name (int, float, bool, string, void)", tok.line, tok.column)
        return None

    def _parse_statement(self) -> Optional[ASTNode]:
        try:
            if self._match(TokenType.LET):
                return self._parse_var_decl()
            if self._match(TokenType.IF):
                return self._parse_if_stmt()
            if self._match(TokenType.WHILE):
                return self._parse_while_stmt()
            if self._match(TokenType.FOR):
                return self._parse_for_stmt()
            if self._match(TokenType.PRINT):
                return self._parse_print_stmt()
            if self._match(TokenType.RETURN):
                return self._parse_return_stmt()
            if self._check(TokenType.LBRACE):
                return self._parse_block()

            # Assignment or expression statement
            if self._check(TokenType.IDENTIFIER) and self._peek(1).type == TokenType.ASSIGN:
                return self._parse_assignment_stmt()

            return self._parse_expr_stmt()
        except Exception:
            self._synchronize()
            return None

    def _parse_var_decl(self) -> Optional[VarDeclNode]:
        let_tok = self._previous()
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected identifier after 'let'")
        if not name_tok:
            self._synchronize()
            return None

        type_name: Optional[str] = None
        if self._match(TokenType.COLON):
            type_name = self._parse_type()

        init_expr: Optional[ASTNode] = None
        if self._match(TokenType.ASSIGN):
            init_expr = self._parse_expression()

        if not self._consume(TokenType.SEMI, "Expected ';' after variable declaration"):
            self._synchronize()
            return None

        return VarDeclNode(name_tok.lexeme, type_name, init_expr, let_tok.line, let_tok.column)

    def _parse_assignment_stmt(self) -> Optional[AssignNode]:
        name_tok = self._advance()  # IDENTIFIER
        self._advance()  # ASSIGN '='
        expr = self._parse_expression()
        if not self._consume(TokenType.SEMI, "Expected ';' after assignment"):
            self._synchronize()
            return None
        return AssignNode(name_tok.lexeme, expr, name_tok.line, name_tok.column)

    def _parse_if_stmt(self) -> Optional[IfNode]:
        if_tok = self._previous()
        if not self._consume(TokenType.LPAREN, "Expected '(' after 'if'"):
            self._synchronize()
            return None

        condition = self._parse_expression()

        if not self._consume(TokenType.RPAREN, "Expected ')' after if condition"):
            self._synchronize()
            return None

        if not self._check(TokenType.LBRACE):
            tok = self._peek()
            self._error("Expected '{' for 'if' block", tok.line, tok.column)
            self._synchronize()
            return None

        then_branch = self._parse_block()

        else_branch: Optional[ASTNode] = None
        if self._match(TokenType.ELSE):
            if self._check(TokenType.IF):
                self._advance()  # 'if'
                else_branch = self._parse_if_stmt()
            elif self._check(TokenType.LBRACE):
                else_branch = self._parse_block()
            else:
                tok = self._peek()
                self._error("Expected '{' or 'if' after 'else'", tok.line, tok.column)
                self._synchronize()

        return IfNode(condition, then_branch, else_branch, if_tok.line, if_tok.column)

    def _parse_while_stmt(self) -> Optional[WhileNode]:
        while_tok = self._previous()
        if not self._consume(TokenType.LPAREN, "Expected '(' after 'while'"):
            self._synchronize()
            return None

        condition = self._parse_expression()

        if not self._consume(TokenType.RPAREN, "Expected ')' after while condition"):
            self._synchronize()
            return None

        if not self._check(TokenType.LBRACE):
            tok = self._peek()
            self._error("Expected '{' for while body", tok.line, tok.column)
            self._synchronize()
            return None

        body = self._parse_block()
        return WhileNode(condition, body, while_tok.line, while_tok.column)

    def _parse_for_stmt(self) -> Optional[ForNode]:
        for_tok = self._previous()
        if not self._consume(TokenType.LPAREN, "Expected '(' after 'for'"):
            self._synchronize()
            return None

        # 1. Initializer: let x = 0; OR x = 0; OR ;
        init: Optional[ASTNode] = None
        if self._match(TokenType.LET):
            init = self._parse_var_decl()
        elif self._match(TokenType.SEMI):
            init = None
        elif self._check(TokenType.IDENTIFIER) and self._peek(1).type == TokenType.ASSIGN:
            init = self._parse_assignment_stmt()
        else:
            init = self._parse_expr_stmt()

        # 2. Condition: expr; OR ;
        condition: Optional[ASTNode] = None
        if not self._check(TokenType.SEMI):
            condition = self._parse_expression()
        if not self._consume(TokenType.SEMI, "Expected ';' after for loop condition"):
            self._synchronize()
            return None

        # 3. Update: x = x + 1 (no trailing semicolon)
        update: Optional[ASTNode] = None
        if not self._check(TokenType.RPAREN):
            if self._check(TokenType.IDENTIFIER) and self._peek(1).type == TokenType.ASSIGN:
                id_tok = self._advance()
                self._advance()  # '='
                expr = self._parse_expression()
                update = AssignNode(id_tok.lexeme, expr, id_tok.line, id_tok.column)
            else:
                update = self._parse_expression()

        if not self._consume(TokenType.RPAREN, "Expected ')' after for clauses"):
            self._synchronize()
            return None

        if not self._check(TokenType.LBRACE):
            tok = self._peek()
            self._error("Expected '{' for loop body", tok.line, tok.column)
            self._synchronize()
            return None

        body = self._parse_block()
        return ForNode(init, condition, update, body, for_tok.line, for_tok.column)

    def _parse_print_stmt(self) -> Optional[PrintNode]:
        print_tok = self._previous()
        if not self._consume(TokenType.LPAREN, "Expected '(' after 'print'"):
            self._synchronize()
            return None

        expressions: List[ASTNode] = []
        if not self._check(TokenType.RPAREN):
            while True:
                expressions.append(self._parse_expression())
                if not self._match(TokenType.COMMA):
                    break

        if not self._consume(TokenType.RPAREN, "Expected ')' after print arguments"):
            self._synchronize()
            return None

        if not self._consume(TokenType.SEMI, "Expected ';' after print statement"):
            self._synchronize()
            return None

        return PrintNode(expressions, print_tok.line, print_tok.column)

    def _parse_return_stmt(self) -> Optional[ReturnNode]:
        ret_tok = self._previous()
        value: Optional[ASTNode] = None
        if not self._check(TokenType.SEMI):
            value = self._parse_expression()

        if not self._consume(TokenType.SEMI, "Expected ';' after return statement"):
            self._synchronize()
            return None

        return ReturnNode(value, ret_tok.line, ret_tok.column)

    def _parse_block(self) -> BlockNode:
        lbrace = self._consume(TokenType.LBRACE, "Expected '{'")
        line = lbrace.line if lbrace else self._peek().line
        col = lbrace.column if lbrace else self._peek().column

        statements: List[ASTNode] = []
        while not self._check(TokenType.RBRACE) and not self._is_at_end():
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)

        self._consume(TokenType.RBRACE, "Expected '}' to close block")
        return BlockNode(statements, line, col)

    def _parse_expr_stmt(self) -> Optional[ASTNode]:
        expr = self._parse_expression()
        if not self._consume(TokenType.SEMI, "Expected ';' after expression statement"):
            self._synchronize()
            return None
        return expr

    # --- EXPRESSION PRECEDENCE CLIMBING ---

    def _parse_expression(self) -> ASTNode:
        return self._parse_logical_or()

    def _parse_logical_or(self) -> ASTNode:
        expr = self._parse_logical_and()
        while self._match(TokenType.OR):
            op_tok = self._previous()
            right = self._parse_logical_and()
            expr = BinaryOpNode(expr, op_tok.lexeme, right, op_tok.line, op_tok.column)
        return expr

    def _parse_logical_and(self) -> ASTNode:
        expr = self._parse_equality()
        while self._match(TokenType.AND):
            op_tok = self._previous()
            right = self._parse_equality()
            expr = BinaryOpNode(expr, op_tok.lexeme, right, op_tok.line, op_tok.column)
        return expr

    def _parse_equality(self) -> ASTNode:
        expr = self._parse_relational()
        while self._match(TokenType.EQEQ, TokenType.NEQ):
            op_tok = self._previous()
            right = self._parse_relational()
            expr = BinaryOpNode(expr, op_tok.lexeme, right, op_tok.line, op_tok.column)
        return expr

    def _parse_relational(self) -> ASTNode:
        expr = self._parse_additive()
        while self._match(TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE):
            op_tok = self._previous()
            right = self._parse_additive()
            expr = BinaryOpNode(expr, op_tok.lexeme, right, op_tok.line, op_tok.column)
        return expr

    def _parse_additive(self) -> ASTNode:
        expr = self._parse_multiplicative()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op_tok = self._previous()
            right = self._parse_multiplicative()
            expr = BinaryOpNode(expr, op_tok.lexeme, right, op_tok.line, op_tok.column)
        return expr

    def _parse_multiplicative(self) -> ASTNode:
        expr = self._parse_unary()
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_tok = self._previous()
            right = self._parse_unary()
            expr = BinaryOpNode(expr, op_tok.lexeme, right, op_tok.line, op_tok.column)
        return expr

    def _parse_unary(self) -> ASTNode:
        if self._match(TokenType.NOT, TokenType.MINUS):
            op_tok = self._previous()
            operand = self._parse_unary()
            return UnaryOpNode(op_tok.lexeme, operand, op_tok.line, op_tok.column)
        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        tok = self._peek()

        if self._match(TokenType.INT_LIT):
            return LiteralNode(tok.value, "int", tok.line, tok.column)

        if self._match(TokenType.FLOAT_LIT):
            return LiteralNode(tok.value, "float", tok.line, tok.column)

        if self._match(TokenType.STRING_LIT):
            return LiteralNode(tok.value, "string", tok.line, tok.column)

        if self._match(TokenType.BOOL_LIT):
            return LiteralNode(tok.value, "bool", tok.line, tok.column)

        if self._match(TokenType.IDENTIFIER):
            name = tok.lexeme
            # Function call: identifier ( args... )
            if self._match(TokenType.LPAREN):
                args: List[ASTNode] = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._parse_expression())
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "Expected ')' after arguments")
                return CallNode(name, args, tok.line, tok.column)
            return IdentifierNode(name, tok.line, tok.column)

        if self._match(TokenType.LPAREN):
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN, "Expected ')' after expression")
            return expr

        if tok.type in (TokenType.SEMI, TokenType.RBRACE, TokenType.EOF):
            self._error(f"Expected expression before '{tok.lexeme or tok.type.value}'", tok.line, tok.column)
            return LiteralNode(0, "int", tok.line, tok.column)

        # If we reach here, unexpected token
        self._advance()
        self._error(f"Unexpected token '{tok.lexeme or tok.type.value}' in expression", tok.line, tok.column)
        return LiteralNode(0, "int", tok.line, tok.column)
