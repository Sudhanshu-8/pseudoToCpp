import ply.yacc as yacc
from lexer import tokens
import sys
import importlib
import re

_if_mod = importlib.import_module("control_flow.if")
_for_mod = importlib.import_module("control_flow.for")
_while_mod = importlib.import_module("control_flow.while")

symbol_table = {}
has_return = False

valid_dtypes = ["int", "float", "string", "long", "char", "array", "vector"]


class MissingTypeError(Exception):
    """Raised when the parser needs a datatype for a variable but none is provided.

    The intention is that higher layers (CLI, HTTP server, UI) catch this and
    ask the user for the datatype in an appropriate way (terminal prompt,
    frontend dialog, etc.).
    """


# Optional callback that external callers can register to supply types.
type_provider = None

def parse_code(code):
    """Parse pseudo-code and return AST. Reset state before parsing."""
    global symbol_table, has_return
    symbol_table = {}
    has_return = False
    return parser.parse(code)

def register_type_provider(fn):
    """Register a callback used to resolve unknown variable types.

    The callback should have the signature ``fn(var_name: str, valid: list[str])``
    and return a string from ``valid``. If it cannot provide a type it should
    raise ``MissingTypeError``.
    """

    global type_provider
    type_provider = fn


# Detect datatype automatically based on assigned value
def infer_type(value):
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        if value.startswith('"') and value.endswith('"'):
            return "string"
        if value.startswith("'") and value.endswith("'"):
            return "char"
    return None


# Ask datatype from a registered provider (no direct stdin usage here).
def ask_type(var):
    if type_provider is None:
        # No provider registered – force the caller to handle this case.
        raise MissingTypeError(var)

    dtype = type_provider(var, valid_dtypes).strip()
    if dtype not in valid_dtypes:
        raise MissingTypeError(var)
    return dtype

def handle_assignment(var, value, is_expression=False):
    """Update symbol_table for an assignment and return normalized value string.

    For complex expressions we mostly fall back to asking the user for the type
    when the variable has not been seen before.

    This also ensures both the assigned variable and any source identifier
    (e.g. in "b = a") have datatypes recorded.
    """
    global symbol_table

    # Simple constants keep type inference
    if isinstance(value, (int, float)):
        inferred = infer_type(value)
        if inferred:
            symbol_table[var] = inferred
    elif isinstance(value, str):
        # If RHS is a single identifier (not an expression like "x + y")
        if not is_expression and value.isidentifier():
            # Ensure the source identifier has a type.
            if value not in symbol_table:
                symbol_table[value] = ask_type(value)

            # Propagate type from source to target variable.
            symbol_table[var] = symbol_table[value]
        else:
            # For unknown or expression-based assignments, ask for var's type
            if var not in symbol_table:
                symbol_table[var] = ask_type(var)

    return str(value)


_id_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _identifiers_in_expr(expr):
    """Return a list of identifier-like names found in an expression string."""
    if not isinstance(expr, str):
        return []
    return _id_pattern.findall(expr)


# -------- Grammar Rules --------

def p_program(p):
    """program : function"""
    # DON'T reset here - symbol_table is already populated by child rules
    p[0] = [p[1]]

def p_function(p):
    """function : FN ID LPAREN param_list_opt RPAREN LBRACE stmt_list RBRACE"""
    global has_return, symbol_table
    
    # Get return type from symbol table or default to void
    if has_return and "__return_type__" in symbol_table:
        ret_type = symbol_table.pop("__return_type__")  # Remove special key
    else:
        ret_type = "void"
    
    params = p[4] or []

    # Ensure parameter types are known at parse time
    for param in params:
        if param not in symbol_table:
            symbol_table[param] = ask_type(param)

    p[0] = {
        "type": "function",
        "name": p[2],
        "params": params,
        "body": p[7],
        "return_type": ret_type,
    }
def p_param_list_opt(p):
    """param_list_opt : param_list
                      | empty"""
    if p[1] is None:
        p[0] = []
    else:
        p[0] = p[1]


def p_param_list(p):
    """param_list : ID
                  | param_list COMMA ID"""
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_stmt_list(p):
    """stmt_list : stmt_list statement
                 | statement
                 | empty"""
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    elif p[1] is None:
        p[0] = []
    else:
        p[0] = [p[1]]


def p_statement_assign_simple(p):
    """statement : ID ASSIGN NUMBER SEMICOLON
                 | ID ASSIGN ID SEMICOLON"""
    var = p[1]
    val = p[3]
    normalized = handle_assignment(var, val, is_expression=False)
    p[0] = {"type": "assign", "var": var, "value": normalized}


