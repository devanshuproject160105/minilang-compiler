"""
MiniLang Compiler Package
Educational compiler pipeline implementation with visual telemetry.
"""

from .tokens import TokenType, Token
from .lexer import Lexer, LexicalError
from .ast_nodes import ASTNode
from .parser import Parser, ParseError
from .semantic import SemanticAnalyzer, SemanticError, SymbolTable, Symbol
from .ir import TACInstruction, OpCode
from .ir_generator import IRGenerator
from .optimizer import Optimizer, OptimizationPass
from .codegen import CodeGenerator, BytecodeInstruction, BytecodeOp
from .vm import VirtualMachine, VMState, VMError
from .pipeline import CompilerPipeline, PipelineResult

__all__ = [
    "TokenType",
    "Token",
    "Lexer",
    "LexicalError",
    "ASTNode",
    "Parser",
    "ParseError",
    "SemanticAnalyzer",
    "SemanticError",
    "SymbolTable",
    "Symbol",
    "TACInstruction",
    "OpCode",
    "IRGenerator",
    "Optimizer",
    "OptimizationPass",
    "CodeGenerator",
    "BytecodeInstruction",
    "BytecodeOp",
    "VirtualMachine",
    "VMState",
    "VMError",
    "CompilerPipeline",
    "PipelineResult",
]
