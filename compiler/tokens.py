"""
Token definitions and Token class for MiniLang.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional, Dict


class TokenType(Enum):
    # Keywords
    LET = "LET"
    FN = "FN"
    RETURN = "RETURN"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    FOR = "FOR"
    PRINT = "PRINT"
    
    # Types
    TYPE_INT = "TYPE_INT"
    TYPE_FLOAT = "TYPE_FLOAT"
    TYPE_BOOL = "TYPE_BOOL"
    TYPE_STRING = "TYPE_STRING"
    TYPE_VOID = "TYPE_VOID"
    
    # Literals
    INT_LIT = "INT_LIT"
    FLOAT_LIT = "FLOAT_LIT"
    STRING_LIT = "STRING_LIT"
    BOOL_LIT = "BOOL_LIT"
    IDENTIFIER = "IDENTIFIER"
    
    # Arithmetic Operators
    PLUS = "PLUS"           # +
    MINUS = "MINUS"         # -
    STAR = "STAR"           # *
    SLASH = "SLASH"         # /
    PERCENT = "PERCENT"     # %
    
    # Comparison Operators
    EQEQ = "EQEQ"           # ==
    NEQ = "NEQ"             # !=
    LT = "LT"               # <
    LTE = "LTE"             # <=
    GT = "GT"               # >
    GTE = "GTE"             # >=
    
    # Logical Operators
    AND = "AND"             # &&
    OR = "OR"               # ||
    NOT = "NOT"             # !
    
    # Assignment & Punctuation
    ASSIGN = "ASSIGN"       # =
    LPAREN = "LPAREN"       # (
    RPAREN = "RPAREN"       # )
    LBRACE = "LBRACE"       # {
    RBRACE = "RBRACE"       # }
    SEMI = "SEMI"           # ;
    COLON = "COLON"         # :
    COMMA = "COMMA"         # ,
    ARROW = "ARROW"         # ->
    
    # End of File / Errors
    EOF = "EOF"
    ERROR = "ERROR"


KEYWORDS: Dict[str, TokenType] = {
    "let": TokenType.LET,
    "fn": TokenType.FN,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "print": TokenType.PRINT,
    "int": TokenType.TYPE_INT,
    "float": TokenType.TYPE_FLOAT,
    "bool": TokenType.TYPE_BOOL,
    "string": TokenType.TYPE_STRING,
    "void": TokenType.TYPE_VOID,
    "true": TokenType.BOOL_LIT,
    "false": TokenType.BOOL_LIT,
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int
    lexeme: str = ""

    def __post_init__(self):
        if not self.lexeme:
            self.lexeme = str(self.value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "value": self.value,
            "lexeme": self.lexeme,
            "line": self.line,
            "column": self.column,
        }

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"
