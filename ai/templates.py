"""
Offline fallback templates and heuristic engine for the AI Assistant.
Provides high quality, pedagogical explanations and code generation when
no Anthropic API key is configured or when running offline.
"""

from typing import Dict, Any, Optional, List


def offline_explain_error(code: str, error: Dict[str, Any]) -> Dict[str, Any]:
    stage = error.get("stage", "compiler")
    msg = error.get("message", "An error occurred during compilation.")
    line = error.get("line", 0)
    col = error.get("column", 0)

    # Extract target code line
    code_lines = code.split("\n")
    target_line = code_lines[line - 1] if 1 <= line <= len(code_lines) else ""

    explanation = ""
    suggested_fix = ""

    if stage == "lexer":
        explanation = (
            f"The Lexer (Scanner) encountered an unrecognized character at Line {line}, Column {col}. "
            f"MiniLang only allows standard ASCII alphanumeric characters, operators (+, -, *, /, %, ==, !=, <, <=, >, >=, &&, ||, !), "
            f"and delimiters (;, :, ,, ->, (, ), {{, }})."
        )
        suggested_fix = f"Remove or replace the unrecognized character on line {line}."

    elif stage == "parser":
        if "Expected ';'" in msg:
            explanation = (
                f"Syntax Error on Line {line}: MiniLang requires every variable declaration, assignment, "
                f"print statement, and return statement to end with a semicolon ';'."
            )
            suggested_fix = f"Add a semicolon ';' to terminate the statement at or before line {line}."
        elif "Expected '}'" in msg:
            explanation = (
                f"Syntax Error on Line {line}: A block was opened with '{{' but was never properly closed with '}}'."
            )
            suggested_fix = f"Ensure all curly brackets '{{' have matching closing brackets '}}'."
        elif "Expected '('" in msg or "Expected ')'" in msg:
            explanation = (
                f"Syntax Error on Line {line}: Control flow statements (if, while, for) and function declarations require parentheses around their conditions or parameter lists."
            )
            suggested_fix = f"Check for missing opening '(' or closing ')' parentheses around the condition on line {line}."
        else:
            explanation = f"Syntax Error on Line {line}, Column {col}: {msg}."
            suggested_fix = f"Check line {line} for grammatical structure matching the MiniLang EBNF specification."

    elif stage == "semantic":
        if "undeclared variable" in msg.lower() or "undefined variable" in msg.lower():
            explanation = (
                f"Semantic Error on Line {line}: You are trying to use a variable before declaring it in the current scope. "
                f"In MiniLang, all variables must be declared using the 'let' keyword (e.g., 'let x: int = 10;' or 'let x = 10;')."
            )
            suggested_fix = f"Declare the variable with 'let <name> = <value>;' before line {line}."
        elif "redeclaration" in msg.lower():
            explanation = (
                f"Semantic Error on Line {line}: A variable with the same name was already declared in this exact scope. "
                f"You cannot declare two variables with the same name in the same scope."
            )
            suggested_fix = f"Rename the variable or assign to the existing one without using 'let'."
        elif "type mismatch" in msg.lower() or "cannot assign" in msg.lower():
            explanation = (
                f"Type Error on Line {line}: {msg}. "
                f"MiniLang is statically typed. An integer cannot be assigned to a string or boolean without explicit handling."
            )
            suggested_fix = f"Ensure the expression type matches the declared variable type on line {line}."
        elif "missing a return statement" in msg.lower():
            explanation = (
                f"Control Flow Error on Line {line}: The function has a declared return type, but some execution paths exit without returning a value."
            )
            suggested_fix = f"Add a 'return <expression>;' statement ensuring all branches (then/else) return a valid value."
        else:
            explanation = f"Semantic Analysis Error on Line {line}: {msg}."
            suggested_fix = f"Verify variable declarations, types, and function contracts around line {line}."

    elif stage == "vm":
        if "division by zero" in msg.lower():
            explanation = f"Runtime Error: The program attempted to divide a number by zero during execution."
            suggested_fix = "Check the divisor expression to ensure it cannot evaluate to zero before dividing."
        elif "infinite loop" in msg.lower():
            explanation = f"Runtime Execution Limit Reached: The virtual machine exceeded its instruction limit."
            suggested_fix = "Ensure loops have proper terminating conditions and increment/decrement their loop counter variable."
        else:
            explanation = f"Virtual Machine Runtime Error: {msg}."
            suggested_fix = "Inspect variable values and stack frames to locate the unexpected runtime state."

    return {
        "explanation": explanation,
        "suggested_fix": suggested_fix,
        "line_number": line,
        "code_snippet": target_line,
        "mode": "offline-heuristic",
    }


