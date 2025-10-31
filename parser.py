# parser.py
import ply.yacc as yacc
from lexer import tokens

# -----------------------------
# Grammar Rules for C++ Codegen
# -----------------------------

def p_program(p):
    '''program : function'''
    p[0] = (
        "#include <iostream>\n"
        "using namespace std;\n\n"
        f"{p[1]}"
    )

def p_function(p):
    '''function : FN LPAREN IDENT RPAREN LBRACE statements RBRACE'''
    p[0] = f"void {p[3]}() {{\n{p[6]}\n}}\n\nint main() {{\n    {p[3]}();\n    return 0;\n}}\n"

def p_statements_multiple(p):
    '''statements : statements statement'''
    p[0] = p[1] + p[2]

def p_statements_single(p):
    '''statements : statement'''
    p[0] = p[1]

def p_statement_assign(p):
    '''statement : IDENT ASSIGN IDENT SEMICOLON'''
    p[0] = f"    {p[1]} = {p[3]};\n"

def p_statement_assign_num(p):
    '''statement : IDENT ASSIGN NUMBER SEMICOLON'''
    p[0] = f"    {p[1]} = {p[3]};\n"

def p_statement_while(p):
    '''statement : WHILE LPAREN condition RPAREN LBRACE statements RBRACE'''
    p[0] = f"    while ({p[3]}) {{\n{p[6]}}}\n"

def p_statement_if(p):
    '''statement : IF LPAREN condition RPAREN LBRACE statements RBRACE'''
    p[0] = f"    if ({p[3]}) {{\n{p[6]}}}\n"

def p_statement_break(p):
    '''statement : BREAK SEMICOLON'''
    p[0] = "    break;\n"

def p_statement_return(p):
    '''statement : RETURN IDENT SEMICOLON'''
    p[0] = f"    return {p[2]};\n"

def p_condition(p):
    '''condition : IDENT OP IDENT'''
    p[0] = f"{p[1]} {p[2]} {p[3]}"

def p_error(p):
    if p:
        print(f"Syntax error near '{p.value}'")
    else:
        print("Syntax error at end of input")

parser = yacc.yacc()
