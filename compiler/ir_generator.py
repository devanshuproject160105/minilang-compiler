"""
Intermediate Representation (IR) Generator for MiniLang.
Translates AST into Three-Address Code (TAC) with temporary variables and control-flow labels.
"""

from typing import List, Optional, Any, Dict
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
from .ir import TACInstruction, OpCode


class IRGenerator:
    def __init__(self):
        self.instructions: List[TACInstruction] = []
        self.temp_counter: int = 0
        self.label_counter: int = 0

    def _new_temp(self) -> str:
        t = f"t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def _new_label(self, prefix: str = "L") -> str:
        lbl = f"{prefix}{self.label_counter}"
        self.label_counter += 1
        return lbl

    def _emit(self, op: OpCode, arg1: Any = None, arg2: Any = None, result: Any = None, comment: str = "") -> TACInstruction:
        instr = TACInstruction(op, arg1, arg2, result, comment)
        self.instructions.append(instr)
        return instr

    def generate(self, program: ProgramNode) -> List[TACInstruction]:
        """Translates the AST into a list of TAC instructions."""
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0

        # Separate functions and top-level statements
        functions: List[FnDeclNode] = []
        top_level_stmts: List[ASTNode] = []

        for stmt in program.statements:
            if isinstance(stmt, FnDeclNode):
                functions.append(stmt)
            else:
                top_level_stmts.append(stmt)

        # If there are functions and top-level code, jump over functions to main
        if functions and top_level_stmts:
            main_label = self._new_label("main_entry_")
            self._emit(OpCode.JUMP, main_label, comment="Jump to main entry point")

            for fn in functions:
                self._generate_function(fn)

            self._emit(OpCode.LABEL, main_label, comment="Main entry point")
            for stmt in top_level_stmts:
                self._generate_statement(stmt)
        elif functions:
            for fn in functions:
                self._generate_function(fn)
        else:
            for stmt in top_level_stmts:
                self._generate_statement(stmt)

        return self.instructions

    def _generate_function(self, node: FnDeclNode):
        self._emit(OpCode.FUNC_BEGIN, node.name)
        self._generate_block(node.body)
        # Ensure a final return exists
        if not self.instructions or self.instructions[-1].op != OpCode.RETURN:
            self._emit(OpCode.RETURN, None, comment="Default return")
        self._emit(OpCode.FUNC_END, node.name)

    def _generate_statement(self, node: ASTNode):
        if isinstance(node, VarDeclNode):
            if node.init_expr:
                val = self._generate_expression(node.init_expr)
                self._emit(OpCode.ASSIGN, val, None, node.name)
            else:
                default_val = 0
                if node.type_name == "float":
                    default_val = 0.0
                elif node.type_name == "bool":
                    default_val = False
                elif node.type_name == "string":
                    default_val = '""'
                self._emit(OpCode.ASSIGN, default_val, None, node.name)

        elif isinstance(node, AssignNode):
            val = self._generate_expression(node.expr)
            self._emit(OpCode.ASSIGN, val, None, node.name)

        elif isinstance(node, IfNode):
            cond_val = self._generate_expression(node.condition)
            l_else = self._new_label("else_")
            l_end = self._new_label("endif_")

            self._emit(OpCode.JUMP_IF_FALSE, cond_val, l_else)
            self._generate_statement(node.then_branch)

            if node.else_branch:
                self._emit(OpCode.JUMP, l_end)
                self._emit(OpCode.LABEL, l_else)
                self._generate_statement(node.else_branch)
                self._emit(OpCode.LABEL, l_end)
            else:
                self._emit(OpCode.LABEL, l_else)

        elif isinstance(node, WhileNode):
            l_start = self._new_label("while_start_")
            l_end = self._new_label("while_end_")

            self._emit(OpCode.LABEL, l_start)
            cond_val = self._generate_expression(node.condition)
            self._emit(OpCode.JUMP_IF_FALSE, cond_val, l_end)

            self._generate_statement(node.body)
            self._emit(OpCode.JUMP, l_start)
            self._emit(OpCode.LABEL, l_end)

        elif isinstance(node, ForNode):
            l_start = self._new_label("for_start_")
            l_end = self._new_label("for_end_")

            if node.init:
                self._generate_statement(node.init)

            self._emit(OpCode.LABEL, l_start)
            if node.condition:
                cond_val = self._generate_expression(node.condition)
                self._emit(OpCode.JUMP_IF_FALSE, cond_val, l_end)

            self._generate_statement(node.body)

            if node.update:
                if isinstance(node.update, AssignNode):
                    self._generate_statement(node.update)
                else:
                    self._generate_expression(node.update)

            self._emit(OpCode.JUMP, l_start)
            self._emit(OpCode.LABEL, l_end)

        elif isinstance(node, PrintNode):
            for expr in node.expressions:
                val = self._generate_expression(expr)
                self._emit(OpCode.PRINT, val)

        elif isinstance(node, ReturnNode):
            if node.value:
                val = self._generate_expression(node.value)
                self._emit(OpCode.RETURN, val)
            else:
                self._emit(OpCode.RETURN, None)

        elif isinstance(node, BlockNode):
            self._generate_block(node)

        elif isinstance(node, (BinaryOpNode, UnaryOpNode, CallNode, LiteralNode, IdentifierNode)):
            self._generate_expression(node)

    def _generate_block(self, node: BlockNode):
        for stmt in node.statements:
            self._generate_statement(stmt)

    def _generate_expression(self, node: ASTNode) -> Any:
        if isinstance(node, LiteralNode):
            if node.literal_type == "string":
                return f'"{node.value}"'
            elif node.literal_type == "bool":
                return "true" if node.value else "false"
            return node.value

        if isinstance(node, IdentifierNode):
            return node.name

        if isinstance(node, CallNode):
            arg_temps = []
            for arg in node.args:
                arg_val = self._generate_expression(arg)
                arg_temps.append(arg_val)

            for arg_val in arg_temps:
                self._emit(OpCode.PARAM, arg_val)

            ret_temp = self._new_temp() if node.inferred_type != "void" else None
            self._emit(OpCode.CALL, node.callee, len(arg_temps), ret_temp)
            return ret_temp

        if isinstance(node, UnaryOpNode):
            operand_val = self._generate_expression(node.operand)
            temp = self._new_temp()
            if node.op == "-":
                self._emit(OpCode.NEG, operand_val, None, temp)
            elif node.op == "!":
                self._emit(OpCode.NOT, operand_val, None, temp)
            return temp

        if isinstance(node, BinaryOpNode):
            left_val = self._generate_expression(node.left)
            right_val = self._generate_expression(node.right)
            temp = self._new_temp()

            op_map = {
                "+": OpCode.ADD,
                "-": OpCode.SUB,
                "*": OpCode.MUL,
                "/": OpCode.DIV,
                "%": OpCode.MOD,
                "==": OpCode.EQ,
                "!=": OpCode.NEQ,
                "<": OpCode.LT,
                "<=": OpCode.LTE,
                ">": OpCode.GT,
                ">=": OpCode.GTE,
                "&&": OpCode.AND,
                "||": OpCode.OR,
            }

            ir_op = op_map.get(node.op, OpCode.ADD)
            self._emit(ir_op, left_val, right_val, temp)
            return temp

        return 0
