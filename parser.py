import ply.yacc as yacc
from lexer import tokens
import sys

symbol_table = {}
has_return = False

valid_dtypes = ["int", "float", "string", "long", "char", "array", "vector"]

# Detect datatype automatically based on assigned value
def infer_type(value):
    if isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        if value.startswith('"') and value.endswith('"'):
            return "string"
        elif value.startswith("'") and value.endswith("'"):
            return "char"
    return None

# Ask datatype from user if needed
def ask_type(var):
    dtype = input(f"Enter datatype for variable '{var}' ({', '.join(valid_dtypes)}): ").strip()
    while dtype not in valid_dtypes:
        dtype = input(f"Invalid datatype. Enter again for '{var}': ").strip()
    return dtype

# -------- Grammar Rules --------

def p_program(p):
    '''program : function'''
    p[0] = [p[1]]

def p_function(p):
    '''function : FN ID LPAREN RPAREN LBRACE stmt_list RBRACE'''
    global has_return
    ret_type = "int" if has_return else "void"
    p[0] = {"type": "function", "name": p[2], "body": p[6], "return_type": ret_type}

def p_stmt_list(p):
    '''stmt_list : stmt_list statement
                 | statement'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_statement_assign(p):
    '''statement : ID ASSIGN NUMBER SEMICOLON
                 | ID ASSIGN ID SEMICOLON'''
    var = p[1]
    val = p[3]

    # --- Infer datatype automatically ---
    if isinstance(val, (int, float)):
        inferred = infer_type(val)
        symbol_table[var] = inferred
    elif isinstance(val, str):
        # if assigning from another variable
        if val in symbol_table:
            symbol_table[var] = symbol_table[val]
        else:
            # ask user for unknown variables
            symbol_table[val] = ask_type(val)
            symbol_table[var] = symbol_table[val]

    p[0] = {"type": "assign", "var": var, "value": val}

def p_statement_if(p):
    '''statement : IF LPAREN condition RPAREN LBRACE stmt_list RBRACE'''
    p[0] = {"type": "if", "condition": p[3], "body": p[6]}

def p_statement_while(p):
    '''statement : WHILE LPAREN condition RPAREN LBRACE stmt_list RBRACE'''
    p[0] = {"type": "while", "condition": p[3], "body": p[6]}

def p_statement_return(p):
    '''statement : RETURN ID SEMICOLON
                 | RETURN NUMBER SEMICOLON'''
    global has_return
    has_return = True
    p[0] = {"type": "return", "value": p[2]}

def p_condition(p):
    '''condition : ID LT NUMBER
                 | ID LT ID
                 | NUMBER LT ID
                 | ID GT NUMBER
                 | ID GT ID
                 | NUMBER GT ID
                 | ID EQ NUMBER
                 | ID EQ ID'''
    p[0] = f"{p[1]} {p[2]} {p[3]}"

def p_error(p):
    if p:
        print(f"Syntax error near '{p.value}'")
    else:
        print("Syntax error at EOF")
    sys.exit(1)

# -------- C++ Code Generation --------

def generate_cpp(parsed, indent=0):
    cpp = ""
    space = " " * (indent * 4)
    for stmt in parsed:
        st = stmt["type"]
        if st == "function":
            cpp += f"{stmt['return_type']} {stmt['name']}() {{\n"
            cpp += generate_cpp(stmt["body"], indent + 1)
            cpp += "}\n\n"
        elif st == "assign":
            dtype = symbol_table.get(stmt["var"], "")
            decl = f"{dtype} " if dtype else ""
            cpp += space + f"{decl}{stmt['var']} = {stmt['value']};\n"
        elif st == "if":
            cpp += space + f"if ({stmt['condition']}) {{\n"
            cpp += generate_cpp(stmt["body"], indent + 1)
            cpp += space + "}\n"
        elif st == "while":
            cpp += space + f"while ({stmt['condition']}) {{\n"
            cpp += generate_cpp(stmt["body"], indent + 1)
            cpp += space + "}\n"
        elif st == "return":
            cpp += space + f"return {stmt['value']};\n"
    return cpp

def to_cpp(parsed):
    header = "#include <bits/stdc++.h>\nusing namespace std;\n\n"
    body = generate_cpp(parsed)
    main = "int main() {\n    " + parsed[0]["name"] + "();\n    return 0;\n}\n"
    return header + body + main

parser = yacc.yacc()