def offline_explain_stage(stage: str, stage_data: Dict[str, Any]) -> Dict[str, Any]:
    descriptions = {
        "lexer": {
            "title": "Lexical Analysis (Scanning)",
            "summary": "Transforms raw source code text into a stream of discrete lexical tokens.",
            "what_happened": "The lexer stripped away comments and whitespace, validated identifiers and literals, and generated Token objects with exact line and column coordinates.",
            "compiler_concepts": "Regular expressions, Deterministic Finite Automata (DFA), token classification, and error recovery for unrecognized glyphs."
        },
        "parser": {
            "title": "Syntax Analysis (Parsing)",
            "summary": "Verifies grammatical structure and builds an Abstract Syntax Tree (AST).",
            "what_happened": "A recursive descent parser parsed the token stream according to MiniLang's EBNF grammar, establishing operator precedence and nesting.",
            "compiler_concepts": "Context-Free Grammars (CFG), LL(1) / Pratt precedence climbing, Abstract Syntax Trees, and panic-mode error recovery."
        },
        "semantic": {
            "title": "Semantic Analysis & Type Checking",
            "summary": "Validates program semantics, scope rules, and type compatibility.",
            "what_happened": "Constructed a scoped symbol table (handling global, function, and block levels), performed static type checking, verified function contracts, and ensured return path guarantees.",
            "compiler_concepts": "Static typing, scoped symbol tables (lexical scoping), type inference, name resolution, and definite return analysis."
        },
        "ir": {
            "title": "Intermediate Representation (TAC)",
            "summary": "Linearizes the hierarchical AST into Three-Address Code (TAC).",
            "what_happened": "Decomposed complex nested expressions into atomic instructions using temporary variables (t0, t1, ...) and explicit control-flow labels (L0, L1, ...).",
            "compiler_concepts": "Machine-independent IR, quadruples/triples, temporary variable generation, and linearization of control flow."
        },
        "optimizer": {
            "title": "IR Optimization",
            "summary": "Improves code performance and size without altering program behavior.",
            "what_happened": "Applied iterative passes of Constant Folding (evaluating constant math at compile-time), Constant Propagation (substituting known values), and Dead Code Elimination.",
            "compiler_concepts": "Data-flow analysis, local constant propagation, algebraic simplifications, dead code elimination, and fixed-point iteration."
        },
        "codegen": {
            "title": "Bytecode Code Generation",
            "summary": "Converts optimized TAC instructions into target stack-based bytecode.",
            "what_happened": "Mapped three-address instructions into stack operations (PUSH_CONST, LOAD_VAR, STORE_VAR, BINARY_*) and resolved symbolic labels into absolute instruction pointers (IP).",
            "compiler_concepts": "Target architecture instruction selection, two-pass label resolution, and stack machine design."
        },
        "vm": {
            "title": "Virtual Machine Execution",
            "summary": "Simulates execution of bytecode on an abstract stack computer.",
            "what_happened": "Managed the instruction pointer, evaluation operand stack, call frames (for local variables and function returns), and console output.",
            "compiler_concepts": "Virtual machines, call frame activation records, stack evaluation, and execution step debugging."
        }
    }

    info = descriptions.get(stage, {
        "title": f"Compiler Stage: {stage}",
        "summary": "Processed the program through this compilation phase.",
        "what_happened": "Analyzed input data and generated the corresponding structured output representation.",
        "compiler_concepts": "Formal language processing and phase transitions."
    })
    info["mode"] = "offline-heuristic"
    return info


def offline_generate_code(prompt: str) -> str:
    p = prompt.lower()

    if "factorial" in p:
        return (
            "// Generated: Factorial Calculation\n"
            "fn factorial(n: int) -> int {\n"
            "    if (n <= 1) {\n"
            "        return 1;\n"
            "    }\n"
            "    return n * factorial(n - 1);\n"
            "}\n\n"
            "let x = 6;\n"
            "let ans = factorial(x);\n"
            "print(\"Factorial of 6 is:\", ans);\n"
        )
    elif "fibonacci" in p:
        return (
            "// Generated: Fibonacci Sequence\n"
            "fn fib(n: int) -> int {\n"
            "    if (n <= 0) { return 0; }\n"
            "    if (n == 1) { return 1; }\n"
            "    return fib(n - 1) + fib(n - 2);\n"
            "}\n\n"
            "let terms = 8;\n"
            "for (let i = 0; i < terms; i = i + 1) {\n"
            "    print(\"fib(\", i, \") =\", fib(i));\n"
            "}\n"
        )
    elif "prime" in p:
        return (
            "// Generated: Prime Number Check\n"
            "fn is_prime(n: int) -> bool {\n"
            "    if (n <= 1) { return false; }\n"
            "    let i = 2;\n"
            "    while (i * i <= n) {\n"
            "        if (n % i == 0) {\n"
            "            return false;\n"
            "        }\n"
            "        i = i + 1;\n"
            "    }\n"
            "    return true;\n"
            "}\n\n"
            "let test_num = 17;\n"
            "if (is_prime(test_num)) {\n"
            "    print(test_num, \"is a prime number!\");\n"
            "} else {\n"
            "    print(test_num, \"is NOT prime.\");\n"
            "}\n"
        )
    elif "sum" in p or "add" in p:
        return (
            "// Generated: Sum of numbers from 1 to N\n"
            "let n = 10;\n"
            "let sum = 0;\n"
            "for (let i = 1; i <= n; i = i + 1) {\n"
            "    sum = sum + i;\n"
            "}\n"
            "print(\"Sum of numbers 1 to\", n, \"is:\", sum);\n"
        )
    else:
        return (
            "// Generated MiniLang Program\n"
            "let message: string = \"MiniLang generated output\";\n"
            "print(message);\n\n"
            "let a = 10;\n"
            "let b = 20;\n"
            "let result = (a + b) * 2;\n"
            "print(\"Computed result:\", result);\n"
        )


def offline_optimization_hints(code: str) -> List[Dict[str, str]]:
    hints = [
        {
            "category": "Constant Folding",
            "hint": "Constant expressions (like `3 * 24 * 60`) are automatically folded at compile-time by MiniLang's optimizer without runtime overhead."
        },
        {
            "category": "Loop Invariant Code Motion",
            "hint": "If you compute expressions inside a `while` or `for` loop that do not depend on the loop index, move them before the loop to avoid redundant recalculation."
        },
        {
            "category": "Dead Code Elimination",
            "hint": "MiniLang's optimizer strips out unused temporary variables and unreached branches automatically."
        }
    ]
    return hints
