"""
Intermediate Representation Optimizer for MiniLang.
Applies Constant Folding, Constant Propagation, and Dead Code Elimination
while logging precise rule firings for the visual diff inspection tool.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Set, Optional
from .ir import TACInstruction, OpCode


@dataclass
class OptimizationLog:
    rule: str
    original_text: str
    optimized_text: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "original_text": self.original_text,
            "optimized_text": self.optimized_text,
            "description": self.description,
        }


class OptimizationPass:
    def __init__(self):
        self.logs: List[OptimizationLog] = []

    def _is_number(self, val: Any) -> bool:
        if isinstance(val, (int, float)):
            return True
        if isinstance(val, str):
            try:
                float(val)
                return True
            except ValueError:
                return False
        return False

    def _parse_val(self, val: Any) -> Any:
        if isinstance(val, (int, float, bool)):
            return val
        if isinstance(val, str):
            if val == "true":
                return True
            if val == "false":
                return False
            try:
                if "." in val:
                    return float(val)
                return int(val)
            except ValueError:
                return val
        return val


class Optimizer:
    def __init__(self):
        self.logs: List[OptimizationLog] = []

    def optimize(self, instructions: List[TACInstruction]) -> Tuple[List[TACInstruction], List[Dict[str, Any]]]:
        """Runs iterative optimization passes until convergence or max iterations reached."""
        self.logs = []
        current = [TACInstruction(i.op, i.arg1, i.arg2, i.result, i.comment) for i in instructions]

        # Multi-pass fixed-point loop
        max_iterations = 8
        for iteration in range(max_iterations):
            prev_len = len(current)
            prev_texts = [instr.to_text() for instr in current]

            # Pass 1: Constant Propagation
            current = self._constant_propagation(current)

            # Pass 2: Constant Folding
            current = self._constant_folding(current)

            # Pass 3: Branch Simplification
            current = self._branch_simplification(current)

            # Pass 4: Dead Code Elimination
            current = self._dead_code_elimination(current)

            new_texts = [instr.to_text() for instr in current]
            if prev_texts == new_texts:
                break

        logs_data = [log.to_dict() for log in self.logs]
        return current, logs_data

    def _constant_propagation(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        result: List[TACInstruction] = []
        # Local constant map within basic blocks
        const_map: Dict[str, Any] = {}

        for instr in instructions:
            # Invalidate constants across labels, jumps, calls
            if instr.op in (OpCode.LABEL, OpCode.FUNC_BEGIN, OpCode.FUNC_END, OpCode.CALL):
                const_map.clear()

            new_arg1 = instr.arg1
            new_arg2 = instr.arg2
            changed = False

            if isinstance(instr.arg1, str) and instr.arg1 in const_map:
                new_arg1 = const_map[instr.arg1]
                changed = True

            if isinstance(instr.arg2, str) and instr.arg2 in const_map:
                new_arg2 = const_map[instr.arg2]
                changed = True

            new_instr = TACInstruction(instr.op, new_arg1, new_arg2, instr.result, instr.comment)

            if changed:
                self.logs.append(
                    OptimizationLog(
                        rule="Constant Propagation",
                        original_text=instr.to_text(),
                        optimized_text=new_instr.to_text(),
                        description=f"Propagated constant into '{new_instr.to_text()}'",
                    )
                )

            # Track variable assigned to a constant
            if new_instr.op == OpCode.ASSIGN and self._is_constant(new_instr.arg1):
                if isinstance(new_instr.result, str):
                    const_map[new_instr.result] = new_instr.arg1
            elif isinstance(new_instr.result, str) and new_instr.result in const_map:
                # Variable reassigned to non-constant, remove from map
                del const_map[new_instr.result]

            result.append(new_instr)

        return result

    def _constant_folding(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        result: List[TACInstruction] = []

        for instr in instructions:
            if instr.op in (
                OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD,
                OpCode.EQ, OpCode.NEQ, OpCode.LT, OpCode.LTE, OpCode.GT, OpCode.GTE,
                OpCode.AND, OpCode.OR,
            ):
                v1 = self._to_literal_val(instr.arg1)
                v2 = self._to_literal_val(instr.arg2)

                if v1 is not None and v2 is not None:
                    folded_val = self._evaluate_binop(instr.op, v1, v2)
                    if folded_val is not None:
                        new_instr = TACInstruction(OpCode.ASSIGN, folded_val, None, instr.result)
                        self.logs.append(
                            OptimizationLog(
                                rule="Constant Folding",
                                original_text=instr.to_text(),
                                optimized_text=new_instr.to_text(),
                                description=f"Folded {v1} {instr.op.name} {v2} -> {folded_val}",
                            )
                        )
                        result.append(new_instr)
                        continue

            elif instr.op == OpCode.NOT:
                v1 = self._to_literal_val(instr.arg1)
                if isinstance(v1, bool):
                    folded_val = not v1
                    new_instr = TACInstruction(OpCode.ASSIGN, folded_val, None, instr.result)
                    self.logs.append(
                        OptimizationLog(
                            rule="Constant Folding",
                            original_text=instr.to_text(),
                            optimized_text=new_instr.to_text(),
                            description=f"Folded !{v1} -> {folded_val}",
                        )
                    )
                    result.append(new_instr)
                    continue

            elif instr.op == OpCode.NEG:
                v1 = self._to_literal_val(instr.arg1)
                if isinstance(v1, (int, float)):
                    folded_val = -v1
                    new_instr = TACInstruction(OpCode.ASSIGN, folded_val, None, instr.result)
                    self.logs.append(
                        OptimizationLog(
                            rule="Constant Folding",
                            original_text=instr.to_text(),
                            optimized_text=new_instr.to_text(),
                            description=f"Folded -({v1}) -> {folded_val}",
                        )
                    )
                    result.append(new_instr)
                    continue

            result.append(instr)

        return result

    def _branch_simplification(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        result: List[TACInstruction] = []

        for instr in instructions:
            if instr.op == OpCode.JUMP_IF_FALSE:
                cond = self._to_literal_val(instr.arg1)
                if isinstance(cond, bool):
                    if cond is True:
                        # Condition is always true -> branch never taken -> eliminate jump!
                        self.logs.append(
                            OptimizationLog(
                                rule="Dead Branch Elimination",
                                original_text=instr.to_text(),
                                optimized_text="[Eliminated]",
                                description=f"Condition '{instr.arg1}' is always true; jump eliminated",
                            )
                        )
                        continue
                    elif cond is False:
                        # Condition is always false -> jump always taken -> unconditional jump!
                        new_instr = TACInstruction(OpCode.JUMP, instr.arg2, None, None)
                        self.logs.append(
                            OptimizationLog(
                                rule="Branch Simplification",
                                original_text=instr.to_text(),
                                optimized_text=new_instr.to_text(),
                                description=f"Condition '{instr.arg1}' is always false; converted to unconditional jump",
                            )
                        )
                        result.append(new_instr)
                        continue

            elif instr.op == OpCode.JUMP_IF_TRUE:
                cond = self._to_literal_val(instr.arg1)
                if isinstance(cond, bool):
                    if cond is True:
                        new_instr = TACInstruction(OpCode.JUMP, instr.arg2, None, None)
                        self.logs.append(
                            OptimizationLog(
                                rule="Branch Simplification",
                                original_text=instr.to_text(),
                                optimized_text=new_instr.to_text(),
                                description=f"Condition is always true; converted to unconditional jump",
                            )
                        )
                        result.append(new_instr)
                        continue
                    elif cond is False:
                        self.logs.append(
                            OptimizationLog(
                                rule="Dead Branch Elimination",
                                original_text=instr.to_text(),
                                optimized_text="[Eliminated]",
                                description=f"Condition is always false; jump eliminated",
                            )
                        )
                        continue

            result.append(instr)

        return result

    def _dead_code_elimination(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        # Step 1: Eliminate instructions after unconditional jump/return until next label
        reachable_instructions: List[TACInstruction] = []
        is_reachable = True

        for instr in instructions:
            if instr.op in (OpCode.LABEL, OpCode.FUNC_BEGIN, OpCode.FUNC_END):
                is_reachable = True

            if is_reachable:
                reachable_instructions.append(instr)
            else:
                self.logs.append(
                    OptimizationLog(
                        rule="Dead Code Elimination",
                        original_text=instr.to_text(),
                        optimized_text="[Eliminated]",
                        description="Eliminated unreachable instruction following unconditional jump/return",
                    )
                )

            if instr.op in (OpCode.JUMP, OpCode.RETURN):
                is_reachable = False

        # Step 2: Eliminate unused temporary assignments
        # Collect all used names
        used_names: Set[str] = set()
        targeted_labels: Set[str] = set()

        for instr in reachable_instructions:
            if instr.op in (OpCode.JUMP, OpCode.JUMP_IF_FALSE, OpCode.JUMP_IF_TRUE):
                target = instr.arg2 if instr.op != OpCode.JUMP else instr.arg1
                if target:
                    targeted_labels.add(str(target))

            for arg in (instr.arg1, instr.arg2):
                if isinstance(arg, str):
                    used_names.add(arg)

        final_instructions: List[TACInstruction] = []
        for instr in reachable_instructions:
            # If it's an assignment to a temp (e.g. t0, t1) that is NEVER used, eliminate it
            if instr.op in (
                OpCode.ASSIGN, OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV, OpCode.MOD,
                OpCode.EQ, OpCode.NEQ, OpCode.LT, OpCode.LTE, OpCode.GT, OpCode.GTE,
                OpCode.AND, OpCode.OR, OpCode.NOT, OpCode.NEG
            ):
                if isinstance(instr.result, str) and instr.result.startswith("t") and instr.result not in used_names:
                    self.logs.append(
                        OptimizationLog(
                            rule="Dead Code Elimination",
                            original_text=instr.to_text(),
                            optimized_text="[Eliminated]",
                            description=f"Eliminated computation of unused temporary variable '{instr.result}'",
                        )
                    )
                    continue

            # Remove unreferenced labels (excluding function boundaries or main)
            if instr.op == OpCode.LABEL:
                lbl_name = str(instr.arg1)
                if not (lbl_name in targeted_labels or lbl_name.startswith("main")):
                    self.logs.append(
                        OptimizationLog(
                            rule="Dead Label Elimination",
                            original_text=instr.to_text(),
                            optimized_text="[Eliminated]",
                            description=f"Eliminated unreferenced label '{lbl_name}'",
                        )
                    )
                    continue

            final_instructions.append(instr)

        return final_instructions

    def _is_constant(self, val: Any) -> bool:
        if isinstance(val, (int, float, bool)):
            return True
        if isinstance(val, str):
            if val in ("true", "false"):
                return True
            if val.startswith('"') and val.endswith('"'):
                return True
            try:
                float(val)
                return True
            except ValueError:
                return False
        return False

    def _to_literal_val(self, val: Any) -> Optional[Any]:
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
                return None
        return None

    def _evaluate_binop(self, op: OpCode, v1: Any, v2: Any) -> Optional[Any]:
        try:
            if op == OpCode.ADD:
                if isinstance(v1, str) and isinstance(v2, str):
                    return f'"{v1 + v2}"'
                return v1 + v2
            if op == OpCode.SUB:
                return v1 - v2
            if op == OpCode.MUL:
                return v1 * v2
            if op == OpCode.DIV:
                if v2 == 0:
                    return None  # Do not fold division by zero at compile time so runtime error is preserved
                return v1 // v2 if isinstance(v1, int) and isinstance(v2, int) else v1 / v2
            if op == OpCode.MOD:
                if v2 == 0:
                    return None
                return v1 % v2
            if op == OpCode.EQ:
                return v1 == v2
            if op == OpCode.NEQ:
                return v1 != v2
            if op == OpCode.LT:
                return v1 < v2
            if op == OpCode.LTE:
                return v1 <= v2
            if op == OpCode.GT:
                return v1 > v2
            if op == OpCode.GTE:
                return v1 >= v2
            if op == OpCode.AND:
                return bool(v1 and v2)
            if op == OpCode.OR:
                return bool(v1 or v2)
        except Exception:
            return None
        return None
