"""
Three-Address Code (TAC) representation and Instruction data model for MiniLang.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any, Dict


class OpCode(Enum):
    ASSIGN = "ASSIGN"
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    MOD = "MOD"
    EQ = "EQ"
    NEQ = "NEQ"
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    NEG = "NEG"
    LABEL = "LABEL"
    JUMP = "JUMP"
    JUMP_IF_FALSE = "JUMP_IF_FALSE"
    JUMP_IF_TRUE = "JUMP_IF_TRUE"
    PARAM = "PARAM"
    CALL = "CALL"
    RETURN = "RETURN"
    PRINT = "PRINT"
    FUNC_BEGIN = "FUNC_BEGIN"
    FUNC_END = "FUNC_END"


@dataclass
class TACInstruction:
    op: OpCode
    arg1: Any = None
    arg2: Any = None
    result: Any = None
    comment: str = ""

    def to_text(self) -> str:
        """Returns standard readable TAC format."""
        if self.op == OpCode.LABEL:
            return f"{self.arg1}:"
        elif self.op == OpCode.ASSIGN:
            return f"{self.result} = {self.arg1}"
        elif self.op in (OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD):
            sym = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "MOD": "%"}[self.op.value]
            return f"{self.result} = {self.arg1} {sym} {self.arg2}"
        elif self.op in (OpCode.EQ, OpCode.NEQ, OpCode.LT, OpCode.LTE, OpCode.GT, OpCode.GTE):
            sym = {"EQ": "==", "NEQ": "!=", "LT": "<", "LTE": "<=", "GT": ">", "GTE": ">="}[self.op.value]
            return f"{self.result} = {self.arg1} {sym} {self.arg2}"
        elif self.op in (OpCode.AND, OpCode.OR):
            sym = {"AND": "&&", "OR": "||"}[self.op.value]
            return f"{self.result} = {self.arg1} {sym} {self.arg2}"
        elif self.op == OpCode.NOT:
            return f"{self.result} = !{self.arg1}"
        elif self.op == OpCode.NEG:
            return f"{self.result} = -{self.arg1}"
        elif self.op == OpCode.JUMP:
            return f"goto {self.arg1}"
        elif self.op == OpCode.JUMP_IF_FALSE:
            return f"if_false {self.arg1} goto {self.arg2}"
        elif self.op == OpCode.JUMP_IF_TRUE:
            return f"if_true {self.arg1} goto {self.arg2}"
        elif self.op == OpCode.PARAM:
            return f"param {self.arg1}"
        elif self.op == OpCode.CALL:
            if self.result:
                return f"{self.result} = call {self.arg1}, {self.arg2}"
            return f"call {self.arg1}, {self.arg2}"
        elif self.op == OpCode.RETURN:
            if self.arg1 is not None:
                return f"return {self.arg1}"
            return "return"
        elif self.op == OpCode.PRINT:
            return f"print {self.arg1}"
        elif self.op == OpCode.FUNC_BEGIN:
            return f"func_begin {self.arg1}"
        elif self.op == OpCode.FUNC_END:
            return f"func_end {self.arg1}"
        return f"{self.op.value} {self.arg1} {self.arg2} -> {self.result}"

    def to_dict(self, index: int = 0) -> Dict[str, Any]:
        return {
            "index": index,
            "op": self.op.value,
            "arg1": str(self.arg1) if self.arg1 is not None else None,
            "arg2": str(self.arg2) if self.arg2 is not None else None,
            "result": str(self.result) if self.result is not None else None,
            "text": self.to_text(),
            "comment": self.comment,
        }
