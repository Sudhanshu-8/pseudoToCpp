import os
import sys
import webbrowser
from threading import Timer
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from parser import parser, to_cpp, register_type_provider, MissingTypeError, valid_dtypes, parse_code

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

app = Flask(__name__, static_folder=get_resource_path("frontend/build"), static_url_path="")
CORS(app, resources={r"/*": {"origins":"*"}})

# Group the valid types
DATATYPES = ["int", "float", "double", "string", "long", "char", "bool"]
# Filter from valid_dtypes, categorizing the rest as datastructures
DATASTRUCTURES = [t for t in valid_dtypes if t not in DATATYPES]

def make_http_type_provider(type_hints: dict):
    """Create a non-interactive type provider for HTTP requests.

    ``type_hints`` is expected to be a mapping from variable name to datatype.
    If the requested variable is not present, we raise ``MissingTypeError``.
    """

    def _provider(var: str, allowed):
        if not isinstance(type_hints, dict):
            raise MissingTypeError(var)
        dtype = type_hints.get(var)
        if not isinstance(dtype, str):
            raise MissingTypeError(var)
        return dtype

    return _provider


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

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
        from parser import symbol_table
        parsed = parse_code(code)
        cpp_code = to_cpp(parsed)
        
        # Flatten symbol_table for frontend: {(func, var): type} -> {"var (in func)": type}
        resolved_types = {}
        for (f, v), t in symbol_table.items():
            key = f"{v} (in {f})" if f else v
            resolved_types[key] = t
            
        return jsonify({
            "cpp": cpp_code,
            "resolved_types": resolved_types
        })
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


@app.route("/types", methods=["GET"])
def types():
    return jsonify({
        "datatypes": [t for t in DATATYPES if t in valid_dtypes],
        "datastructures": DATASTRUCTURES
    })


@app.route("/templates", methods=["GET"])
def list_templates():
    folder = get_resource_path("algo-templates")
    if not os.path.exists(folder):
        return jsonify([])
    files = [f for f in os.listdir(folder) if f.endswith(".txt")]
    return jsonify([{"name": f.replace(".txt", "").replace("_", " ").title(), "id": f} for f in files])


@app.route("/template/<id>", methods=["GET"])
def get_template(id):
    path = os.path.join(get_resource_path("algo-templates"), id)
    if not os.path.exists(path):
        return jsonify({"error": "Template not found"}), 404
    with open(path, "r") as f:
        return jsonify({"content": f.read()})

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    # In production/PyInstaller, we don't want debug mode
    # In dev, opening browser once is enough
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1.5, open_browser).start()
    
    app.run(host="127.0.0.1", port=5000, debug=False)
