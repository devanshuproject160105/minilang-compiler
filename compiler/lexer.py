"""
Lexer (Scanner) for MiniLang.
Converts source code into a stream of tokens with accurate line/column tracking
and robust error recovery for unrecognized characters.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from .tokens import Token, TokenType, KEYWORDS


@dataclass
class LexicalError:
    message: str
    line: int
    column: int
    character: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": "lexer",
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "character": self.character,
        }


class Lexer:
    def __init__(self, source: str):
        self.source: str = source
        self.length: int = len(source)
        self.pos: int = 0
        self.line: int = 1
        self.column: int = 1
        self.tokens: List[Token] = []
        self.errors: List[LexicalError] = []

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx < self.length:
            return self.source[idx]
        return ""

    def _advance(self) -> str:
        if self.pos < self.length:
            ch = self.source[self.pos]
            self.pos += 1
            if ch == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            return ch
        return ""

    def _match(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def tokenize(self) -> Tuple[List[Token], List[LexicalError]]:
        """
        Scans entire source code and returns list of Tokens and list of LexicalErrors.
        Recovers from invalid characters and continues tokenizing.
        """
        self.tokens = []
        self.errors = []
        self.pos = 0
        self.line = 1
        self.column = 1

        while self.pos < self.length:
            start_line = self.line
            start_col = self.column
            ch = self._peek()

            # Whitespace
            if ch in (" ", "\t", "\r", "\n"):
                self._advance()
                continue

            # Single-line comment
            if ch == "/" and self._peek(1) == "/":
                self._advance()  # /
                self._advance()  # /
                while self.pos < self.length and self._peek() != "\n":
                    self._advance()
                continue

            # Numbers (int or float)
            if ch.isdigit():
                self._tokenize_number(start_line, start_col)
                continue

            # Strings
            if ch == '"':
                self._tokenize_string(start_line, start_col)
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == "_":
                self._tokenize_identifier(start_line, start_col)
                continue

            # Multi-character & single-character operators
            if ch == "+":
                self._advance()
                self.tokens.append(Token(TokenType.PLUS, "+", start_line, start_col, "+"))
            elif ch == "-":
                self._advance()
                if self._match(">"):
                    self.tokens.append(Token(TokenType.ARROW, "->", start_line, start_col, "->"))
                else:
                    self.tokens.append(Token(TokenType.MINUS, "-", start_line, start_col, "-"))
            elif ch == "*":
                self._advance()
                self.tokens.append(Token(TokenType.STAR, "*", start_line, start_col, "*"))
            elif ch == "/":
                self._advance()
                self.tokens.append(Token(TokenType.SLASH, "/", start_line, start_col, "/"))
            elif ch == "%":
                self._advance()
                self.tokens.append(Token(TokenType.PERCENT, "%", start_line, start_col, "%"))
            elif ch == "=":
                self._advance()
                if self._match("="):
                    self.tokens.append(Token(TokenType.EQEQ, "==", start_line, start_col, "=="))
                else:
                    self.tokens.append(Token(TokenType.ASSIGN, "=", start_line, start_col, "="))
            elif ch == "!":
                self._advance()
                if self._match("="):
                    self.tokens.append(Token(TokenType.NEQ, "!=", start_line, start_col, "!="))
                else:
                    self.tokens.append(Token(TokenType.NOT, "!", start_line, start_col, "!"))
            elif ch == "<":
                self._advance()
                if self._match("="):
                    self.tokens.append(Token(TokenType.LTE, "<=", start_line, start_col, "<="))
                else:
                    self.tokens.append(Token(TokenType.LT, "<", start_line, start_col, "<"))
            elif ch == ">":
                self._advance()
                if self._match("="):
                    self.tokens.append(Token(TokenType.GTE, ">=", start_line, start_col, ">="))
                else:
                    self.tokens.append(Token(TokenType.GT, ">", start_line, start_col, ">"))
            elif ch == "&":
                self._advance()
                if self._match("&"):
                    self.tokens.append(Token(TokenType.AND, "&&", start_line, start_col, "&&"))
                else:
                    err = LexicalError(f"Unexpected character '&', expected '&&'", start_line, start_col, "&")
                    self.errors.append(err)
            elif ch == "|":
                self._advance()
                if self._match("|"):
                    self.tokens.append(Token(TokenType.OR, "||", start_line, start_col, "||"))
                else:
                    err = LexicalError(f"Unexpected character '|', expected '||'", start_line, start_col, "|")
                    self.errors.append(err)
            elif ch == "(":
                self._advance()
                self.tokens.append(Token(TokenType.LPAREN, "(", start_line, start_col, "("))
            elif ch == ")":
                self._advance()
                self.tokens.append(Token(TokenType.RPAREN, ")", start_line, start_col, ")"))
            elif ch == "{":
                self._advance()
                self.tokens.append(Token(TokenType.LBRACE, "{", start_line, start_col, "{"))
            elif ch == "}":
                self._advance()
                self.tokens.append(Token(TokenType.RBRACE, "}", start_line, start_col, "}"))
            elif ch == ";":
                self._advance()
                self.tokens.append(Token(TokenType.SEMI, ";", start_line, start_col, ";"))
            elif ch == ":":
                self._advance()
                self.tokens.append(Token(TokenType.COLON, ":", start_line, start_col, ":"))
            elif ch == ",":
                self._advance()
                self.tokens.append(Token(TokenType.COMMA, ",", start_line, start_col, ","))
            else:
                # Error recovery: record error and advance
                bad_char = self._advance()
                err = LexicalError(
                    f"Unexpected or invalid character: '{bad_char}'",
                    start_line,
                    start_col,
                    bad_char,
                )
                self.errors.append(err)

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column, ""))
        return self.tokens, self.errors

    def _tokenize_number(self, start_line: int, start_col: int):
        num_str = ""
        is_float = False
        while self.pos < self.length and self._peek().isdigit():
            num_str += self._advance()

        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            num_str += self._advance()  # '.'
            while self.pos < self.length and self._peek().isdigit():
                num_str += self._advance()

        if is_float:
            self.tokens.append(Token(TokenType.FLOAT_LIT, float(num_str), start_line, start_col, num_str))
        else:
            self.tokens.append(Token(TokenType.INT_LIT, int(num_str), start_line, start_col, num_str))

    def _tokenize_string(self, start_line: int, start_col: int):
        self._advance()  # opening "
        content = ""
        closed = False

        while self.pos < self.length:
            ch = self._peek()
            if ch == '"':
                self._advance()
                closed = True
                break
            elif ch == "\n":
                # Unterminated string literal before newline
                err = LexicalError("Unterminated string literal (newline before closing quote)", start_line, start_col, '"')
                self.errors.append(err)
                return
            elif ch == "\\":
                self._advance()  # \
                esc = self._advance()
                if esc == "n":
                    content += "\n"
                elif esc == "t":
                    content += "\t"
                elif esc == "r":
                    content += "\r"
                elif esc == '"':
                    content += '"'
                elif esc == "\\":
                    content += "\\"
                else:
                    content += "\\" + esc
            else:
                content += self._advance()

        if not closed:
            err = LexicalError("Unterminated string literal at end of file", start_line, start_col, '"')
            self.errors.append(err)
            return

        self.tokens.append(Token(TokenType.STRING_LIT, content, start_line, start_col, f'"{content}"'))

    def _tokenize_identifier(self, start_line: int, start_col: int):
        ident = ""
        while self.pos < self.length and (self._peek().isalnum() or self._peek() == "_"):
            ident += self._advance()

        if ident in KEYWORDS:
            tok_type = KEYWORDS[ident]
            if tok_type == TokenType.BOOL_LIT:
                val = True if ident == "true" else False
                self.tokens.append(Token(tok_type, val, start_line, start_col, ident))
            else:
                self.tokens.append(Token(tok_type, ident, start_line, start_col, ident))
        else:
            self.tokens.append(Token(TokenType.IDENTIFIER, ident, start_line, start_col, ident))
