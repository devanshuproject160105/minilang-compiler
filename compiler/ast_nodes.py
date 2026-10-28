"""
Abstract Syntax Tree (AST) node definitions for MiniLang.
Provides hierarchical node structures with JSON serialization for D3.js visualization.
"""

from typing import List, Optional, Any, Dict


class ASTNode:
    def __init__(self, line: int = 0, column: int = 0):
        self.line = line
        self.column = column
        self.inferred_type: Optional[str] = None  # Populated by semantic analysis

    def to_dict(self) -> Dict[str, Any]:
        """Returns a dict formatted for D3.js hierarchical tree visualization."""
        return {
            "name": self.__class__.__name__,
            "node_type": self.__class__.__name__,
            "inferred_type": self.inferred_type,
            "line": self.line,
            "column": self.column,
            "children": []
        }


class ProgramNode(ASTNode):
    def __init__(self, statements: List[ASTNode], line: int = 1, column: int = 1):
        super().__init__(line, column)
        self.statements = statements

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": "Program",
            "node_type": "Program",
            "inferred_type": "void",
            "line": self.line,
            "column": self.column,
            "children": [stmt.to_dict() for stmt in self.statements]
        }


class VarDeclNode(ASTNode):
    def __init__(self, name: str, type_name: Optional[str], init_expr: Optional[ASTNode], line: int, column: int):
        super().__init__(line, column)
        self.name = name
        self.type_name = type_name
        self.init_expr = init_expr

    def to_dict(self) -> Dict[str, Any]:
        label = f"let {self.name}"
        if self.type_name:
            label += f": {self.type_name}"
        children = []
        if self.init_expr:
            children.append(self.init_expr.to_dict())
        return {
            "name": label,
            "node_type": "VarDecl",
            "var_name": self.name,
            "declared_type": self.type_name,
            "inferred_type": self.inferred_type,
            "line": self.line,
            "column": self.column,
            "children": children
        }


class AssignNode(ASTNode):
    def __init__(self, name: str, expr: ASTNode, line: int, column: int):
        super().__init__(line, column)
        self.name = name
        self.expr = expr

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": f"Assign: {self.name} =",
            "node_type": "Assign",
            "var_name": self.name,
            "inferred_type": self.inferred_type,
            "line": self.line,
            "column": self.column,
            "children": [self.expr.to_dict()]
        }


class BlockNode(ASTNode):
    def __init__(self, statements: List[ASTNode], line: int, column: int):
        super().__init__(line, column)
        self.statements = statements

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": "Block { }",
            "node_type": "Block",
            "inferred_type": "void",
            "line": self.line,
            "column": self.column,
            "children": [stmt.to_dict() for stmt in self.statements]
        }


class IfNode(ASTNode):
    def __init__(self, condition: ASTNode, then_branch: ASTNode, else_branch: Optional[ASTNode], line: int, column: int):
        super().__init__(line, column)
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

    def to_dict(self) -> Dict[str, Any]:
        children = [
            {"name": "Condition", "node_type": "ConditionWrapper", "children": [self.condition.to_dict()]},
            {"name": "Then", "node_type": "ThenWrapper", "children": [self.then_branch.to_dict()]}
        ]
        if self.else_branch:
            children.append({"name": "Else", "node_type": "ElseWrapper", "children": [self.else_branch.to_dict()]})
        return {
            "name": "IfStmt",
            "node_type": "IfStmt",
            "inferred_type": "void",
            "line": self.line,
            "column": self.column,
            "children": children
        }


class WhileNode(ASTNode):
    def __init__(self, condition: ASTNode, body: ASTNode, line: int, column: int):
        super().__init__(line, column)
        self.condition = condition
        self.body = body

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": "WhileLoop",
            "node_type": "WhileLoop",
            "inferred_type": "void",
            "line": self.line,
            "column": self.column,
            "children": [
                {"name": "Condition", "node_type": "ConditionWrapper", "children": [self.condition.to_dict()]},
                {"name": "Body", "node_type": "BodyWrapper", "children": [self.body.to_dict()]}
            ]
        }


