"""Helpers for generating C++ code for for-loops."""


def generate_for_cpp(stmt, indent, format_assignment, generate_cpp):
    """Generate C++ code for a 'for' statement node.

    stmt: dict with keys 'init', 'condition', 'update', and 'body'
    indent: current indentation level (in blocks, not spaces)
    format_assignment: function used to format assignment nodes
    generate_cpp: function used to generate C++ for the nested body
    """
    space = " " * (indent * 4)

    init_part = ""
    if stmt["init"] is not None:
        # No type declaration - variable already declared at function start
        init_part = format_assignment(stmt["init"], include_type=False)

    cond_part = stmt["condition"] if stmt["condition"] is not None else ""

    update_part = ""
    if stmt["update"] is not None:
        update_part = format_assignment(stmt["update"], include_type=False)

    cpp = space + f"for ({init_part}; {cond_part}; {update_part}) {{\n"
    cpp += generate_cpp(stmt["body"], indent + 1)
    cpp += space + "}\n"
    return cpp