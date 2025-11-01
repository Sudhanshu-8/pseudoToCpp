import ply.lex as lex

# List of token names
tokens = (
    'FN', 'WHILE', 'FOR', 'IF', 'ELSE', 'RETURN', 'BREAK', 'CONTINUE',
    'PRINT', 'SCAN',
    'ID', 'NUMBER', 'STRING', 'CHAR', 'BOOL',
    'ASSIGN', 'LT', 'GT', 'LE', 'GE', 'EQ', 'NE',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
    'AND', 'OR', 'NOT',
    'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE',
    'SEMICOLON', 'COMMA'
)

# Regular expressions for tokens
t_FN        = r'\\Fn'
t_WHILE     = r'\\While'
t_FOR       = r'\\For'
t_IF        = r'\\If'
t_ELSE      = r'\\Else'
t_RETURN    = r'\\KwRet'
t_BREAK     = r'\\Break'
t_CONTINUE  = r'\\Cont'
t_PRINT     = r'\\Print'
t_SCAN      = r'\\Scan'

t_ASSIGN    = r'\\gets'
t_LT        = r'<'
t_GT        = r'>'
t_LE        = r'<='
t_GE        = r'>='
t_EQ        = r'=='
t_NE        = r'!='

t_PLUS      = r'\+'
t_MINUS     = r'-'
t_TIMES     = r'\*'
t_DIVIDE    = r'/'
t_MOD       = r'%'

t_AND       = r'&&'
t_OR        = r'\|\|'
t_NOT       = r'!'

t_LPAREN    = r'\('
t_RPAREN    = r'\)'
t_LBRACE    = r'\{'
t_RBRACE    = r'\}'
t_SEMICOLON = r';'
t_COMMA     = r','

# Ignored characters (spaces and tabs)
t_ignore = ' \t'


# Reserved literals (boolean values)
reserved_literals = {
    'true': 'BOOL',
    'false': 'BOOL',
}


# String literals
def t_STRING(t):
    r'"([^\\"]|\\.)*"'
    t.value = t.value[1:-1]  # Remove quotes
    return t


# Character literals
def t_CHAR(t):
    r'\'([^\\\']|\\.)\''
    t.value = t.value[1:-1]
    return t


# Numbers
def t_NUMBER(t):
    r'\d+(\.\d+)?'
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t


# Identifiers and reserved literals
def t_ID(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    t.type = reserved_literals.get(t.value, 'ID')
    return t


# Single-line comments
def t_COMMENT_SINGLE(t):
    r'//.*'
    pass  # Ignore comment text


# Multi-line comments
def t_COMMENT_MULTI(t):
    r'/\*[\s\S]*?\*/'
    pass  # Ignore comment text


# Track line numbers
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# Error handling
def t_error(t):
    print(f"❌ Illegal character '{t.value[0]}' at line {t.lexer.lineno}")
    t.lexer.skip(1)


# Build lexer
lexer = lex.lex()


# ---- OPTIONAL: Debug helper ----
if __name__ == "__main__":
    data = r'''
    \Fn add(x, y) {
        \Print("Sum is:");
        \KwRet x + y;
    }

    \Fn main() {
        a \gets 10;
        b \gets 20;
        c \gets add(a, b);
        \Print(c);
    }
    '''

    lexer.input(data)
    for tok in lexer:
        print(tok)