class ForNode(ASTNode):
    def __init__(self, init: Optional[ASTNode], condition: Optional[ASTNode], update: Optional[ASTNode], body: ASTNode, line: int, column: int):
        super().__init__(line, column)
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body

    def to_dict(self) -> Dict[str, Any]:
        children = []
        if self.init:
            children.append({"name": "Init", "node_type": "InitWrapper", "children": [self.init.to_dict()]})
        if self.condition:
            children.append({"name": "Condition", "node_type": "ConditionWrapper", "children": [self.condition.to_dict()]})
        if self.update:
            children.append({"name": "Update", "node_type": "UpdateWrapper", "children": [self.update.to_dict()]})
        children.append({"name": "Body", "node_type": "BodyWrapper", "children": [self.body.to_dict()]})
        return {
            "name": "ForLoop",
            "node_type": "ForLoop",
            "inferred_type": "void",
            "line": self.line,
            "column": self.column,
            "children": children
        }


class PrintNode(ASTNode):
    def __init__(self, expressions: List[ASTNode], line: int, column: int):
        super().__init__(line, column)
        self.expressions = expressions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": f"print() [{len(self.expressions)} args]",
            "node_type": "PrintStmt",
            "inferred_type": "void",
            "line": self.line,
            "column": self.column,
            "children": [expr.to_dict() for expr in self.expressions]
        }


class ReturnNode(ASTNode):
    def __init__(self, value: Optional[ASTNode], line: int, column: int):
        super().__init__(line, column)
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        children = [self.value.to_dict()] if self.value else []
        return {
            "name": "return",
            "node_type": "ReturnStmt",
            "inferred_type": self.inferred_type,
            "line": self.line,
            "column": self.column,
            "children": children
        }


class FnDeclNode(ASTNode):
    def __init__(self, name: str, params: List[Dict[str, str]], return_type: str, body: BlockNode, line: int, column: int):
        super().__init__(line, column)
        self.name = name
        self.params = params  # list of {"name": str, "type": str}
        self.return_type = return_type
        self.body = body

    def to_dict(self) -> Dict[str, Any]:
        param_str = ", ".join([f"{p['name']}: {p['type']}" for p in self.params])
        return {
            "name": f"fn {self.name}({param_str}) -> {self.return_type}",
            "node_type": "FnDecl",
            "fn_name": self.name,
            "return_type": self.return_type,
            "params": self.params,
            "inferred_type": self.return_type,
            "line": self.line,
            "column": self.column,
            "children": [self.body.to_dict()]
        }


class BinaryOpNode(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode, line: int, column: int):
        super().__init__(line, column)
        self.left = left
        self.op = op
        self.right = right

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": f"BinaryOp ({self.op})",
            "node_type": "BinaryOp",
            "operator": self.op,
            "inferred_type": self.inferred_type,
            "line": self.line,
            "column": self.column,
            "children": [self.left.to_dict(), self.right.to_dict()]
        }


class UnaryOpNode(ASTNode):
    def __init__(self, op: str, operand: ASTNode, line: int, column: int):
        super().__init__(line, column)
        self.op = op
        self.operand = operand

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": f"UnaryOp ({self.op})",
            "node_type": "UnaryOp",
            "operator": self.op,
            "inferred_type": self.inferred_type,
            "line": self.line,
            "column": self.column,
            "children": [self.operand.to_dict()]
        }


class LiteralNode(ASTNode):
    def __init__(self, value: Any, literal_type: str, line: int, column: int):
        super().__init__(line, column)
        self.value = value
        self.literal_type = literal_type
        self.inferred_type = literal_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": f"Lit: {repr(self.value)} ({self.literal_type})",
            "node_type": "Literal",
            "value": self.value,
            "literal_type": self.literal_type,
            "inferred_type": self.inferred_type,
            "line": self.line,
            "column": self.column,
            "children": []
        }


class IdentifierNode(ASTNode):
    def __init__(self, name: str, line: int, column: int):
        super().__init__(line, column)
        self.name = name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": f"Id: {self.name}",
            "node_type": "Identifier",
            "identifier": self.name,
            "inferred_type": self.inferred_type,
            "line": self.line,
            "column": self.column,
            "children": []
        }


class CallNode(ASTNode):
    def __init__(self, callee: str, args: List[ASTNode], line: int, column: int):
        super().__init__(line, column)
        self.callee = callee
        self.args = args

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": f"Call: {self.callee}()",
            "node_type": "Call",
            "callee": self.callee,
            "inferred_type": self.inferred_type,
            "line": self.line,
            "column": self.column,
            "children": [arg.to_dict() for arg in self.args]
        }
