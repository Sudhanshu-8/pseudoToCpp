"""Helpers for generating C++ code for if-statements."""


def generate_if_cpp(stmt, indent, generate_cpp):
    """Generate C++ code for an 'if' statement node.

    stmt: dict with keys 'condition', 'body', 'elifs', and 'else_body'
    indent: current indentation level (in blocks, not spaces)
    generate_cpp: function used to generate C++ for the nested body
    """
    space = " " * (indent * 4)
    cpp = space + f"if ({stmt['condition']}) {{\n"
    cpp += generate_cpp(stmt["body"], indent + 1)
    cpp += space + "}"

    # Handle else-if blocks
    elifs = stmt.get("elifs", [])
    for elif_node in elifs:
        cpp += f" else if ({elif_node['condition']}) {{\n"
        cpp += generate_cpp(elif_node["body"], indent + 1)
        cpp += space + "}"

    # Handle else block
    else_body = stmt.get("else_body")
    if else_body is not None:
        cpp += " else {\n"
        cpp += generate_cpp(else_body, indent + 1)
        cpp += space + "}"

    cpp += "\n"
    return cpp
