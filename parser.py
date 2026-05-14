import ply.yacc as yacc
from lexer import tokens
import sys
import importlib
import re

_if_mod = importlib.import_module("control_flow.if")
_for_mod = importlib.import_module("control_flow.for")
_while_mod = importlib.import_module("control_flow.while")

symbol_table = {}
current_function = None
function_return_types = {}

# Mapping from set types to their element types
SET_ELEMENT_TYPES = {
    "set": "int",
    "set_int": "int",
    "set_float": "float",
    "set_double": "double",
    "set_char": "char",
    "set_string": "string",
}

# Extended valid datatypes including set types
valid_dtypes = [
    "int", "float", "string", "long", "char", "bool", "array", "vector",
    "set", "set_int", "set_float", "set_double", "set_char", "set_string", "double"
]


class MissingTypeError(Exception):
    """Raised when the parser needs a datatype for a variable but none is provided."""


# Optional callback that external callers can register to supply types.
type_provider = None

def parse_code(code):
    """Parse pseudo-code and return AST. Reset state before parsing."""
    global symbol_table, current_function, function_return_types
    symbol_table = {}
    current_function = None
    function_return_types = {}
    return parser.parse(code)

def register_type_provider(fn):
    """Register a callback used to resolve unknown variable types."""
    global type_provider
    type_provider = fn


# Ask datatype from a registered provider (no direct stdin usage here).
def ask_type(var, context=None):
    if type_provider is None:
        raise MissingTypeError(var)

    # If we have a function context, include it in the variable name for the UI
    display_var = f"{var} (in {context})" if context else var
    dtype = type_provider(display_var, valid_dtypes).strip()
    
    # Validation: accept basic types OR datastructure_element patterns
    is_valid = dtype in valid_dtypes
    if not is_valid and "_" in dtype:
        parts = dtype.split("_")
        if len(parts) == 2 and parts[0] in ["vector", "array", "set"] and parts[1] in valid_dtypes:
            is_valid = True
            
    if not is_valid:
        raise MissingTypeError(var)
    return dtype

def handle_assignment(var, value, is_expression=False):
    """Update symbol_table for an assignment and return normalized value string.
    
    Includes type inference for simple literals.
    """
    global symbol_table, current_function

    scope_key = (current_function, var)
    
    if scope_key not in symbol_table:
        # Try inference first
        inferred = None
        if not is_expression:
            if isinstance(value, int):
                inferred = "int"
            elif isinstance(value, float):
                inferred = "float"
            elif isinstance(value, str):
                if value.startswith('"'): inferred = "string"
                elif value.startswith("'"): inferred = "char"
                elif value.lower() in ["true", "false"]: inferred = "bool"
                elif value.isdigit(): inferred = "int"
                else:
                    try:
                        float(value)
                        inferred = "float"
                    except ValueError: pass
        
        if inferred:
            symbol_table[scope_key] = inferred
        else:
            # Fallback to provider
            symbol_table[scope_key] = ask_type(var, context=current_function)

    return str(value)


_id_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _identifiers_in_expr(expr):
    """Return a list of identifier-like names found in an expression string."""
    if not isinstance(expr, str):
        return []
    return _id_pattern.findall(expr)


# -------- Grammar Rules --------

def p_program(p):
    """program : function_list"""
    p[0] = p[1]

def p_function_list(p):
    """function_list : function_list function
                     | function"""
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_function_head(p):
    """function_head : FN ID"""
    global current_function
    current_function = p[2]
    p[0] = p[2]

def p_function(p):
    """function : function_head LPAREN param_list_opt RPAREN LBRACE stmt_list RBRACE"""
    global symbol_table, current_function, function_return_types
    func_name = p[1]
    params = p[3] or []
    body = p[6]
    
    # Determine return type
    ret_type = function_return_types.get(func_name)
    if not ret_type:
        # Check if there was any return statement (even if it didn't trigger ask_type yet)
        has_return_stmt = any(
            stmt.get("type") == "return"
            for stmt in body
            if isinstance(stmt, dict)
        )
        if has_return_stmt:
            ret_type = ask_type(f"return_type_of_{func_name}")
            function_return_types[func_name] = ret_type
        else:
            ret_type = "void"
    
    # Ensure parameter types are known and scoped
    for param in params:
        scope_key = (func_name, param)
        if scope_key not in symbol_table:
            symbol_table[scope_key] = ask_type(param, context=func_name)

    # Collect variables that belong to this function from the symbol_table
    func_vars = {var: dtype for (f, var), dtype in symbol_table.items() if f == func_name}

    p[0] = {
        "type": "function",
        "name": func_name,
        "params": params,
        "body": body,
        "return_type": ret_type,
        "variables": func_vars, 
    }
    # Clear current function context after finishing
    current_function = None


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


