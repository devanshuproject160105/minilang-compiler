"""
Semantic Analyzer and Scoped Symbol Table for MiniLang.
Enforces type safety, scope rules, function contracts, and control-flow constraints.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Tuple
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
class SemanticError:
    message: str
    line: int
    column: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": "semantic",
            "message": self.message,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class Symbol:
    name: str
    type_name: str
    kind: str  # "variable", "parameter", "function"
    line: int
    scope_level: int
    params: Optional[List[Dict[str, str]]] = None  # for functions
    return_type: Optional[str] = None             # for functions

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "name": self.name,
            "type": self.type_name,
            "kind": self.kind,
            "line": self.line,
            "scope_level": self.scope_level,
        }
        if self.kind == "function":
            data["params"] = self.params
            data["return_type"] = self.return_type
        return data


class SymbolTable:
    def __init__(self, name: str, level: int = 0, parent: Optional["SymbolTable"] = None):
        self.name: str = name
        self.level: int = level
        self.parent: Optional["SymbolTable"] = parent
        self.symbols: Dict[str, Symbol] = {}
        self.children: List["SymbolTable"] = []

        if parent:
            parent.children.append(self)

    def define(self, symbol: Symbol) -> bool:
        """Defines a symbol in the current scope. Returns False if already declared in this exact scope."""
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        """Resolves symbol in current scope or climbs parent scopes."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_current(self, name: str) -> Optional[Symbol]:
        """Looks up symbol in current scope only."""
        return self.symbols.get(name)

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable hierarchical structure for UI."""
        return {
            "scope_name": self.name,
            "level": self.level,
            "symbols": [sym.to_dict() for sym in self.symbols.values()],
            "children": [child.to_dict() for child in self.children],
        }


class SemanticAnalyzer:
    def __init__(self):
        self.global_scope = SymbolTable("Global Scope", level=0)
        self.current_scope: SymbolTable = self.global_scope
        self.all_scopes: List[SymbolTable] = [self.global_scope]
        self.errors: List[SemanticError] = []
        self.current_function: Optional[FnDeclNode] = None

    def _enter_scope(self, name: str) -> SymbolTable:
        new_scope = SymbolTable(name, level=self.current_scope.level + 1, parent=self.current_scope)
        self.all_scopes.append(new_scope)
        self.current_scope = new_scope
        return new_scope

    def _exit_scope(self):
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def _error(self, message: str, line: int, column: int):
        self.errors.append(SemanticError(message, line, column))

    def _types_compatible(self, target_type: str, source_type: str) -> bool:
        if target_type == source_type:
            return True
        # Allow implicit widening from int to float
        if target_type == "float" and source_type == "int":
            return True
        return False

    def analyze(self, program: ProgramNode) -> Tuple[List[SemanticError], Dict[str, Any]]:
        self.errors = []
        self.global_scope = SymbolTable("Global Scope", level=0)
        self.current_scope = self.global_scope
        self.all_scopes = [self.global_scope]
        self.current_function = None

        # Pass 1: Register all function signatures first (enables forward calls / mutual recursion)
        for stmt in program.statements:
            if isinstance(stmt, FnDeclNode):
                fn_sym = Symbol(
                    name=stmt.name,
                    type_name=f"fn({', '.join([p['type'] for p in stmt.params])}) -> {stmt.return_type}",
                    kind="function",
                    line=stmt.line,
                    scope_level=0,
                    params=stmt.params,
                    return_type=stmt.return_type,
                )
                if not self.global_scope.define(fn_sym):
                    self._error(f"Redeclaration of function '{stmt.name}'", stmt.line, stmt.column)

        # Pass 2: Type check and analyze all statements
        for stmt in program.statements:
            self._analyze_statement(stmt)

        symbol_table_dump = self.global_scope.to_dict()
        return self.errors, symbol_table_dump

    def _analyze_statement(self, node: ASTNode):
        if isinstance(node, VarDeclNode):
            self._analyze_var_decl(node)
        elif isinstance(node, AssignNode):
            self._analyze_assign(node)
        elif isinstance(node, IfNode):
            self._analyze_if(node)
        elif isinstance(node, WhileNode):
            self._analyze_while(node)
        elif isinstance(node, ForNode):
            self._analyze_for(node)
        elif isinstance(node, PrintNode):
            self._analyze_print(node)
        elif isinstance(node, ReturnNode):
            self._analyze_return(node)
        elif isinstance(node, FnDeclNode):
            self._analyze_function(node)
        elif isinstance(node, BlockNode):
            self._analyze_block(node)
        elif isinstance(node, (BinaryOpNode, UnaryOpNode, CallNode, LiteralNode, IdentifierNode)):
            self._analyze_expression(node)

    def _analyze_var_decl(self, node: VarDeclNode):
        init_type: Optional[str] = None
        if node.init_expr:
            init_type = self._analyze_expression(node.init_expr)

        final_type: str = "int"
        if node.type_name:
            final_type = node.type_name
            if init_type and not self._types_compatible(final_type, init_type):
                self._error(
                    f"Type mismatch in declaration of '{node.name}': declared as '{final_type}' but initialized with '{init_type}'",
                    node.line,
                    node.column,
                )
        elif init_type:
            final_type = init_type
        else:
            self._error(
                f"Variable '{node.name}' declared without type annotation or initializer",
                node.line,
                node.column,
            )

        node.inferred_type = final_type
        sym = Symbol(
            name=node.name,
            type_name=final_type,
            kind="variable",
            line=node.line,
            scope_level=self.current_scope.level,
        )

        if not self.current_scope.define(sym):
            self._error(
                f"Redeclaration of variable '{node.name}' in the same scope",
                node.line,
                node.column,
            )

    def _analyze_assign(self, node: AssignNode):
        expr_type = self._analyze_expression(node.expr)
        sym = self.current_scope.lookup(node.name)

        if not sym:
            self._error(f"Assignment to undefined variable '{node.name}'", node.line, node.column)
            node.inferred_type = expr_type
            return

        if sym.kind == "function":
            self._error(f"Cannot assign to function '{node.name}'", node.line, node.column)
            return

        if expr_type and not self._types_compatible(sym.type_name, expr_type):
            self._error(
                f"Cannot assign value of type '{expr_type}' to variable '{node.name}' of type '{sym.type_name}'",
                node.line,
                node.column,
            )

        node.inferred_type = sym.type_name

    def _analyze_if(self, node: IfNode):
        cond_type = self._analyze_expression(node.condition)
        if cond_type != "bool":
            self._error(f"Condition in 'if' statement must be 'bool', got '{cond_type}'", node.line, node.column)

        self._analyze_statement(node.then_branch)
        if node.else_branch:
            self._analyze_statement(node.else_branch)

    def _analyze_while(self, node: WhileNode):
        cond_type = self._analyze_expression(node.condition)
        if cond_type != "bool":
            self._error(f"Condition in 'while' statement must be 'bool', got '{cond_type}'", node.line, node.column)

        self._analyze_statement(node.body)

    def _analyze_for(self, node: ForNode):
        self._enter_scope(f"For Scope (L{node.line})")
        if node.init:
            self._analyze_statement(node.init)
        if node.condition:
            cond_type = self._analyze_expression(node.condition)
            if cond_type != "bool":
                self._error(f"Condition in 'for' loop must be 'bool', got '{cond_type}'", node.line, node.column)
        if node.update:
            if isinstance(node.update, AssignNode):
                self._analyze_assign(node.update)
            else:
                self._analyze_expression(node.update)

        self._analyze_statement(node.body)
        self._exit_scope()

    def _analyze_print(self, node: PrintNode):
        for expr in node.expressions:
            self._analyze_expression(expr)
        node.inferred_type = "void"

    def _analyze_return(self, node: ReturnNode):
        val_type = "void"
        if node.value:
            val_type = self._analyze_expression(node.value)

        if not self.current_function:
            self._error("Return statement outside of any function", node.line, node.column)
            return

        expected_type = self.current_function.return_type
        if expected_type == "void":
            if node.value is not None:
                self._error("Void function should not return a value", node.line, node.column)
        else:
            if node.value is None:
                self._error(f"Non-void function '{self.current_function.name}' must return a value of type '{expected_type}'", node.line, node.column)
            elif not self._types_compatible(expected_type, val_type):
                self._error(f"Function '{self.current_function.name}' expects return type '{expected_type}', but got '{val_type}'", node.line, node.column)

        node.inferred_type = val_type

    def _analyze_function(self, node: FnDeclNode):
        self.current_function = node
        self._enter_scope(f"fn {node.name}()")

        # Define parameters in function's scope
        for param in node.params:
            p_sym = Symbol(
                name=param["name"],
                type_name=param["type"],
                kind="parameter",
                line=node.line,
                scope_level=self.current_scope.level,
            )
            if not self.current_scope.define(p_sym):
                self._error(f"Duplicate parameter name '{param['name']}' in function '{node.name}'", node.line, node.column)

        # Analyze body
        self._analyze_block(node.body, create_scope=False)

        # Check for missing return if return type is not void
        if node.return_type != "void":
            if not self._has_guaranteed_return(node.body):
                self._error(
                    f"Function '{node.name}' with return type '{node.return_type}' is missing a return statement on all paths",
                    node.line,
                    node.column,
                )

        self._exit_scope()
        self.current_function = None

    def _has_guaranteed_return(self, block: BlockNode) -> bool:
        for stmt in block.statements:
            if isinstance(stmt, ReturnNode):
                return True
            if isinstance(stmt, IfNode):
                if stmt.else_branch:
                    then_ret = False
                    if isinstance(stmt.then_branch, BlockNode):
                        then_ret = self._has_guaranteed_return(stmt.then_branch)
                    elif isinstance(stmt.then_branch, ReturnNode):
                        then_ret = True

                    else_ret = False
                    if isinstance(stmt.else_branch, BlockNode):
                        else_ret = self._has_guaranteed_return(stmt.else_branch)
                    elif isinstance(stmt.else_branch, IfNode):
                        # Else-if chain
                        else_ret = self._has_guaranteed_return(BlockNode([stmt.else_branch], stmt.line, stmt.column))
                    elif isinstance(stmt.else_branch, ReturnNode):
                        else_ret = True

                    if then_ret and else_ret:
                        return True
        return False

    def _analyze_block(self, node: BlockNode, create_scope: bool = True):
        if create_scope:
            self._enter_scope(f"Block (L{node.line})")

        for stmt in node.statements:
            self._analyze_statement(stmt)

        if create_scope:
            self._exit_scope()

    def _analyze_expression(self, node: ASTNode) -> str:
        if isinstance(node, LiteralNode):
            node.inferred_type = node.literal_type
            return node.literal_type

        if isinstance(node, IdentifierNode):
            sym = self.current_scope.lookup(node.name)
            if not sym:
                self._error(f"Use of undeclared variable '{node.name}'", node.line, node.column)
                node.inferred_type = "int"
                return "int"
            node.inferred_type = sym.type_name
            return sym.type_name

        if isinstance(node, CallNode):
            sym = self.current_scope.lookup(node.callee)
            if not sym or sym.kind != "function":
                self._error(f"Call to undeclared function '{node.callee}'", node.line, node.column)
                node.inferred_type = "int"
                return "int"

            expected_params = sym.params or []
            if len(node.args) != len(expected_params):
                self._error(
                    f"Function '{node.callee}' expects {len(expected_params)} arguments, but got {len(node.args)}",
                    node.line,
                    node.column,
                )

            for i, arg in enumerate(node.args):
                arg_type = self._analyze_expression(arg)
                if i < len(expected_params):
                    param_type = expected_params[i]["type"]
                    if not self._types_compatible(param_type, arg_type):
                        self._error(
                            f"Argument {i+1} of '{node.callee}' expects type '{param_type}', but got '{arg_type}'",
                            arg.line,
                            arg.column,
                        )

            node.inferred_type = sym.return_type or "void"
            return node.inferred_type

        if isinstance(node, UnaryOpNode):
            operand_type = self._analyze_expression(node.operand)
            if node.op == "-":
                if operand_type not in ("int", "float"):
                    self._error(f"Unary operator '-' requires numeric operand, got '{operand_type}'", node.line, node.column)
                    node.inferred_type = "int"
                    return "int"
                node.inferred_type = operand_type
                return operand_type
            elif node.op == "!":
                if operand_type != "bool":
                    self._error(f"Logical NOT '!' requires boolean operand, got '{operand_type}'", node.line, node.column)
                node.inferred_type = "bool"
                return "bool"

        if isinstance(node, BinaryOpNode):
            left_type = self._analyze_expression(node.left)
            right_type = self._analyze_expression(node.right)

            # Arithmetic: +, -, *, /, %
            if node.op in ("+", "-", "*", "/"):
                if left_type == "string" and right_type == "string" and node.op == "+":
                    node.inferred_type = "string"
                    return "string"
                if left_type in ("int", "float") and right_type in ("int", "float"):
                    result_type = "float" if ("float" in (left_type, right_type) or node.op == "/") else "int"
                    # In integer division, if both are int and op is '/', let's keep int if we want integer arithmetic, or float.
                    # In MiniLang integer arithmetic: 15 / 4 = 3 (int), or 3.75 (float).
                    # Standard C/Java/Python: if int / int -> let's make int / int = int, float / anything = float
                    if node.op == "/":
                        result_type = "float" if ("float" in (left_type, right_type)) else "int"
                    node.inferred_type = result_type
                    return result_type
                self._error(f"Operator '{node.op}' not supported between '{left_type}' and '{right_type}'", node.line, node.column)
                node.inferred_type = "int"
                return "int"

            if node.op == "%":
                if left_type != "int" or right_type != "int":
                    self._error(f"Modulo operator '%' requires integer operands, got '{left_type}' and '{right_type}'", node.line, node.column)
                node.inferred_type = "int"
                return "int"

            # Comparisons: ==, !=
            if node.op in ("==", "!="):
                if not (self._types_compatible(left_type, right_type) or self._types_compatible(right_type, left_type)):
                    self._error(f"Comparison '{node.op}' cannot compare '{left_type}' and '{right_type}'", node.line, node.column)
                node.inferred_type = "bool"
                return "bool"

            # Relational: <, <=, >, >=
            if node.op in ("<", "<=", ">", ">="):
                if left_type not in ("int", "float") or right_type not in ("int", "float"):
                    self._error(f"Relational operator '{node.op}' requires numeric operands, got '{left_type}' and '{right_type}'", node.line, node.column)
                node.inferred_type = "bool"
                return "bool"

            # Logical: &&, ||
            if node.op in ("&&", "||"):
                if left_type != "bool" or right_type != "bool":
                    self._error(f"Logical operator '{node.op}' requires boolean operands, got '{left_type}' and '{right_type}'", node.line, node.column)
                node.inferred_type = "bool"
                return "bool"

        node.inferred_type = "int"
        return "int"
