from flask import Flask, request, jsonify
from flask_cors import CORS

from parser import parser, to_cpp, register_type_provider, MissingTypeError, valid_dtypes, parse_code

app = Flask(__name__)
CORS(app, resources={r"/convert": {"origins": ["http://localhost:3000", "*"]}})


def make_http_type_provider(type_hints: dict):
    """Create a non-interactive type provider for HTTP requests.

    ``type_hints`` is expected to be a mapping from variable name to datatype.
    If the requested variable is not present or the datatype is invalid, we
    raise ``MissingTypeError`` so the caller can ask the user via the
    frontend UI.
    """

    def _provider(var: str, allowed):
        if not isinstance(type_hints, dict):
            raise MissingTypeError(var)
        dtype = type_hints.get(var)
        if not isinstance(dtype, str) or dtype not in allowed:
            raise MissingTypeError(var)
        return dtype

    return _provider


@app.route("/convert", methods=["POST"])
def convert():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    type_hints = data.get("types", {}) or {}

    if not code.strip():
        return jsonify({"error": "No code provided"}), 400

    # Register a request-scoped type provider so the parser never reads stdin.
    register_type_provider(make_http_type_provider(type_hints))

    try:
        parsed = parse_code(code)
        cpp_code = to_cpp(parsed)
        return jsonify({"cpp": cpp_code})
    except MissingTypeError as e:
        # Let the frontend know which variable needs a datatype.
        return (
            jsonify(
                {
                    "error": "missing_type",
                    "variable": str(e),
                    "valid_types": valid_dtypes,
                }
            ),
            400,
        )
    except SyntaxError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:  # Fallback
        return jsonify({"error": f"Internal error: {e}"}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    # Default dev settings; frontend expects this port.
    app.run(host="0.0.0.0", port=5000, debug=True)