def p_statement_assign_indexed(p):
    """statement : ID LBRACKET expression RBRACKET ASSIGN expression SEMICOLON
                 | ID LBRACKET expression RBRACKET ASSIGN ID SEMICOLON
                 | ID LBRACKET expression RBRACKET ASSIGN NUMBER SEMICOLON"""
    var = p[1]
    index = p[3]
    value = p[6]
    
    # Ensure the array itself is in symbol table
    scope_key = (current_function, var)
    if scope_key not in symbol_table:
        symbol_table[scope_key] = ask_type(var, context=current_function)
        
    p[0] = {"type": "assign_indexed", "var": var, "index": index, "value": value}


def p_statement_declare(p):
    """statement : DECL ID SEMICOLON"""
    global symbol_table, current_function
    var = p[2]
    
    scope_key = (current_function, var)
    if scope_key not in symbol_table:
        symbol_table[scope_key] = ask_type(var, context=current_function)
    
    p[0] = {"type": "declare", "var": var}


def p_statement_if(p):
    """statement : IF LPAREN condition RPAREN LBRACE stmt_list RBRACE else_if_stmt"""
    p[0] = {
        "type": "if",
        "condition": p[3],
        "body": p[6],
        "elifs": p[8]["elifs"],
        "else_body": p[8]["else_body"]
    }


def p_else_if_stmt(p):
    """else_if_stmt : ELSE IF LPAREN condition RPAREN LBRACE stmt_list RBRACE else_if_stmt
                    | ELSE LBRACE stmt_list RBRACE
                    | empty"""
    if len(p) == 10:  # ELSE IF ...
        p[0] = {
            "elifs": [{"condition": p[4], "body": p[7]}] + p[9]["elifs"],
            "else_body": p[9]["else_body"]
        }
    elif len(p) == 5:  # ELSE { ... }
        p[0] = {
            "elifs": [],
            "else_body": p[3]
        }
    else:  # empty
        p[0] = {
            "elifs": [],
            "else_body": None
        }


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
    is_expr = not isinstance(val, (int, float)) and not (isinstance(val, str) and val.isidentifier())
    normalized = handle_assignment(var, val, is_expression=is_expr)
    p[0] = {"type": "assign", "var": var, "value": normalized}


def p_statement_return(p):
    """statement : RETURN expression SEMICOLON
                 | RETURN NUMBER SEMICOLON
                 | RETURN ID SEMICOLON"""
    global current_function, function_return_types, symbol_table
    ret_val = p[2]
    
    if current_function and current_function not in function_return_types:
        # INFERENCE: If returning an ID whose type we already know
        if isinstance(ret_val, str) and ret_val.isidentifier():
            scope_key = (current_function, ret_val)
            if scope_key in symbol_table:
                function_return_types[current_function] = symbol_table[scope_key]
        
        # If still unknown, ask the provider
        if current_function not in function_return_types:
            function_return_types[current_function] = ask_type(f"return_type_of_{current_function}")
    
    p[0] = {"type": "return", "value": ret_val}

def p_statement_function_call(p):
    """statement : ID LPAREN argument_list_opt RPAREN SEMICOLON"""
    global symbol_table, current_function
    func_name = p[1]
    args = p[3] or []
    
    for arg in args:
        if isinstance(arg, str) and arg.isidentifier():
            scope_key = (current_function, arg)
            if scope_key not in symbol_table:
                symbol_table[scope_key] = ask_type(arg, context=current_function)
    
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


def p_factor_string(p):
    """factor : STRING"""
    p[0] = f'"{p[1]}"'


def p_factor_char(p):
    """factor : CHAR"""
    p[0] = f"'{p[1]}'"


def p_factor_id(p):
    """factor : ID"""
    global symbol_table, current_function
    var = p[1]
    scope_key = (current_function, var)
    if scope_key not in symbol_table:
        symbol_table[scope_key] = ask_type(var, context=current_function)
    p[0] = var


def p_factor_indexed(p):
    """factor : ID LBRACKET expression RBRACKET"""
    global symbol_table, current_function
    var = p[1]
    index = p[3]
    scope_key = (current_function, var)
    if scope_key not in symbol_table:
        symbol_table[scope_key] = ask_type(var, context=current_function)
    p[0] = f"{var}[{index}]"


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
    """PLY error handler."""
    if p:
        raise SyntaxError(f"Syntax error near '{p.value}'")
    raise SyntaxError("Syntax error at EOF")

def p_factor_function_call(p):
    """factor : ID LPAREN argument_list_opt RPAREN"""
    global symbol_table, current_function
    func_name = p[1]
    args = p[3] or []
    
    for arg in args:
        if isinstance(arg, str) and arg.isidentifier():
            scope_key = (current_function, arg)
            if scope_key not in symbol_table:
                symbol_table[scope_key] = ask_type(arg, context=current_function)
    
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

