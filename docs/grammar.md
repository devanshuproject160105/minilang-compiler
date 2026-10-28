# MiniLang Formal Grammar Specification (EBNF)

This document specifies the formal Extended Backus-Naur Form (EBNF) grammar and lexical conventions for **MiniLang**, an educational imperative programming language designed for compiler construction courses.

---

## 1. Lexical Grammar

### 1.1 Character Classes & Whitespace
```ebnf
letter          = "A" .. "Z" | "a" .. "z" | "_" ;
digit           = "0" .. "9" ;
non_zero_digit  = "1" .. "9" ;
whitespace      = " " | "\t" | "\r" | "\n" ;
comment         = "//" , { all_characters - "\n" } , "\n" ;
```

### 1.2 Identifiers and Keywords
```ebnf
identifier      = letter , { letter | digit } ;

keywords        = "let" | "fn" | "return" | "if" | "else" 
                | "while" | "for" | "print" 
                | "int" | "float" | "bool" | "string" | "void"
                | "true" | "false" ;
```

### 1.3 Literals
```ebnf
int_literal     = "0" | non_zero_digit , { digit } ;
float_literal   = digit+ , "." , digit+ ;
string_literal  = '"' , { string_char } , '"' ;
string_char     = ( all_characters - ( '"' | "\\" | "\n" ) ) 
                | escape_sequence ;
escape_sequence = '\\' , ( '"' | "\\" | "n" | "t" | "r" ) ;
bool_literal    = "true" | "false" ;

literal         = int_literal | float_literal | string_literal | bool_literal ;
```

### 1.4 Operators and Delimiters
```ebnf
arithmetic_op   = "+" | "-" | "*" | "/" | "%" ;
comparison_op   = "==" | "!=" | "<" | "<=" | ">" | ">=" ;
logical_op      = "&&" | "||" | "!" ;
assignment_op   = "=" ;
delimiters      = "(" | ")" | "{" | "}" | ";" | ":" | "," | "->" ;
```

---

## 2. Syntactic Grammar (EBNF)

### 2.1 Program Structure
```ebnf
Program         = { TopLevelItem } , EOF ;
TopLevelItem    = FunctionDecl | Statement ;
```

### 2.2 Declarations
```ebnf
FunctionDecl    = "fn" , identifier , "(" , [ ParameterList ] , ")" , [ "->" , Type ] , Block ;
ParameterList   = Parameter , { "," , Parameter } ;
Parameter       = identifier , ":" , Type ;

Type            = "int" | "float" | "bool" | "string" | "void" ;

VarDecl         = "let" , identifier , [ ":" , Type ] , [ "=" , Expression ] , ";" ;
```

### 2.3 Statements
```ebnf
Statement       = VarDecl
                | AssignmentStmt
                | IfStmt
                | WhileStmt
                | ForStmt
                | PrintStmt
                | ReturnStmt
                | ExprStmt
                | Block ;

AssignmentStmt  = identifier , "=" , Expression , ";" ;
IfStmt          = "if" , "(" , Expression , ")" , Block , [ "else" , ( IfStmt | Block ) ] ;
WhileStmt       = "while" , "(" , Expression , ")" , Block ;
ForStmt         = "for" , "(" , ( VarDecl | AssignmentStmt | ";" ) , 
                                [ Expression ] , ";" , 
                                [ AssignmentWithoutSemi ] , ")" , Block ;
AssignmentWithoutSemi = identifier , "=" , Expression ;
PrintStmt       = "print" , "(" , [ ArgumentList ] , ")" , ";" ;
ReturnStmt      = "return" , [ Expression ] , ";" ;
ExprStmt        = Expression , ";" ;
Block           = "{" , { Statement } , "}" ;
ArgumentList    = Expression , { "," , Expression } ;
```

### 2.4 Expressions & Operator Precedence

Precedence levels (lowest to highest):
1. Logical OR (`||`) - Left-associative
2. Logical AND (`&&`) - Left-associative
3. Equality (`==`, `!=`) - Non-associative / Left-associative
4. Relational (`<`, `<=`, `>`, `>=`) - Non-associative / Left-associative
5. Additive (`+`, `-`) - Left-associative
6. Multiplicative (`*`, `/`, `%`) - Left-associative
7. Unary (`!`, `-`) - Right-associative
8. Primary / Call (`()`, literals, identifiers)

```ebnf
Expression      = LogicalOr ;

LogicalOr       = LogicalAnd , { "||" , LogicalAnd } ;
LogicalAnd      = Equality , { "&&" , Equality } ;
Equality        = Relational , [ ( "==" | "!=" ) , Relational ] ;
Relational      = Additive , [ ( "<" | "<=" | ">" | ">=" ) , Additive ] ;
Additive        = Multiplicative , { ( "+" | "-" ) , Multiplicative } ;
Multiplicative  = Unary , { ( "*" | "/" | "%" ) , Unary } ;
Unary           = ( "!" | "-" ) , Unary | Primary ;

Primary         = literal
                | FunctionCall
                | identifier
                | "(" , Expression , ")" ;

FunctionCall    = identifier , "(" , [ ArgumentList ] , ")" ;
```

---

## 3. Semantic Rules

1. **Scoping**:
   - Variables are statically (lexically) scoped.
   - Declarations within a nested block shadow identical names in outer scopes.
   - Duplicate declarations in the *exact same scope* produce a semantic error.
2. **Type Checking**:
   - Variables declared with an explicit type must be initialized with an expression of compatible type.
   - Variables declared without a type annotation infer their type from the initializing expression.
   - Implicit widening: `int` is widened to `float` in mixed arithmetic expressions (`int + float -> float`).
   - String concatenation: `string + string -> string`.
   - Modulo operator `%` requires integer operands (`int % int -> int`).
   - Conditions in `if` and `while` must evaluate to `bool`.
3. **Function Semantics**:
   - Functions must be declared before or at file scope.
   - Function signatures dictate parameter count and strict argument types.
   - Non-void functions must return a value on all code execution paths.
