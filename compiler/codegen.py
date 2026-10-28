"""
Stack-based Bytecode Generator for MiniLang.
Translates TAC IR into compact virtual machine bytecode instructions
with two-pass label resolution and metadata for visual stepping.
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from .ir import TACInstruction, OpCode


class BytecodeOp(Enum):
    PUSH_CONST = "PUSH_CONST"
    LOAD_VAR = "LOAD_VAR"
    STORE_VAR = "STORE_VAR"
    BINARY_ADD = "BINARY_ADD"
    BINARY_SUB = "BINARY_SUB"
    BINARY_MUL = "BINARY_MUL"
    BINARY_DIV = "BINARY_DIV"
    BINARY_MOD = "BINARY_MOD"
    COMPARE_EQ = "COMPARE_EQ"
    COMPARE_NE = "COMPARE_NE"
    COMPARE_LT = "COMPARE_LT"
    COMPARE_LE = "COMPARE_LE"
    COMPARE_GT = "COMPARE_GT"
    COMPARE_GE = "COMPARE_GE"
    LOGICAL_AND = "LOGICAL_AND"
    LOGICAL_OR = "LOGICAL_OR"
    LOGICAL_NOT = "LOGICAL_NOT"
    NEGATE = "NEGATE"
    JUMP = "JUMP"
    JUMP_IF_FALSE = "JUMP_IF_FALSE"
    JUMP_IF_TRUE = "JUMP_IF_TRUE"
    CALL_FUNC = "CALL_FUNC"
    RETURN_VAL = "RETURN_VAL"
    RETURN_VOID = "RETURN_VOID"
    PRINT_VAL = "PRINT_VAL"
    HALT = "HALT"


@dataclass
class BytecodeInstruction:
    ip: int
    op: BytecodeOp
    arg1: Any = None
    arg2: Any = None
    comment: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "op": self.op.value,
            "arg1": self.arg1,
            "arg2": self.arg2,
            "text": self.__str__(),
            "comment": self.comment,
        }

    def __str__(self) -> str:
        s = f"{self.ip:04d}: {self.op.value}"
        if self.arg1 is not None:
            s += f" {self.arg1!r}" if isinstance(self.arg1, str) and not self.arg1.isdigit() else f" {self.arg1}"
        if self.arg2 is not None:
            s += f", {self.arg2}"
        if self.comment:
            s += f"  ; {self.comment}"
        return s


class CodeGenerator:
    def __init__(self):
        self.instructions: List[BytecodeInstruction] = []
        self.label_map: Dict[str, int] = {}

    def _is_var(self, val: Any) -> bool:
        if isinstance(val, str):
            if val.startswith('"') and val.endswith('"'):
                return False
            if val in ("true", "false"):
                return False
            try:
                float(val)
                return False
            except ValueError:
                return True
        return False

    def _to_const(self, val: Any) -> Any:
        if isinstance(val, (int, float, bool)):
            return val
        if isinstance(val, str):
            if val == "true":
                return True
            if val == "false":
                return False
            if val.startswith('"') and val.endswith('"'):
                return val[1:-1]
            try:
                if "." in val:
                    return float(val)
                return int(val)
            except ValueError:
                return val
        return val

    def generate(self, tac_instructions: List[TACInstruction]) -> List[BytecodeInstruction]:
        """Translates TAC instructions into stack bytecode with resolved branch labels."""
        raw_ops: List[Dict[str, Any]] = []
        self.label_map = {}

        # Track function entry labels
        for instr in tac_instructions:
            if instr.op == OpCode.FUNC_BEGIN:
                self.label_map[f"func_{instr.arg1}"] = len(raw_ops)
            elif instr.op == OpCode.LABEL:
                self.label_map[str(instr.arg1)] = len(raw_ops)
            elif instr.op == OpCode.ASSIGN:
                # Load arg1, store in result
                if self._is_var(instr.arg1):
                    raw_ops.append({"op": BytecodeOp.LOAD_VAR, "arg1": instr.arg1, "comment": f"Load {instr.arg1}"})
                else:
                    raw_ops.append({"op": BytecodeOp.PUSH_CONST, "arg1": self._to_const(instr.arg1), "comment": f"Push {instr.arg1}"})
                raw_ops.append({"op": BytecodeOp.STORE_VAR, "arg1": instr.result, "comment": f"Store into {instr.result}"})

            elif instr.op in (
                OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD,
                OpCode.EQ, OpCode.NEQ, OpCode.LT, OpCode.LTE, OpCode.GT, OpCode.GTE,
                OpCode.AND, OpCode.OR,
            ):
                # Push arg1, push arg2, apply op, store into result
                if self._is_var(instr.arg1):
                    raw_ops.append({"op": BytecodeOp.LOAD_VAR, "arg1": instr.arg1})
                else:
                    raw_ops.append({"op": BytecodeOp.PUSH_CONST, "arg1": self._to_const(instr.arg1)})

                if self._is_var(instr.arg2):
                    raw_ops.append({"op": BytecodeOp.LOAD_VAR, "arg1": instr.arg2})
                else:
                    raw_ops.append({"op": BytecodeOp.PUSH_CONST, "arg1": self._to_const(instr.arg2)})

                op_trans = {
                    OpCode.ADD: BytecodeOp.BINARY_ADD,
                    OpCode.SUB: BytecodeOp.BINARY_SUB,
                    OpCode.MUL: BytecodeOp.BINARY_MUL,
                    OpCode.DIV: BytecodeOp.BINARY_DIV,
                    OpCode.MOD: BytecodeOp.BINARY_MOD,
                    OpCode.EQ: BytecodeOp.COMPARE_EQ,
                    OpCode.NEQ: BytecodeOp.COMPARE_NE,
                    OpCode.LT: BytecodeOp.COMPARE_LT,
                    OpCode.LTE: BytecodeOp.COMPARE_LE,
                    OpCode.GT: BytecodeOp.COMPARE_GT,
                    OpCode.GTE: BytecodeOp.COMPARE_GE,
                    OpCode.AND: BytecodeOp.LOGICAL_AND,
                    OpCode.OR: BytecodeOp.LOGICAL_OR,
                }
                raw_ops.append({"op": op_trans[instr.op]})
                raw_ops.append({"op": BytecodeOp.STORE_VAR, "arg1": instr.result})

            elif instr.op == OpCode.NEG:
                if self._is_var(instr.arg1):
                    raw_ops.append({"op": BytecodeOp.LOAD_VAR, "arg1": instr.arg1})
                else:
                    raw_ops.append({"op": BytecodeOp.PUSH_CONST, "arg1": self._to_const(instr.arg1)})
                raw_ops.append({"op": BytecodeOp.NEGATE})
                raw_ops.append({"op": BytecodeOp.STORE_VAR, "arg1": instr.result})

            elif instr.op == OpCode.NOT:
                if self._is_var(instr.arg1):
                    raw_ops.append({"op": BytecodeOp.LOAD_VAR, "arg1": instr.arg1})
                else:
                    raw_ops.append({"op": BytecodeOp.PUSH_CONST, "arg1": self._to_const(instr.arg1)})
                raw_ops.append({"op": BytecodeOp.LOGICAL_NOT})
                raw_ops.append({"op": BytecodeOp.STORE_VAR, "arg1": instr.result})

            elif instr.op == OpCode.PRINT:
                if self._is_var(instr.arg1):
                    raw_ops.append({"op": BytecodeOp.LOAD_VAR, "arg1": instr.arg1})
                else:
                    raw_ops.append({"op": BytecodeOp.PUSH_CONST, "arg1": self._to_const(instr.arg1)})
                raw_ops.append({"op": BytecodeOp.PRINT_VAL, "arg1": 1})

            elif instr.op == OpCode.JUMP:
                raw_ops.append({"op": BytecodeOp.JUMP, "target_label": str(instr.arg1)})

            elif instr.op == OpCode.JUMP_IF_FALSE:
                if self._is_var(instr.arg1):
                    raw_ops.append({"op": BytecodeOp.LOAD_VAR, "arg1": instr.arg1})
                else:
                    raw_ops.append({"op": BytecodeOp.PUSH_CONST, "arg1": self._to_const(instr.arg1)})
                raw_ops.append({"op": BytecodeOp.JUMP_IF_FALSE, "target_label": str(instr.arg2)})

            elif instr.op == OpCode.JUMP_IF_TRUE:
                if self._is_var(instr.arg1):
                    raw_ops.append({"op": BytecodeOp.LOAD_VAR, "arg1": instr.arg1})
                else:
                    raw_ops.append({"op": BytecodeOp.PUSH_CONST, "arg1": self._to_const(instr.arg1)})
                raw_ops.append({"op": BytecodeOp.JUMP_IF_TRUE, "target_label": str(instr.arg2)})

            elif instr.op == OpCode.PARAM:
                if self._is_var(instr.arg1):
                    raw_ops.append({"op": BytecodeOp.LOAD_VAR, "arg1": instr.arg1})
                else:
                    raw_ops.append({"op": BytecodeOp.PUSH_CONST, "arg1": self._to_const(instr.arg1)})

            elif instr.op == OpCode.CALL:
                raw_ops.append({
                    "op": BytecodeOp.CALL_FUNC,
                    "arg1": instr.arg1,
                    "arg2": instr.arg2,
                    "ret_var": instr.result
                })
                if instr.result:
                    raw_ops.append({"op": BytecodeOp.STORE_VAR, "arg1": instr.result})

            elif instr.op == OpCode.RETURN:
                if instr.arg1 is not None:
                    if self._is_var(instr.arg1):
                        raw_ops.append({"op": BytecodeOp.LOAD_VAR, "arg1": instr.arg1})
                    else:
                        raw_ops.append({"op": BytecodeOp.PUSH_CONST, "arg1": self._to_const(instr.arg1)})
                    raw_ops.append({"op": BytecodeOp.RETURN_VAL})
                else:
                    raw_ops.append({"op": BytecodeOp.RETURN_VOID})

            elif instr.op == OpCode.FUNC_END:
                # Fallback return
                raw_ops.append({"op": BytecodeOp.RETURN_VOID})

        # Append final HALT
        raw_ops.append({"op": BytecodeOp.HALT, "comment": "End of program"})

        # Pass 2: Resolve jump targets to concrete IP numbers
        self.instructions = []
        for ip, op_dict in enumerate(raw_ops):
            op = op_dict["op"]
            arg1 = op_dict.get("arg1")
            arg2 = op_dict.get("arg2")
            comment = op_dict.get("comment", "")

            if op in (BytecodeOp.JUMP, BytecodeOp.JUMP_IF_FALSE, BytecodeOp.JUMP_IF_TRUE):
                target_label = op_dict.get("target_label", "")
                resolved_ip = self.label_map.get(target_label, len(raw_ops) - 1)
                arg1 = resolved_ip
                comment = f"Jump to {target_label} (IP: {resolved_ip})"

            elif op == BytecodeOp.CALL_FUNC:
                func_name = str(arg1)
                target_ip = self.label_map.get(f"func_{func_name}", 0)
                comment = f"Call {func_name} at IP {target_ip}"

            self.instructions.append(BytecodeInstruction(ip, op, arg1, arg2, comment))

        return self.instructions