def p_statement_assign_expr(p):
    """statement : ID ASSIGN expression SEMICOLON"""
    var = p[1]
    val = p[3]
    normalized = handle_assignment(var, val, is_expression=True)
    p[0] = {"type": "assign", "var": var, "value": normalized}


def p_statement_if(p):
    """statement : IF LPAREN condition RPAREN LBRACE stmt_list RBRACE"""
    p[0] = {"type": "if", "condition": p[3], "body": p[6]}


def p_statement_while(p):
    """statement : WHILE LPAREN condition RPAREN LBRACE stmt_list RBRACE"""
    p[0] = {"type": "while", "condition": p[3], "body": p[6]}


def p_statement_for(p):
    """statement : FOR LPAREN for_init_opt SEMICOLON condition_opt SEMICOLON for_update_opt RPAREN LBRACE stmt_list RBRACE"""
    p[0] = {
        "type": "for",
        "init": p[3],
        "condition": p[5],
        "update": p[7],
        "body": p[10],
    }


def p_for_init_opt(p):
    """for_init_opt : ID ASSIGN NUMBER
                     | ID ASSIGN ID
                     | ID ASSIGN expression
                     | empty"""
    if len(p) == 1 or p[1] is None:
        p[0] = None
        return

    var = p[1]
    val = p[3]
    is_expr = not isinstance(val, (int, float)) and not (isinstance(val, str) and val.isidentifier())
    normalized = handle_assignment(var, val, is_expression=is_expr)
    p[0] = {"type": "assign", "var": var, "value": normalized}


def p_condition_opt(p):
    """condition_opt : condition
                      | empty"""
    p[0] = p[1]


def p_for_update_opt(p):
    """for_update_opt : ID ASSIGN NUMBER
                       | ID ASSIGN ID
                       | ID ASSIGN expression
                       | empty"""
    if len(p) == 1 or p[1] is None:
        p[0] = None
        return

    var = p[1]
    val = p[3]
    # Update should never redeclare the type, but should still track it
    is_expr = not isinstance(val, (int, float)) and not (isinstance(val, str) and val.isidentifier())
    normalized = handle_assignment(var, val, is_expression=is_expr)
    p[0] = {"type": "assign", "var": var, "value": normalized}


def p_statement_return(p):
    """statement : RETURN expression SEMICOLON
                 | RETURN NUMBER SEMICOLON
                 | RETURN ID SEMICOLON"""
    global has_return
    has_return = True
    
    ret_val = p[2]
    
    # Always ask for return type - no inference
    if "__return_type__" not in symbol_table:
        symbol_table["__return_type__"] = ask_type("function_return_type")
    
    p[0] = {"type": "return", "value": ret_val}

def p_statement_function_call(p):
    """statement : ID LPAREN argument_list_opt RPAREN SEMICOLON"""
    func_name = p[1]
    args = p[3] or []
    
    # Ensure all argument identifiers have types
    for arg in args:
        if isinstance(arg, str) and arg.isidentifier() and arg not in symbol_table:
            symbol_table[arg] = ask_type(arg)
    
    args_str = ", ".join(str(arg) for arg in args)
    p[0] = {"type": "function_call", "name": func_name, "args": args_str}


def p_expression_binop_addsub(p):
    """expression : expression PLUS term
                  | expression MINUS term"""
    p[0] = f"{p[1]} {p[2]} {p[3]}"


def p_expression_term(p):
    """expression : term"""
    p[0] = p[1]


def p_term_binop(p):
    """term : term TIMES factor
             | term DIVIDE factor
             | term MOD factor"""
    p[0] = f"{p[1]} {p[2]} {p[3]}"


def p_term_factor(p):
    """term : factor"""
    p[0] = p[1]


def p_factor_number(p):
    """factor : NUMBER"""
    p[0] = str(p[1])


def p_factor_id(p):
    """factor : ID"""
    var = p[1]
    # Ensure any identifier used in an expression has a datatype.
    if var not in symbol_table:
        symbol_table[var] = ask_type(var)
    p[0] = var


def p_factor_group(p):
    """factor : LPAREN expression RPAREN"""
    p[0] = f"({p[2]})"


def p_condition(p):
    """condition : expression LT expression
                 | expression GT expression
                 | expression LE expression
                 | expression GE expression
                 | expression EQ expression
                 | expression NE expression"""
    p[0] = f"{p[1]} {p[2]} {p[3]}"


