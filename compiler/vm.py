"""
Stack-based Virtual Machine for MiniLang bytecode execution.
Supports both continuous execution and step-by-step debugging with complete
inspection of the operand stack, call frames, and variable environments.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .codegen import BytecodeInstruction, BytecodeOp


class VMError(Exception):
    def __init__(self, message: str, ip: int = 0):
        super().__init__(message)
        self.message = message
        self.ip = ip


@dataclass
class CallFrame:
    func_name: str
    return_ip: int
    locals: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "func_name": self.func_name,
            "return_ip": self.return_ip,
            "locals": {k: str(v) for k, v in self.locals.items()},
        }


@dataclass
class VMState:
    ip: int
    current_instruction: Optional[Dict[str, Any]]
    stack: List[Any]
    variables: Dict[str, Any]
    call_stack: List[Dict[str, Any]]
    output: List[str]
    status: str  # "READY", "RUNNING", "PAUSED", "FINISHED", "ERROR"
    step_count: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "current_instruction": self.current_instruction,
            "stack": [str(v) if not isinstance(v, (int, float, bool)) else v for v in self.stack],
            "variables": {k: str(v) if not isinstance(v, (int, float, bool)) else v for k, v in self.variables.items()},
            "call_stack": self.call_stack,
            "output": self.output,
            "status": self.status,
            "step_count": self.step_count,
            "error": self.error,
        }


class VirtualMachine:
    def __init__(self, instructions: List[BytecodeInstruction], function_params: Optional[Dict[str, List[str]]] = None, max_steps: int = 20000):
        self.instructions: List[BytecodeInstruction] = instructions
        self.function_params: Dict[str, List[str]] = function_params or {}
        self.max_steps: int = max_steps

        # Execution state
        self.ip: int = 0
        self.stack: List[Any] = []
        self.globals: Dict[str, Any] = {}
        self.call_stack: List[CallFrame] = []
        self.output: List[str] = []
        self.step_count: int = 0
        self.status: str = "READY"
        self.error: Optional[str] = None

        # Build function entry map: func_name -> ip
        self.function_entry_map: Dict[str, int] = {}
        for instr in self.instructions:
            if instr.comment and "Call " in instr.comment and " at IP " in instr.comment:
                # E.g. "Call fibonacci at IP 12"
                parts = instr.comment.split()
                try:
                    f_name = parts[1]
                    f_ip = int(parts[-1])
                    self.function_entry_map[f_name] = f_ip
                except (IndexError, ValueError):
                    pass

    def _get_var(self, name: str) -> Any:
        if self.call_stack and name in self.call_stack[-1].locals:
            return self.call_stack[-1].locals[name]
        if name in self.globals:
            return self.globals[name]
        # Default value for uninitialized variable lookup
        return 0

    def _set_var(self, name: str, value: Any):
        if self.call_stack:
            # If variable already exists in locals or is a temporary/local var
            self.call_stack[-1].locals[name] = value
        else:
            self.globals[name] = value

    def get_state(self) -> VMState:
        curr_instr = self.instructions[self.ip].to_dict() if 0 <= self.ip < len(self.instructions) else None
        # Combined variables for visualization: globals + locals
        combined_vars = dict(self.globals)
        if self.call_stack:
            combined_vars.update(self.call_stack[-1].locals)

        return VMState(
            ip=self.ip,
            current_instruction=curr_instr,
            stack=list(self.stack),
            variables=combined_vars,
            call_stack=[frame.to_dict() for frame in self.call_stack],
            output=list(self.output),
            status=self.status,
            step_count=self.step_count,
            error=self.error,
        )

    def step(self) -> VMState:
        """Executes a single bytecode instruction and returns updated state."""
        if self.status in ("FINISHED", "ERROR"):
            return self.get_state()

        if self.ip >= len(self.instructions):
            self.status = "FINISHED"
            return self.get_state()

        if self.step_count >= self.max_steps:
            self.status = "ERROR"
            self.error = f"Infinite loop detected: exceeded maximum instruction limit ({self.max_steps} steps)"
            return self.get_state()

        instr = self.instructions[self.ip]
        self.step_count += 1
        self.status = "RUNNING"

        try:
            self._execute_instruction(instr)
        except VMError as e:
            self.status = "ERROR"
            self.error = e.message
        except Exception as e:
            self.status = "ERROR"
            self.error = f"Runtime Exception at IP {self.ip}: {str(e)}"

        if self.status == "RUNNING":
            if self.ip >= len(self.instructions):
                self.status = "FINISHED"
            else:
                self.status = "PAUSED"

        return self.get_state()

    def run(self) -> VMState:
        """Runs until completion, error, or step limit."""
        while self.status not in ("FINISHED", "ERROR") and self.ip < len(self.instructions):
            self.step()
        return self.get_state()

    def _execute_instruction(self, instr: BytecodeInstruction):
        op = instr.op

        if op == BytecodeOp.PUSH_CONST:
            self.stack.append(instr.arg1)
            self.ip += 1

        elif op == BytecodeOp.LOAD_VAR:
            val = self._get_var(instr.arg1)
            self.stack.append(val)
            self.ip += 1

        elif op == BytecodeOp.STORE_VAR:
            if not self.stack:
                raise VMError(f"Stack underflow during STORE_VAR '{instr.arg1}'", self.ip)
            val = self.stack.pop()
            self._set_var(instr.arg1, val)
            self.ip += 1

        elif op in (
            BytecodeOp.BINARY_ADD, BytecodeOp.BINARY_SUB, BytecodeOp.BINARY_MUL,
            BytecodeOp.BINARY_DIV, BytecodeOp.BINARY_MOD,
            BytecodeOp.COMPARE_EQ, BytecodeOp.COMPARE_NE, BytecodeOp.COMPARE_LT,
            BytecodeOp.COMPARE_LE, BytecodeOp.COMPARE_GT, BytecodeOp.COMPARE_GE,
            BytecodeOp.LOGICAL_AND, BytecodeOp.LOGICAL_OR,
        ):
            if len(self.stack) < 2:
                raise VMError(f"Stack underflow during binary operation '{op.value}'", self.ip)
            b = self.stack.pop()
            a = self.stack.pop()

            if op == BytecodeOp.BINARY_ADD:
                res = (str(a) + str(b)) if (isinstance(a, str) or isinstance(b, str)) else (a + b)
            elif op == BytecodeOp.BINARY_SUB:
                res = a - b
            elif op == BytecodeOp.BINARY_MUL:
                res = a * b
            elif op == BytecodeOp.BINARY_DIV:
                if b == 0:
                    raise VMError("Runtime Error: Division by zero", self.ip)
                res = a // b if isinstance(a, int) and isinstance(b, int) else a / b
            elif op == BytecodeOp.BINARY_MOD:
                if b == 0:
                    raise VMError("Runtime Error: Modulo by zero", self.ip)
                res = a % b
            elif op == BytecodeOp.COMPARE_EQ:
                res = (a == b)
            elif op == BytecodeOp.COMPARE_NE:
                res = (a != b)
            elif op == BytecodeOp.COMPARE_LT:
                res = (a < b)
            elif op == BytecodeOp.COMPARE_LE:
                res = (a <= b)
            elif op == BytecodeOp.COMPARE_GT:
                res = (a > b)
            elif op == BytecodeOp.COMPARE_GE:
                res = (a >= b)
            elif op == BytecodeOp.LOGICAL_AND:
                res = bool(a and b)
            elif op == BytecodeOp.LOGICAL_OR:
                res = bool(a or b)

            self.stack.append(res)
            self.ip += 1

        elif op == BytecodeOp.NEGATE:
            if not self.stack:
                raise VMError("Stack underflow during NEGATE", self.ip)
            val = self.stack.pop()
            self.stack.append(-val)
            self.ip += 1

        elif op == BytecodeOp.LOGICAL_NOT:
            if not self.stack:
                raise VMError("Stack underflow during LOGICAL_NOT", self.ip)
            val = self.stack.pop()
            self.stack.append(not bool(val))
            self.ip += 1

        elif op == BytecodeOp.JUMP:
            self.ip = int(instr.arg1)

        elif op == BytecodeOp.JUMP_IF_FALSE:
            if not self.stack:
                raise VMError("Stack underflow during JUMP_IF_FALSE", self.ip)
            cond = self.stack.pop()
            if not bool(cond):
                self.ip = int(instr.arg1)
            else:
                self.ip += 1

        elif op == BytecodeOp.JUMP_IF_TRUE:
            if not self.stack:
                raise VMError("Stack underflow during JUMP_IF_TRUE", self.ip)
            cond = self.stack.pop()
            if bool(cond):
                self.ip = int(instr.arg1)
            else:
                self.ip += 1

        elif op == BytecodeOp.PRINT_VAL:
            if not self.stack:
                raise VMError("Stack underflow during PRINT_VAL", self.ip)
            val = self.stack.pop()
            printed_str = str(val).lower() if isinstance(val, bool) else str(val)
            self.output.append(printed_str)
            self.ip += 1

        elif op == BytecodeOp.CALL_FUNC:
            func_name = str(instr.arg1)
            arg_count = int(instr.arg2)

            if len(self.stack) < arg_count:
                raise VMError(f"Stack underflow calling '{func_name}'", self.ip)

            # Pop args in reverse order
            args = []
            for _ in range(arg_count):
                args.insert(0, self.stack.pop())

            # Find target IP
            target_ip = self.function_entry_map.get(func_name)
            if target_ip is None:
                raise VMError(f"Unknown function target '{func_name}'", self.ip)

            # Map arguments to parameter names if known
            param_names = self.function_params.get(func_name, [f"arg_{i}" for i in range(arg_count)])
            frame_locals = {}
            for name, val in zip(param_names, args):
                frame_locals[name] = val

            new_frame = CallFrame(func_name=func_name, return_ip=self.ip + 1, locals=frame_locals)
            self.call_stack.append(new_frame)
            self.ip = target_ip

        elif op == BytecodeOp.RETURN_VAL:
            if not self.stack:
                raise VMError("Stack underflow on return value", self.ip)
            ret_val = self.stack.pop()
            if not self.call_stack:
                # Top level return
                self.status = "FINISHED"
                return
            frame = self.call_stack.pop()
            self.stack.append(ret_val)
            self.ip = frame.return_ip

        elif op == BytecodeOp.RETURN_VOID:
            if not self.call_stack:
                self.status = "FINISHED"
                return
            frame = self.call_stack.pop()
            self.ip = frame.return_ip

        elif op == BytecodeOp.HALT:
            self.status = "FINISHED"
