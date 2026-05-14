import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from "react-resizable-panels";

const DEFAULT_CODE =
  "\\Fn Tournament() {\n    b \\gets a + 1;\n    \\While (a < b) {\n        \\If (a < 5) {\n            \\KwRet b;\n        }\n    }\n}\n";
const CODE_STORAGE_KEY = "pseudoToCpp.code";

function App() {
  const [code, setCode] = useState(() => {
    const saved = localStorage.getItem(CODE_STORAGE_KEY);
    return saved ?? DEFAULT_CODE;
  });
  const [cpp, setCpp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);
  const toastTimerRef = useRef(null);
  const [backendOnline, setBackendOnline] = useState(true);

  const [typeHints, setTypeHints] = useState({});
  const [typeHistory, setTypeHistory] = useState([]);
  const [validTypes, setValidTypes] = useState({ datatypes: [], datastructures: [] });
  const [pendingVar, setPendingVar] = useState(null);
  const [selectedBaseType, setSelectedBaseType] = useState("");
  const [selectedElemType, setSelectedElemType] = useState("int");

  const [templates, setTemplates] = useState([]);
  const [showTemplates, setShowTemplates] = useState(false);
  const textareaRef = useRef(null);

  const fetchTypes = async () => {
    try {
      const res = await axios.get("/types");
      setValidTypes(res.data);
      if (res.data.datatypes && res.data.datatypes.length > 0) {
        setSelectedBaseType(res.data.datatypes[0]);
      }
    } catch (err) {
      console.error("Failed to fetch types:", err);
    }
  };

  const fetchTemplates = async () => {
    try {
      const res = await axios.get("/templates");
      setTemplates(res.data);
    } catch (err) {
      console.error("Failed to fetch templates:", err);
    }
  };

  useEffect(() => {
    fetchTypes();
    fetchTemplates();
  }, []);

  const sendConvertRequest = async (currentCode, currentHints) => {
    const res = await axios.post("/convert", {
      code: currentCode,
      types: currentHints,
    });
    return res.data;
  };

  const checkBackend = async () => {
    try {
      await axios.get("/health", { timeout: 3000 });
      setBackendOnline(true);
      setError((prev) => (prev.startsWith("Backend is offline") ? "" : prev));
      return true;
    } catch {
      setBackendOnline(false);
      return false;
    }
  };

  const handleConvert = async (hints = typeHints) => {
    const online = await checkBackend();
    if (!online) {
      setError("Backend is offline. Please start server.py and try again.");
      return;
    }

    setLoading(true);
    setError("");
    setCpp("");
    
    try {
      const data = await sendConvertRequest(code, hints);
      setCpp(data.cpp || "");
      
      if (data.resolved_types) {
        const history = Object.entries(data.resolved_types).map(([v, t]) => ({ variable: v, type: t }));
        setTypeHistory(history);
        setTypeHints(data.resolved_types);
      }
    } catch (err) {
      const resp = err.response?.data;
      if (resp?.error === "missing_type" && resp.variable) {
        setPendingVar(resp.variable);
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
    if (!pendingVar || !selectedBaseType) return;
    
    let finalType = selectedBaseType;
    const isDS = ["vector", "array", "set"].includes(selectedBaseType);
    if (isDS) {
      finalType = `${selectedBaseType}_${selectedElemType}`;
    }

    const updatedHints = { ...typeHints, [pendingVar]: finalType };
    setTypeHints(updatedHints);
    setPendingVar(null);
    handleConvert(updatedHints);
  };

  const handleOverrideType = (variable) => {
    const newHints = { ...typeHints };
    delete newHints[variable];
    setTypeHints(newHints);
    setPendingVar(variable);
    
    const current = typeHints[variable] || "";
    if (current.includes("_")) {
      const parts = current.split("_");
      setSelectedBaseType(parts[0]);
      setSelectedElemType(parts[1]);
    } else {
      setSelectedBaseType(current || (validTypes.datatypes && validTypes.datatypes[0]) || "int");
      setSelectedElemType("int");
    }
  };

  const handleInsertTemplate = async (templateId) => {
    try {
      const res = await axios.get(`/template/${templateId}`);
      const content = res.data.content;
      
      const textarea = textareaRef.current;
      if (!textarea) {
        setCode(prev => prev + "\n" + content);
        return;
      }

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newCode = code.substring(0, start) + content + code.substring(end);
      setCode(newCode);
      setShowTemplates(false);
      
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(start + content.length, start + content.length);
      }, 0);
    } catch (err) {
      setToast({ type: "error", message: "Failed to load template" });
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(cpp);
      setToast({ type: "success", message: "C++ code copied to clipboard" });
    } catch (e) {
      setToast({ type: "error", message: "Failed to copy" });
    }
  };

  useEffect(() => {
    localStorage.setItem(CODE_STORAGE_KEY, code);
  }, [code]);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      const ok = await checkBackend();
      if (!active) return;
      if (!ok && !loading) {
        setError(prev => prev || "Backend is offline. Please start server.py.");
      }
    };
    poll();
    const intervalId = setInterval(poll, 10000);
    return () => { active = false; clearInterval(intervalId); };
  }, [loading]);

  useEffect(() => {
    if (!toast) return;
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToast(null), 2200);
    return () => { if (toastTimerRef.current) clearTimeout(toastTimerRef.current); };
  }, [toast]);

  const isSelectedDS = ["vector", "array", "set"].includes(selectedBaseType);

  const getWarning = () => {
    if (!pendingVar || !selectedBaseType) return null;
    const isDataStructure = isSelectedDS;
    const varNameMatch = pendingVar.match(/^(\w+)/);
    const varName = varNameMatch ? varNameMatch[1] : pendingVar;
    if (isDataStructure && varName.length === 1) {
      return `Warning: '${varName}' looks like a scalar but you selected a datastructure.`;
    }
    return null;
  };

  return (
    <div className="app-root">
      {toast && (
        <div className={`toast ${toast.type}`} role="status">
          <span className="toast-dot" />
          <span className="toast-message">{toast.message}</span>
          <button className="toast-close" onClick={() => setToast(null)}>×</button>
        </div>
      )}
      <div className="app-shell">
        <header className="app-header">
          <div className="header-main">
            <div>
              <h1>Pseudo ➜ C++ Converter</h1>
              <p>Write pseudo-code and generate C++ instantly.</p>
            </div>
            <div className="header-actions">
              <div className="template-dropdown-container">
                <button className="btn secondary" onClick={() => setShowTemplates(!showTemplates)}>
                  Add Algorithm ▾
                </button>
                {showTemplates && (
                  <div className="template-dropdown">
                    {templates.map(t => (
                      <div key={t.id} className="template-item" onClick={() => handleInsertTemplate(t.id)}>
                        {t.name}
                      </div>
                    ))}
                    {templates.length === 0 && <div className="template-empty">No templates found</div>}
                  </div>
                )}
              </div>
              <p className={`status-line ${backendOnline ? "online" : "offline"}`}>
                {backendOnline ? "● Online" : "● Offline"}
              </p>
            </div>
          </div>
        </header>
        
        <main className="app-main flex-main">
          <PanelGroup direction="horizontal">
            <Panel defaultSize={40} minSize={20} className="pane pane-left">
              <div className="pane-header">
                <h2>Pseudo-code</h2>
              </div>
              <textarea
                ref={textareaRef}
                className="code-input"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                spellCheck={false}
                placeholder="Write your \Fn here..."
              />
            </Panel>
            <PanelResizeHandle className="resize-handle" />
            <Panel defaultSize={25} minSize={15} className="pane pane-middle">
              <div className="pane-header">
                <h2>Type Map</h2>
              </div>
              <div className="type-history">
                {typeHistory.length === 0 ? (
                  <div className="type-history-empty">No types interpreted yet</div>
                ) : (
                  <div className="type-history-list">
                    {typeHistory.map((item, idx) => (
                      <div key={idx} className="type-history-item">
                        <div className="type-info">
                          <span className="type-var">{item.variable}</span>
                          <span className="type-arrow">→</span>
                          <span className="type-dtype">{item.type.replace("_", "<") + (item.type.includes("_") ? ">" : "")}</span>
                        </div>
                        <button 
                          className="type-refresh" 
                          onClick={() => handleOverrideType(item.variable)}
                          title="Change type"
                        >
                          ⟳
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Panel>
            <PanelResizeHandle className="resize-handle" />
            <Panel defaultSize={35} minSize={20} className="pane pane-right">
              <div className="pane-header">
                <h2>C++ Output</h2>
              </div>
              <textarea
                className="code-output"
                value={cpp}
                readOnly
                spellCheck={false}
                placeholder="C++ code will appear here..."
              />
            </Panel>
          </PanelGroup>
        </main>

        <footer className="app-footer">
          <button className="btn primary" onClick={() => handleConvert()} disabled={loading}>
            {loading ? "Converting..." : "Convert to C++"}
          </button>
          <button className="btn secondary" onClick={handleCopy} disabled={!cpp}>
            Copy C++
          </button>
          {pendingVar && (
            <div className="type-prompt">
              <span className="type-prompt-label">Type for <strong>{pendingVar}</strong>:</span>
              <div className="nested-selects">
                <select className="type-select" value={selectedBaseType} onChange={(e) => setSelectedBaseType(e.target.value)}>
                  <optgroup label="Datatypes">
                    {validTypes.datatypes?.map(t => <option key={t} value={t}>{t}</option>)}
                  </optgroup>
                  <optgroup label="Datastructures">
                    <option value="vector">vector</option>
                    <option value="array">array</option>
                    <option value="set">set</option>
                  </optgroup>
                </select>
                
                {isSelectedDS && (
                  <>
                    <span className="nested-arrow">➜</span>
                    <select className="type-select elem-select" value={selectedElemType} onChange={(e) => setSelectedElemType(e.target.value)}>
                      {validTypes.datatypes?.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </>
                )}
              </div>
              <button className="btn tertiary" onClick={handleConfirmType}>Confirm</button>
              {getWarning() && <span className="type-warning">{getWarning()}</span>}
            </div>
          )}
          {error && <div className="error-banner">{error}</div>}
        </footer>
      </div>
    </div>
  );
}

export default App;
