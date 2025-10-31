# lexer.py
import ply.lex as lex

tokens = (
    'FN', 'WHILE', 'IF', 'BREAK', 'RETURN',
    'IDENT', 'NUMBER', 'OP', 'ASSIGN',
    'LBRACE', 'RBRACE', 'LPAREN', 'RPAREN',
    'SEMICOLON', 'COMMA',
)

t_FN = r'\\Fn'
t_WHILE = r'\\While'
t_IF = r'\\If'
t_BREAK = r'\\Break'
t_RETURN = r'\\KwRet'
t_ASSIGN = r'\\gets'
t_OP = r'[+\-*/<>=!]+'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_SEMICOLON = r';'
t_COMMA = r','

t_ignore = ' \t\r\n'

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_IDENT(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    return t

def t_error(t):
    print(f"Illegal character {t.value[0]!r}")
    t.lexer.skip(1)

lexer = lex.lex()
