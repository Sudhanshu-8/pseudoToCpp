"""Helpers for generating C++ code for if-statements."""


def generate_if_cpp(stmt, indent, generate_cpp):
    """Generate C++ code for an 'if' statement node.

    stmt: dict with keys 'condition' and 'body'
    indent: current indentation level (in blocks, not spaces)
    generate_cpp: function used to generate C++ for the nested body
    """
    space = " " * (indent * 4)
    cpp = space + f"if ({stmt['condition']}) {{\n"
    cpp += generate_cpp(stmt["body"], indent + 1)
    cpp += space + "}\n"
    return cpp
