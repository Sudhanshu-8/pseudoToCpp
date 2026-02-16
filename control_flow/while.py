"""Helpers for generating C++ code for while-loops."""


def generate_while_cpp(stmt, indent, generate_cpp):
    """Generate C++ code for a 'while' statement node.

    stmt: dict with keys 'condition' and 'body'
    indent: current indentation level (in blocks, not spaces)
    generate_cpp: function used to generate C++ for the nested body
    """
    space = " " * (indent * 4)
    cpp = space + f"while ({stmt['condition']}) {{\n"
    cpp += generate_cpp(stmt["body"], indent + 1)
    cpp += space + "}\n"
    return cpp
