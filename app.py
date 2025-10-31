# app.py
import sys
from parser import parser

def main():
    if len(sys.argv) < 2:
        print("Usage: python app.py <inputfile>")
        sys.exit(1)

    input_file = sys.argv[1]

    with open(input_file, "r", encoding="utf-8") as f:
        data = f.read()

    result = parser.parse(data)

    if not result:
        print("❌ Parsing failed. Check syntax in input file.")
        sys.exit(1)

    output_file = input_file.replace(".txt", "_converted.cpp")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"\n✅ Generated C++ code saved to: {output_file}\n")
    print(result)

if __name__ == "__main__":
    main()
