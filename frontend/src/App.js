import React, { useState } from "react";
import axios from "axios";

const VALID_TYPES = ["int", "float", "string", "long", "char", "array", "vector"];

function App() {
  const [code, setCode] = useState(
    "\\Fn Tournament() {\n    b \\gets a + 1;\n    \\While (a < b) {\n        \\If (a < 5) {\n            \\KwRet b;\n        }\n    }\n}\n"
  );
  const [cpp, setCpp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Tracks previously chosen datatypes so the backend never has to ask on stdin.
  const [typeHints, setTypeHints] = useState({});

  // When the backend reports a missing type, we surface a prompt in the UI.
  const [pendingVar, setPendingVar] = useState(null);
  const [selectedType, setSelectedType] = useState(VALID_TYPES[0]);

  const sendConvertRequest = async (currentCode, currentHints) => {
    const res = await axios.post("http://localhost:5000/convert", {
      code: currentCode,
      types: currentHints,
    });
    return res.data;
  };

  const handleConvert = async () => {
    setLoading(true);
    setError("");
    setCpp("");
    setPendingVar(null);
    try {
      const data = await sendConvertRequest(code, typeHints);
      setCpp(data.cpp || "");
    } catch (err) {
      const resp = err.response?.data;
      if (resp?.error === "missing_type" && resp.variable) {
        // Ask for the datatype in the frontend instead of the terminal.
        setPendingVar(resp.variable);
        setSelectedType((prev) => prev || VALID_TYPES[0]);
        setError("");
      } else {
        const msg = resp?.error || err.message || "Unknown error";
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmType = async () => {
    if (!pendingVar || !selectedType) return;
    const updatedHints = {
      ...typeHints,
      [pendingVar]: selectedType,
    };
    setTypeHints(updatedHints);
    setPendingVar(null);
    setError("");
    setLoading(true);
    setCpp("");
    try {
      const data = await sendConvertRequest(code, updatedHints);
      setCpp(data.cpp || "");
    } catch (err) {
      const resp = err.response?.data;
      if (resp?.error === "missing_type" && resp.variable) {
        setPendingVar(resp.variable);
        setSelectedType((prev) => prev || VALID_TYPES[0]);
        setError("");
      } else {
        const msg = resp?.error || err.message || "Unknown error";
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cpp);
      alert("C++ code copied to clipboard");
    } catch (e) {
      alert("Failed to copy");
    }
  };

  return (
    <div className="app-root">
      <div className="app-shell">
        <header className="app-header">
          <h1>Pseudo ➜ C++ Converter</h1>
          <p>Write your pseudo-code on the left and generate C++ on the right.</p>
        </header>
        <main className="app-main">
          <section className="pane pane-left">
            <div className="pane-header">
              <h2>Pseudo-code</h2>
            </div>
            <textarea
              className="code-input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              spellCheck={false}
            />
          </section>
          <section className="pane pane-right">
            <div className="pane-header">
              <h2>C++ Output</h2>
            </div>
            <textarea
              className="code-output"
              value={cpp}
              readOnly
              spellCheck={false}
            />
          </section>
        </main>
        <footer className="app-footer">
          <button className="btn primary" onClick={handleConvert} disabled={loading}>
            {loading ? "Converting..." : "Convert to C++"}
          </button>
          <button
            className="btn secondary"
            onClick={handleCopy}
            disabled={!cpp}
          >
            Copy C++
          </button>
          {pendingVar && (
            <div className="type-prompt">
              <span className="type-prompt-label">
                Select datatype for <strong>{pendingVar}</strong>:
              </span>
              <select
                className="type-select"
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
              >
                {VALID_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <button className="btn tertiary" onClick={handleConfirmType}>
                Confirm type
              </button>
            </div>
          )}
          {error && <div className="error-banner">{error}</div>}
        </footer>
      </div>
    </div>
  );
}

export default App;
