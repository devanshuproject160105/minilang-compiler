"""
Compiler Pipeline Orchestrator for MiniLang.
Coordinates all compilation phases and returns structured, JSON-serializable
telemetry for the visual UI and API endpoints.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from .tokens import Token
from .lexer import Lexer, LexicalError
from .parser import Parser, ParseError
from .semantic import SemanticAnalyzer, SemanticError
from .ast_nodes import ProgramNode, FnDeclNode
from .ir import TACInstruction
from .ir_generator import IRGenerator
from .optimizer import Optimizer
from .codegen import CodeGenerator, BytecodeInstruction
from .vm import VirtualMachine, VMState


@dataclass
class PipelineResult:
    success: bool
    stages: Dict[str, str]  # stage_name -> "success" | "failed" | "skipped"
    first_error: Optional[Dict[str, Any]]
    tokens: List[Dict[str, Any]]
    ast: Optional[Dict[str, Any]]
    symbol_table: Optional[Dict[str, Any]]
    ir: List[Dict[str, Any]]
    optimized_ir: List[Dict[str, Any]]
    optimization_logs: List[Dict[str, Any]]
    bytecode: List[Dict[str, Any]]
    execution: Optional[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "stages": self.stages,
            "first_error": self.first_error,
            "tokens": self.tokens,
            "ast": self.ast,
            "symbol_table": self.symbol_table,
            "ir": self.ir,
            "optimized_ir": self.optimized_ir,
            "optimization_logs": self.optimization_logs,
            "bytecode": self.bytecode,
            "execution": self.execution,
        }


class CompilerPipeline:
    def __init__(self):
        self.lexer: Optional[Lexer] = None
        self.parser: Optional[Parser] = None
        self.analyzer: Optional[SemanticAnalyzer] = None
        self.ir_gen: Optional[IRGenerator] = None
        self.optimizer: Optional[Optimizer] = None
        self.codegen: Optional[CodeGenerator] = None
        self.vm: Optional[VirtualMachine] = None

    def compile(self, source_code: str, execute: bool = False) -> PipelineResult:
        stages_status: Dict[str, str] = {
            "lexer": "pending",
            "parser": "pending",
            "semantic": "pending",
            "ir": "pending",
            "optimizer": "pending",
            "codegen": "pending",
            "vm": "pending",
        }

        # 1. Lexer Stage
        self.lexer = Lexer(source_code)
        tokens, lex_errors = self.lexer.tokenize()
        tokens_dict = [t.to_dict() for t in tokens]

        if lex_errors:
            stages_status["lexer"] = "failed"
            for s in ("parser", "semantic", "ir", "optimizer", "codegen", "vm"):
                stages_status[s] = "skipped"
            return PipelineResult(
                success=False,
                stages=stages_status,
                first_error=lex_errors[0].to_dict(),
                tokens=tokens_dict,
                ast=None,
                symbol_table=None,
                ir=[],
                optimized_ir=[],
                optimization_logs=[],
                bytecode=[],
                execution=None,
            )
        stages_status["lexer"] = "success"

        # 2. Parser Stage
        self.parser = Parser(tokens)
        ast_root, parse_errors = self.parser.parse()

        if parse_errors:
            stages_status["parser"] = "failed"
            for s in ("semantic", "ir", "optimizer", "codegen", "vm"):
                stages_status[s] = "skipped"
            return PipelineResult(
                success=False,
                stages=stages_status,
                first_error=parse_errors[0].to_dict(),
                tokens=tokens_dict,
                ast=ast_root.to_dict() if ast_root else None,
                symbol_table=None,
                ir=[],
                optimized_ir=[],
                optimization_logs=[],
                bytecode=[],
                execution=None,
            )
        stages_status["parser"] = "success"

        # 3. Semantic Analysis Stage
        self.analyzer = SemanticAnalyzer()
        semantic_errors, symbol_table_dump = self.analyzer.analyze(ast_root)

        if semantic_errors:
            stages_status["semantic"] = "failed"
            for s in ("ir", "optimizer", "codegen", "vm"):
                stages_status[s] = "skipped"
            return PipelineResult(
                success=False,
                stages=stages_status,
                first_error=semantic_errors[0].to_dict(),
                tokens=tokens_dict,
                ast=ast_root.to_dict() if ast_root else None,
                symbol_table=symbol_table_dump,
                ir=[],
                optimized_ir=[],
                optimization_logs=[],
                bytecode=[],
                execution=None,
            )
        stages_status["semantic"] = "success"

        # Extract function parameter names for VM frames
        func_params: Dict[str, List[str]] = {}
        for stmt in ast_root.statements:
            if isinstance(stmt, FnDeclNode):
                func_params[stmt.name] = [p["name"] for p in stmt.params]

        # 4. IR Generation Stage
        self.ir_gen = IRGenerator()
        raw_tac = self.ir_gen.generate(ast_root)
        ir_dict = [instr.to_dict(i) for i, instr in enumerate(raw_tac)]
        stages_status["ir"] = "success"

        # 5. Optimization Stage
        self.optimizer = Optimizer()
        optimized_tac, opt_logs = self.optimizer.optimize(raw_tac)
        opt_ir_dict = [instr.to_dict(i) for i, instr in enumerate(optimized_tac)]
        stages_status["optimizer"] = "success"

        # 6. Bytecode Generation Stage
        self.codegen = CodeGenerator()
        bytecode_instrs = self.codegen.generate(optimized_tac)
        bytecode_dict = [instr.to_dict() for instr in bytecode_instrs]
        stages_status["codegen"] = "success"

        # 7. Virtual Machine Stage
        self.vm = VirtualMachine(bytecode_instrs, function_params=func_params)
        exec_result = None

        if execute:
            vm_state = self.vm.run()
            exec_result = vm_state.to_dict()
            stages_status["vm"] = "success" if vm_state.status != "ERROR" else "failed"
            first_err = {"stage": "vm", "message": vm_state.error, "line": 0, "column": 0} if vm_state.error else None
        else:
            stages_status["vm"] = "success"
            first_err = None

        return PipelineResult(
            success=(stages_status["vm"] != "failed"),
            stages=stages_status,
            first_error=first_err,
            tokens=tokens_dict,
            ast=ast_root.to_dict() if ast_root else None,
            symbol_table=symbol_table_dump,
            ir=ir_dict,
            optimized_ir=opt_ir_dict,
            optimization_logs=opt_logs,
            bytecode=bytecode_dict,
            execution=exec_result,
        )

    def step_vm(self, bytecode_dict: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Performs a single step in the VM and returns updated state."""
        if not self.vm:
            return {"status": "ERROR", "error": "VM not initialized. Compile the code first."}
        state = self.vm.step()
        return state.to_dict()
