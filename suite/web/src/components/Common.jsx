import { Table, FileText, RotateCw, Save, AlertTriangle } from "lucide-react";

export function MetricCard({ title, value, subtitle, trend }) {
  return (
    <div className="card metric">
      <div className="lbl">{title}</div>
      <div className="val">{value == null ? "\u2014" : value}</div>
      {subtitle && <div className="lbl" style={{ fontSize: "11px", marginTop: 2 }}>{subtitle}</div>}
      {trend && <div style={{ fontSize: "11px", color: trend >= 0 ? "#4ade80" : "#f87171" }}>{trend >= 0 ? "\u25b2" : "\u25bc"} {Math.abs(trend).toFixed(2)}</div>}
    </div>
  );
}

export function StatusBadge({ status, className }) {
  const kind = (status || "queued").toLowerCase();
  return <span className={`badge ${kind} ${className || ""}`}>{kind}</span>;
}

export function PlotPanel({ title, src, width }) {
  return (
    <div className="card plot-wrap" style={{ maxWidth: width || "100%", display: "flex", flexDirection: "column", gap: 8 }}>
      {title && <div style={{ fontSize: "12px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>{title}</div>}
      {src ? (
        <img src={src} alt={title} style={{ width: "100%", maxWidth: width || "100%", height: "auto", borderRadius: 6, background: "#0b0f19" }} />
      ) : (
        <div className="empty">No plot available</div>
      )}
    </div>
  );
}

export function MetricsTable({ metrics }) {
  if (!metrics) return <div className="empty">No metrics yet.</div>;
  const rows = Object.entries(metrics).filter(([, v]) => v != null && String(v) !== "nan");
  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <Table size={16} strokeWidth={1.5} color="#38bdf8" />
        <span style={{ fontWeight: 700, fontSize: 14, color: "#e8eef7" }}>Metrics</span>
      </div>
      <table>
        <thead>
          <tr><th>Metric</th><th>Value</th></tr>
        </thead>
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <td style={{ color: "#94a3b8", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.04em", width: "42%" }}>{k.replace(/_/g, " ")}</td>
              <td style={{ fontVariantNumeric: "tabular-nums", fontSize: 13 }}>
                {typeof v === "number" ? v.toFixed(4) : String(v)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RunTable({ runs, onRunClick }) {
  if (!runs || runs.length === 0) return <div className="empty">No test runs yet.</div>;
  return (
    <div className="card">
      <table>
        <thead>
          <tr>
            <th style={{ width: "52px" }} />
            <th>Run ID</th>
            <th>Kind</th>
            <th>Model / Ctrl</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Created</th>
            <th style={{ textAlign: "right", width: "120px" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.run_id} style={{ cursor: "pointer" }} onClick={() => onRunClick && onRunClick(run.run_id)}>
              <td style={{ width: "52px" }}>
                {run.status === "running" ? (
                  <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: "50%", background: "#4ade80", boxShadow: "0 0 6px #4ade80" }} />
                ) : run.status === "completed" ? (
                  <span style={{ color: "#4ade80" }}>&#10004;</span>
                ) : run.status === "failed" ? (
                  <span style={{ color: "#f87171" }}>&#10006;</span>
                ) : (
                  <span style={{ color: "#94a3b8" }}>\u25cb</span>
                )}
              </td>
              <td style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12, color: "#94a3b8" }}>{run.run_id.slice(0, 8)}…</td>
              <td style={{ fontSize: 12, color: "#94a3b8" }}>{run.kind}</td>
              <td style={{ fontSize: 12 }}>{run.model || "\u2014"} / {run.controller || "\u2014"}</td>
              <td>
                <span
                  className={`badge ${run.status}`}
                  style={{ fontSize: "10px", padding: "2px 8px" }}
                >
                  {run.status}
                </span>
              </td>
              <td>
                <div className="progress" style={{ width: 100, height: 6, margin: 0 }}>
                  <div className="bar" style={{ width: `${(run.progress || 0) * 100}%` }} />
                </div>
                <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>{Math.round((run.progress || 0) * 100)}%</div>
              </td>
              <td style={{ fontSize: 12, color: "#94a3b8", fontFamily: "ui-monospace, Menlo, monospace" }}>{(run.created_at || "").slice(0, 16)}</td>
              <td style={{ textAlign: "right" }}>
                <button className="small" onClick={(e) => { e.stopPropagation(); onRunClick && onRunClick(run.run_id); }}>View</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Toast({ message, type = "info", onClose }) {
  if (!message) return null;
  const border = type === "success" ? "#4ade80" : type === "error" ? "#f87171" : "#38bdf8";
  return (
    <div className="toast" style={{ borderLeftColor: border }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>{message}</div>
      {onClose && <button className="small" onClick={onClose} style={{ marginLeft: "auto", padding: 2, opacity: 0.6 }}>&#215;</button>}
    </div>
  );
}
