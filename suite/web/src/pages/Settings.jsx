import React from "react";
import { Settings as GearIcon, Terminal, Database } from "lucide-react";

export default function Settings({ onNotify }) {
  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-sub">Backend connection and suite configuration.</p>
      </div>
      <div className="grid-2">
        <div className="card">
          <h3>Backend API</h3>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10 }}>
            <GearIcon size={16} strokeWidth={2} color="#38bdf8" />
            <span style={{ fontSize: 12, color: "#94a3b8", fontFamily: "ui-monospace, Menlo, monospace" }}>http://127.0.0.1:8000</span>
          </div>
          <p style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.6 }}>
            The FastAPI backend serves REST endpoints and WebSocket progress streaming on port 8000.
            The Vite dev server proxies /api requests to the backend during development.
          </p>
        </div>
        <div className="card">
          <h3>Quick Commands</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ background: "#0b0f19", border: "1px solid #21314a", borderRadius: 8, padding: 10, fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12, color: "#a5f3fc" }}>
              cd suite/backend && poetry run uvicorn server.main:app --host 127.0.0.1 --port 8000
            </div>
            <div style={{ background: "#0b0f19", border: "1px solid #21314a", borderRadius: 8, padding: 10, fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12, color: "#a5f3fc" }}>
              cd suite/web && npm run dev
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