def p_empty(p):
    """empty :"""
    p[0] = None


def p_error(p):
    """PLY error handler.

    We raise an exception instead of exiting so that callers (CLI or server)
    can decide how to surface the error.
    """
    if p:
        raise SyntaxError(f"Syntax error near '{p.value}'")
    raise SyntaxError("Syntax error at EOF")

def p_factor_function_call(p):
    """factor : ID LPAREN argument_list_opt RPAREN"""
    func_name = p[1]
    args = p[3] or []
    
    # Ensure all argument identifiers have types
    for arg in args:
        if isinstance(arg, str) and arg.isidentifier() and arg not in symbol_table:
            symbol_table[arg] = ask_type(arg)
    
    # Format as C++ function call
    args_str = ", ".join(str(arg) for arg in args)
    p[0] = f"{func_name}({args_str})"


def p_argument_list_opt(p):
    """argument_list_opt : argument_list
                         | empty"""
    p[0] = p[1] if p[1] is not None else []


def p_argument_list(p):
    """argument_list : argument
                     | argument_list COMMA argument"""
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_argument(p):
    """argument : expression"""
    p[0] = p[1]

# -------- C++ Code Generation --------

def _format_for_assignment(assign_node, include_type=True):
    """Format an assignment node as a C++ snippet without redeclaration.

    We now emit declarations separately, so this always returns "var = value".
    """
    var = assign_node["var"]
    value = assign_node["value"]
    return f"{var} = {value}"


def generate_cpp(parsed, indent=0, declared=None):
    """Generate C++ code from parsed AST with proper declaration handling."""
    cpp = ""
    if declared is None:
        declared = set()
    space = " " * (indent * 4)

    for stmt in parsed:
        stype = stmt["type"]

        if stype == "function":
            params = stmt.get("params", [])

            # Build parameter signature with types
            param_parts = []
            for param in params:
                dtype = symbol_table.get(param, "")
                if not dtype:
                    dtype = ask_type(param)
                    symbol_table[param] = dtype
                param_parts.append(f"{dtype} {param}")
            param_sig = ", ".join(param_parts)

            cpp += f"{stmt['return_type']} {stmt['name']}({param_sig}) {{\n"

            # Parameters are pre-declared, mark them as such
            func_declared = set(params)
            
            # Collect ALL variables that need declaration (excluding parameters)
            vars_to_declare = []
            for var, dtype in symbol_table.items():
                if var not in func_declared and dtype:
                    vars_to_declare.append((var, dtype))
                    func_declared.add(var)
            
            # Emit all variable declarations at the top of function
            if vars_to_declare:
                for var, dtype in vars_to_declare:
                    cpp += " " * ((indent + 1) * 4) + f"{dtype} {var};\n"
                # Add blank line after declarations for readability
                cpp += "\n"
            
            # Generate function body (no more declarations will happen)
            cpp += generate_cpp(stmt["body"], indent + 1, declared=func_declared)
            cpp += "}\n\n"

        elif stype == "assign":
            # Simple assignment - no declaration needed
            cpp += space + _format_for_assignment(stmt, include_type=False) + ";\n"

        elif stype == "if":
            def _gen_if(body, ind):
                return generate_cpp(body, ind, declared=declared)
            cpp += _if_mod.generate_if_cpp(stmt, indent, _gen_if)

        elif stype == "while":
            def _gen_while(body, ind):
                return generate_cpp(body, ind, declared=declared)
            cpp += _while_mod.generate_while_cpp(stmt, indent, _gen_while)

        elif stype == "for":
            def _gen_for(body, ind):
                return generate_cpp(body, ind, declared=declared)
            cpp += _for_mod.generate_for_cpp(
                stmt,
                indent,
                _format_for_assignment,
                _gen_for,
            )
        elif stype == "function_call":
            cpp += space + f"{stmt['name']}({stmt['args']});\n"
            
        elif stype == "return":
            cpp += space + f"return {stmt['value']};\n"

    return cpp

def to_cpp(parsed):
    """Generate complete C++ program from parsed AST."""
    header = "#include <bits/stdc++.h>\nusing namespace std;\n\n"
    body = generate_cpp(parsed)
    main = (
        "int main() {\n"
        f"    {parsed[0]['name']}();\n"
        "    return 0;\n"
        "}\n"
    )
    return header + body + main


parser = yacc.yacc()
