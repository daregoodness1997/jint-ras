import React from "react";
import { List } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useRuns } from "../hooks/useRuns";
import { MetricCard } from "../components/Common";
import { listModels, listControllers } from "../lib/api";

export default function Dashboard({ onNotify }) {
  const navigate = useNavigate();
  const { runs, loading } = useRuns();
  const [models, setModels] = React.useState([]);
  const [controllers, setControllers] = React.useState([]);

  React.useEffect(() => {
    listModels().then((d) => setModels(d.models || [])).catch(() => {});
    listControllers().then((d) => setControllers(d.controllers || [])).catch(() => {});
  }, []);

  const completed = runs.filter((r) => r.status === "completed").length;
  const running = runs.filter((r) => r.status === "running").length;
  const failed = runs.filter((r) => r.status === "failed").length;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-sub">Overview of research sweep runs and system status.</p>
        </div>
        <div className="row">
        <button className="primary" onClick={() => navigate("/test")}>
          New Test
        </button>
        </div>
      </div>

      <div className="grid">
        <MetricCard title="Total Runs" value={runs.length} />
        <MetricCard title="Completed" value={completed} />
        <MetricCard title="Running" value={running} />
        <MetricCard title="Failed" value={failed} />
      </div>

      <div className="grid">
        <div className="card">
          <h3>Available Models</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {models.map((m) => (
              <button key={m.label} className="small" disabled>
                {m.label}
              </button>
            ))}
            {models.length === 0 && <span style={{ color: "#64748b", fontSize: 12 }}>loading…</span>}
          </div>
        </div>
        <div className="card">
          <h3>Available Controllers</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {controllers.map((c) => (
              <button key={c} className="small" disabled>
                {c}
              </button>
            ))}
            {controllers.length === 0 && <span style={{ color: "#64748b", fontSize: 12 }}>loading…</span>}
          </div>
        </div>
      </div>

      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <List size={18} strokeWidth={1.5} color="#38bdf8" />
          <span style={{ fontWeight: 700, fontSize: 14, color: "#e8eef7" }}>Recent Runs</span>
        </div>
        {loading ? (
          <div className="empty"><div className="skeleton" style={{ width: 200, height: 120 }} /></div>
        ) : runs.length === 0 ? (
          <div className="empty">No runs yet. Create a test to get started.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Run ID</th><th>Kind</th><th>Status</th><th>Progress</th><th>Created</th>
              </tr>
            </thead>
            <tbody>
              {runs.slice(0, 8).map((run) => (
                <tr key={run.run_id}>
                  <td style={{ fontFamily: "ui-monospace, Menlo, monospace", fontSize: 12, color: "#94a3b8" }}>{run.run_id.slice(0, 8)}…</td>
                  <td style={{ fontSize: 12, color: "#94a3b8" }}>{run.kind}</td>
                  <td><span className={`badge ${run.status}`} style={{ fontSize: "10px", padding: "2px 8px" }}>{run.status}</span></td>
                  <td>
                    <div className="progress" style={{ width: 90, height: 5, margin: 0 }}>
                      <div className="bar" style={{ width: `${(run.progress || 0) * 100}%` }} />
                    </div>
                  </td>
                  <td style={{ fontSize: 12, color: "#94a3b8", fontFamily: "ui-monospace, Menlo, monospace" }}>{(run.created_at || "").slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
