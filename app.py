<<<<<<< HEAD
from parser import parser, to_cpp, register_type_provider, valid_dtypes, MissingTypeError


def cli_type_provider(var, allowed):
    # Fallback interactive provider for the CLI tool only.
    choices = ", ".join(allowed)
    dtype = input(f"Enter datatype for variable '{var}' ({choices}): ").strip()
    while dtype not in allowed:
        dtype = input(f"Invalid datatype. Enter again for '{var}' ({choices}): ").strip()
    return dtype


ndef main():
    register_type_provider(cli_type_provider)

    with open("input.txt") as f:
        data = f.read()

    print("🔹 Starting parsing... You’ll be asked for variable datatypes where needed.\n")

    try:
        result = parse_code(data)
    except MissingTypeError as e:
        raise SystemExit(f"Missing type for variable: {e}")

    cpp_code = to_cpp(result)
    print("\n✅ Generated C++ code:\n")
    print(cpp_code)

    with open("output.cpp", "w") as f:
        f.write(cpp_code)


if __name__ == "__main__":
    main()
=======
from parser import parser, to_cpp

with open("input.txt") as f:
    data = f.read()

print("🔹 Starting parsing... You’ll be asked for variable datatypes where needed.\n")

result = parser.parse(data)

cpp_code = to_cpp(result)
print("\n✅ Generated C++ code:\n")
print(cpp_code)

with open("output.cpp", "w") as f:
    f.write(cpp_code)
>>>>>>> 5b0bb2920e139ef8d09a02537253009599a6ea29
