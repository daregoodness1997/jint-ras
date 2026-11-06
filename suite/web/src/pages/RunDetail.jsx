import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { RefreshCw, Activity, FileText, AlertCircle } from "lucide-react";
import { getSweep, wsUrl, toNumber, listRuns } from "../lib/api";
import { StatusBadge, MetricsTable, Toast } from "../components/Common";

export default function RunDetail({ onNotify }) {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [run, setRun] = React.useState(null);
  const [result, setResult] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [status, setStatus] = React.useState("running");
  const [progress, setProgress] = React.useState(0);
  const [error, setError] = React.useState(null);

  const load = () => {
    getSweep(runId).then((d) => {
      setRun({ run_id: d.run_id, kind: d.kind, status: d.status, progress: d.progress, model: d.result?.model, controller: d.result?.controller, created_at: d.created_at, finished_at: d.finished_at });
      setResult(d.result);
      setStatus(d.status || "idle");
      setProgress(d.progress || 0);
      setError(d.error || null);
      setLoading(false);
    }).catch(() => { setLoading(false); });
  };

  React.useEffect(() => {
    load();
    if (runId) {
      const ws = new WebSocket(wsUrl(runId));
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data);
        setStatus(data.status || "running");
        setProgress(data.progress || 0);
        if (data.status === "completed") { load(); onNotify("Run completed", "success"); ws.close(); }
        if (data.status === "failed") { setError(data.error); setStatus("failed"); ws.close(); onNotify("Run failed", "error"); }
      };
      return () => ws.close();
    }
  }, [runId]);

  const back = () => navigate("/runs");

  if (loading) return <div className="page"><div className="empty">Loading run…</div></div>;
  if (!run) return <div className="page"><div className="empty">Run not found.</div></div>;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <button onClick={back} className="small" style={{ marginRight: 10, color: "#38bdf8" }}>&larr; Back to runs</button>
          <h1 className="page-title">Run {run.run_id.slice(0, 8)}…</h1>
          <p className="page-sub">{run.kind} test &bull; {run.model || "\u2014"} / {run.controller || "\u2014"}</p>
        </div>
        <div className="row">
          <StatusBadge status={status} style={{ fontSize: "11px" }} />
          <button className="small" onClick={load}><RefreshCw size={16} strokeWidth={2} /></button>
        </div>
      </div>

      <div className="progress" style={{ width: "100%" }}>
        <div className="bar" style={{ width: `${progress * 100}%` }} />
      </div>
      <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6 }}>{Math.round((progress || 0) * 100)}% &bull; {status}</div>

      {error && <div style={{ marginTop: 10, color: "#f87171", fontSize: 12 }}>{error}</div>}

      {result && (
        <div className="card" style={{ marginTop: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <FileText size={18} strokeWidth={1.5} color="#38bdf8" />
            <span style={{ fontWeight: 700, fontSize: 15, color: "#e8eef7" }}>
              Results {run.kind === "sweep" ? `(${result.n_cases} cases)` : "(single simulation)"}
            </span>
          </div>
          <div className="grid">
            <MetricCard2 title="Model" value={result.model} />
            <MetricCard2 title="Controller" value={result.controller} />
            <MetricCard2 title="Kind" value={run.kind} />
            {result.n_cases != null && <MetricCard2 title="Cases" value={result.n_cases} />}
            {result.n_rows != null && <MetricCard2 title="Rows" value={result.n_rows} />}
            <MetricCard2 title="Duration (s)" value={result.duration} />
            <MetricCard2 title="f_sim" value={result.f_sim} />
          </div>

          {/* Sweep results table */}
          {result.axis_names && result.cases && (
            <table>
              <thead>
                <tr>
                  {result.axis_names.map((n) => <th key={n}>{n}</th>)}
                  <th style={{ width: "120px" }}>Distance</th>
                  <th style={{ width: "110px" }}>Speed</th>
                  <th style={{ width: "110px" }}>Energy</th>
                  <th style={{ width: "110px" }}>Sat Frac</th>
                  <th style={{ width: "100px" }}>Behavior</th>
                  <th style={{ width: "80px" }}>Error</th>
                </tr>
              </thead>
              <tbody>
                {result.cases.map((c, i) => (
                  <tr key={i}>
                    {result.axis_names.map((n) => (
                      <td key={n} style={{ fontSize: 12 }}>{c.values[n] ?? ""}</td>
                    ))}
                    <td style={{ fontSize: 12, fontVariantNumeric: "tabular-nums" }}>{toNumber(c.metrics.distance)?.toFixed(4) ?? "\u2014"}</td>
                    <td style={{ fontSize: 12, fontVariantNumeric: "tabular-nums" }}>{toNumber(c.metrics.speed)?.toFixed(4) ?? "\u2014"}</td>
                    <td style={{ fontSize: 12, fontVariantNumeric: "tabular-nums" }}>{toNumber(c.metrics.energy)?.toFixed(4) ?? "\u2014"}</td>
                    <td style={{ fontSize: 12, fontVariantNumeric: "tabular-nums" }}>{toNumber(c.metrics.sat_frac)?.toFixed(4) ?? "\u2014"}</td>
                    <td style={{ fontSize: 11, color: "#94a3b8" }}>{c.metrics.behavior || "\u2014"}</td>
                    <td style={{ fontSize: 11, color: c.error ? "#f87171" : "#94a3b8" }}>{c.error || "\u2014"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {/* Single simulation metrics */}
          {!result.axis_names && result.metrics && (
            <div style={{ marginTop: 10 }}>
              <MetricsTable metrics={result.metrics} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetricCard2({ title, value }) {
  return (
    <div style={{ background: "#11192b", border: "1px solid #21314a", borderRadius: 8, padding: 12, display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 700 }}>{title}</div>
      <div style={{ fontSize: 16, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{value == null ? "\u2014" : value}</div>
    </div>
  );
}
