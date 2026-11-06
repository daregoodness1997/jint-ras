import React from "react";
import { Play, Loader2, RefreshCw, Save, FileText, Activity } from "lucide-react";
import {
  api,
  listModels,
  listControllers,
  listParams,
  startSimulate,
  getSimulate,
  startSweep,
  getSweep,
  listRuns,
  wsUrl,
  toNumber,
} from "../lib/api";
import { StatusBadge, MetricsTable, Toast } from "../components/Common";

const DEFAULTS = {
  model: "JINT",
  controller: "pd",
  A_deg: 50,
  f: 0.8,
  rho_deg_s: 0,
  duration: 6,
  f_sim: 500,
  steady_fraction: 0.5,
};

export default function TestConfig({ onNotify }) {
  const [models, setModels] = React.useState([]);
  const [controllers, setControllers] = React.useState([]);
  const [params, setParams] = React.useState([]);
  const [form, setForm] = React.useState({ ...DEFAULTS, axes: { A_deg: [40, 50, 60], f: [0.6, 0.8, 1.0], rho_deg_s: [0, 25, 50] } });
  const [simForm, setSimForm] = React.useState({ ...DEFAULTS });
  const [loading, setLoading] = React.useState(false);
  const [simLoading, setSimLoading] = React.useState(false);
  const [run, setRun] = React.useState(null);
  const [result, setResult] = React.useState(null);
  const [simResult, setSimResult] = React.useState(null);
  const [simRun, setSimRun] = React.useState(null);
  const [simProgress, setSimProgress] = React.useState(0);
  const [simStatus, setSimStatus] = React.useState("idle");
  const [progress, setProgress] = React.useState(0);
  const [status, setStatus] = React.useState("idle"); // idle | running | completed | failed
  const [error, setError] = React.useState(null);
  const [wsMsg, setWsMsg] = React.useState(null);

  React.useEffect(() => {
    listModels().then((d) => setModels(d.models || [])).catch(() => {});
    listControllers().then((d) => setControllers(d.controllers || [])).catch(() => {});
  }, []);

  const handleModelChange = (e) => {
    setForm((p) => ({ ...p, model: e.target.value }));
    setSimForm((p) => ({ ...p, model: e.target.value }));
    listParams(e.target.value).then((d) => setParams(d.params || [])).catch(() => {});
  };

  const updateAxis = (param, values) => {
    setForm((p) => ({ ...p, axes: { ...p.axes, [param]: values } }));
  };

  const startSweepTest = async (e) => {
    e.preventDefault();
    setLoading(true); setError(null); setRun(null); setResult(null); setProgress(0); setStatus("running");
    try {
      const { run_id } = await startSweep(form);
      setRun({ run_id, kind: "sweep" });
      const ws = new WebSocket(wsUrl(run_id));
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data);
        setWsMsg(data);
        setProgress(data.progress || 0);
        setStatus(data.status || "running");
        if (data.status === "completed") {
          getSweep(run_id).then((d) => { setResult(d.result); setStatus("completed"); setLoading(false); ws.close(); onNotify("Sweep completed", "success"); });
        }
        if (data.status === "failed") { setStatus("failed"); setError(data.error); setLoading(false); ws.close(); onNotify("Sweep failed", "error"); }
      };
      ws.onclose = () => {};
    } catch (err) {
      setError(String(err.response?.data?.detail || err.message));
      setStatus("failed"); setLoading(false); onNotify("Failed to start sweep", "error");
    }
  };

  const runSimulate = async (e) => {
    e.preventDefault();
    setSimStatus("running"); setSimProgress(0); setSimRun(null); setSimResult(null); setError(null);
    try {
      const { run_id } = await startSimulate(simForm);
      setSimRun({ run_id, kind: "simulate" });
      const ws = new WebSocket(wsUrl(run_id));
      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data);
        setSimProgress(data.progress || 0);
        setSimStatus(data.status || "running");
        if (data.status === "completed") {
          getSimulate(run_id).then((d) => {
            setSimResult(d.result); setSimStatus("completed"); ws.close(); onNotify("Simulation complete", "success");
          });
        }
        if (data.status === "failed") { setSimStatus("failed"); setError(data.error); ws.close(); onNotify("Simulation failed", "error"); }
      };
      ws.onclose = () => {};
    } catch (err) {
      setError(String(err.response?.data?.detail || err.message));
      setSimStatus("failed"); onNotify("Failed to start simulation", "error");
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">New Test</h1>
        <p className="page-sub">Configure and run a parameter sweep or single simulation.</p>
      </div>

      {error && <Toast message={error} type="error" onClose={() => setError(null)} />}

      <div className="grid-2">
        {/* Sweep config */}
        <div className="card">
          <h3>Parameter Sweep</h3>
          <form onSubmit={startSweepTest} className="stack">
            <div className="row">
              <div className="col">
                <label>Model</label>
                <select value={form.model} onChange={handleModelChange}>
                  {models.map((m) => (m.label ? <option key={m.label} value={m.label}>{m.label}</option> : <option key={m} value={m}>{m}</option>))}
                </select>
              </div>
              <div className="col">
                <label>Controller</label>
                <select value={form.controller} onChange={(e) => setForm((p) => ({ ...p, controller: e.target.value }))}>
                  {controllers.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
            <label style={{ marginTop: 10 }}>Sweep Axes (param &#8594; comma-separated values)</label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 10, marginBottom: 12 }}>
              {Object.entries(form.axes || {}).map(([key, vals]) => (
                <div key={key} className="col" style={{ minWidth: 0 }}>
                  <label>{key}</label>
                  <input
                    value={Array.isArray(vals) ? vals.join(",") : String(vals)}
                    onChange={(e) => updateAxis(key, e.target.value.split(",").map(Number).filter((v) => !Number.isNaN(v)))}
                  />
                </div>
              ))}
            </div>
            <div className="row">
              <div className="col">
                <label>Duration (s)</label>
                <input type="number" value={form.duration} onChange={(e) => setForm((p) => ({ ...p, duration: Number(e.target.value) }))} />
              </div>
              <div className="col">
                <label>f_sim</label>
                <input type="number" value={form.f_sim} onChange={(e) => setForm((p) => ({ ...p, f_sim: Number(e.target.value) }))} />
              </div>
            </div>
            <div className="row" style={{ marginTop: 10 }}>
              <button className="primary" disabled={loading} style={{ width: "100%" }}>
                {loading ? (<Loader2 size={16} />) : (<Play size={16} />)} Start Sweep
              </button>
            </div>
          </form>
        </div>

        {/* Live status */}
        <div className="card">
          <h3>Status</h3>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <StatusBadge status={status} />
            {run && <span style={{ fontSize: 12, color: "#64748b", fontFamily: "ui-monospace, Menlo, monospace" }}>{run.run_id.slice(0, 8)}…</span>}
          </div>
          <div className="progress" style={{ width: "100%" }}>
            <div className="bar" style={{ width: `${progress * 100}%` }} />
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6 }}>{wsMsg?.message || ""}</div>
          {status === "completed" && (
            <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
              <button className="small" onClick={() => { setResult(null); setRun(null); setStatus("idle"); setProgress(0); onNotify("Reset", "info"); }}>Reset</button>
              <button className="primary small" onClick={() => startSweepTest({ preventDefault: () => {} })}>Re-run</button>
            </div>
          )}
          {status === "failed" && (
            <div style={{ marginTop: 8, color: "#f87171", fontSize: 12 }}>{error}</div>
          )}
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="card" style={{ marginTop: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
            <FileText size={18} strokeWidth={1.5} color="#38bdf8" />
            <span style={{ fontWeight: 700, fontSize: 15, color: "#e8eef7" }}>Sweep Results ({result.n_cases} cases)</span>
          </div>
          <MetricsTable metrics={{ n_cases: result.n_cases, model: result.model, controller: result.controller, duration: result.duration, f_sim: result.f_sim }} />
          <table>
            <thead>
              <tr>
                {result.axis_names.map((n) => <th key={n}>{n}</th>)}
                <th style={{ width: "150px" }}>Distance</th>
                <th style={{ width: "110px" }}>Speed</th>
                <th style={{ width: "110px" }}>Energy</th>
                <th style={{ width: "100px" }}>Behavior</th>
                <th style={{ width: "90px" }}>Error</th>
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
                  <td style={{ fontSize: 11, color: "#94a3b8" }}>{c.metrics.behavior || "\u2014"}</td>
                  <td style={{ fontSize: 11, color: c.error ? "#f87171" : "#94a3b8" }}>{c.error || "\u2014"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Single simulation */}
      <div className="card" style={{ marginTop: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <Activity size={18} strokeWidth={1.5} color="#38bdf8" />
          <span style={{ fontWeight: 700, fontSize: 15, color: "#e8eef7" }}>Single Simulation</span>
        </div>
        <form onSubmit={runSimulate} className="stack">
          <div className="row">
            <div className="col">
              <label>Model</label>
              <select value={simForm.model} onChange={(e) => setSimForm((p) => ({ ...p, model: e.target.value }))}>
                {models.map((m) => (m.label ? <option key={m.label} value={m.label}>{m.label}</option> : <option key={m} value={m}>{m}</option>))}
              </select>
            </div>
            <div className="col">
              <label>Controller</label>
              <select value={simForm.controller} onChange={(e) => setSimForm((p) => ({ ...p, controller: e.target.value }))}>
                {controllers.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className="row">
            <div className="col"><label>A_deg</label><input type="number" value={simForm.A_deg} onChange={(e) => setSimForm((p) => ({ ...p, A_deg: Number(e.target.value) }))} /></div>
            <div className="col"><label>f</label><input type="number" step="0.01" value={simForm.f} onChange={(e) => setSimForm((p) => ({ ...p, f: Number(e.target.value) }))} /></div>
            <div className="col"><label>rho_deg_s</label><input type="number" value={simForm.rho_deg_s} onChange={(e) => setSimForm((p) => ({ ...p, rho_deg_s: Number(e.target.value) }))} /></div>
            <div className="col"><label>Duration</label><input type="number" value={simForm.duration} onChange={(e) => setSimForm((p) => ({ ...p, duration: Number(e.target.value) }))} /></div>
            <div className="col"><label>f_sim</label><input type="number" value={simForm.f_sim} onChange={(e) => setSimForm((p) => ({ ...p, f_sim: Number(e.target.value) }))} /></div>
          </div>
          <button className="primary" type="submit" disabled={simStatus === "running"} style={{ width: "100%" }}>
            {simStatus === "running" ? (<Loader2 size={16} />) : (<Play size={16} />)} Run Simulation
          </button>
        </form>
        {simStatus === "running" && (
          <div style={{ marginTop: 10 }}>
            <div className="progress" style={{ width: "100%" }}>
              <div className="bar" style={{ width: `${simProgress * 100}%` }} />
            </div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6 }}>{Math.round((simProgress || 0) * 100)}% &bull; {simStatus}</div>
          </div>
        )}
        {simStatus === "failed" && (
          <div style={{ marginTop: 10, color: "#f87171", fontSize: 12 }}>{error}</div>
        )}
        {simResult && (
          <div style={{ marginTop: 14 }}>
            <MetricsTable metrics={simResult.metrics} />
          </div>
        )}
      </div>
    </div>
  );
}