def _get_cpp_type(dtype):
    """Convert pseudo-code type to proper C++ type string.
    
    Handles: 
    - set_int -> set<int>
    - vector_float -> vector<float>
    - array_char -> vector<char>
    """
    if not dtype: return "void"
    
    # Check for datastructure_element type pattern
    if "_" in dtype:
        parts = dtype.split("_")
        ds = parts[0]
        elem = parts[1]
        if ds == "set":
            return f"set<{elem}>"
        elif ds in ["vector", "array"]:
            return f"vector<{elem}>"
            
    # Legacy/Default mappings
    if dtype == "set": return "set<int>"
    if dtype in ["vector", "array"]: return "vector<int>"
    
    return dtype


def _format_for_assignment(assign_node, include_type=True, var_dtype=None, scope_types=None):
    """Format an assignment node as a C++ snippet."""
    var = assign_node["var"]
    value = assign_node["value"]
    
    elem_type = SET_ELEMENT_TYPES.get(var_dtype)
    is_set_type = elem_type is not None
    
    if is_set_type:
        value_str = str(value)
        is_elem = False
        
        # 1. Check if literal
        try:
            float(value_str)
            is_elem = True
        except (ValueError, TypeError):
            pass
        
        if not is_elem:
            if value_str.startswith("'") or value_str.startswith('"'):
                is_elem = True
        
        # 2. Check if it's an identifier of the element type
        if not is_elem and scope_types and value_str in scope_types:
            if scope_types[value_str] == elem_type:
                is_elem = True
        
        if is_elem:
            return f"{var}.insert({value})"
        else:
            return f"{var} = {value}"
    
    return f"{var} = {value}"


def generate_cpp(parsed, indent=0, declared=None):
    """Generate C++ code from parsed AST with proper declaration handling."""
    cpp = ""
    space = " " * (indent * 4)

    for stmt in parsed:
        stype = stmt["type"]

        if stype == "function":
            params = stmt.get("params", [])
            func_name = stmt["name"]
            func_vars = stmt.get("variables", {}) # This is now a dict {var: dtype}

            # Build parameter signature
            param_parts = []
            for param in params:
                dtype = func_vars.get(param, "int")
                param_parts.append(f"{_get_cpp_type(dtype)} {param}")
            param_sig = ", ".join(param_parts)

            ret_cpp_type = _get_cpp_type(stmt['return_type'])
            cpp += f"{ret_cpp_type} {func_name}({param_sig}) {{\n"

            # Emit all variable declarations (excluding parameters)
            vars_to_declare = [(v, d) for v, d in func_vars.items() if v not in params]
            if vars_to_declare:
                for var, dtype in vars_to_declare:
                    cpp += " " * ((indent + 1) * 4) + f"{_get_cpp_type(dtype)} {var};\n"
                cpp += "\n"
            
            cpp += generate_cpp(stmt["body"], indent + 1, declared=func_vars)
            cpp += "}\n\n"

        elif stype == "assign":
            var = stmt.get("var")
            var_dtype = declared.get(var) if declared else None
            cpp += space + _format_for_assignment(stmt, include_type=False, var_dtype=var_dtype, scope_types=declared) + ";\n"

        elif stype == "assign_indexed":
            cpp += space + f"{stmt['var']}[{stmt['index']}] = {stmt['value']};\n"

        elif stype == "declare":
            pass

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
            def format_assign_with_type(assign_node, include_type=True):
                var = assign_node.get("var")
                var_dtype = declared.get(var) if declared else None
                return _format_for_assignment(assign_node, include_type, var_dtype, scope_types=declared)
            cpp += _for_mod.generate_for_cpp(stmt, indent, format_assign_with_type, _gen_for)

        elif stype == "function_call":
            cpp += space + f"{stmt['name']}({stmt['args']});\n"
            
        elif stype == "return":
            cpp += space + f"return {stmt['value']};\n"

    return cpp

def to_cpp(parsed):
    """Generate complete C++ program from parsed AST."""
    header = "#include <bits/stdc++.h>\nusing namespace std;\n\n"
    body = generate_cpp(parsed)
    has_main = any(func.get("name") == "main" for func in parsed if func.get("type") == "function")

    if not has_main:
        first_func = parsed[0]
        first_func_name = first_func.get("name", "")
        params = first_func.get("params", [])
        
        if not params:
            main = (
                "int main() {\n"
                f"    {first_func_name}();\n"
                "    return 0;\n"
                "}\n"
            )
            return header + body + main
        else:
            return header + body
    else:
        return header + body
    
parser = yacc.yacc()