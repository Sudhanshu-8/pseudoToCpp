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
