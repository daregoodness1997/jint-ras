import React from "react";
import { Image, RefreshCw, Download } from "lucide-react";
import { listPlots, plotUrl, outputUrl } from "../lib/api";
import { PlotPanel } from "../components/Common";

export default function Plots({ onNotify }) {
  const [plots, setPlots] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    listPlots().then((d) => { setPlots(d.plots || []); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Plots & Outputs</h1>
          <p className="page-sub">Generated simulation and sweep visualizations.</p>
        </div>
        <button className="primary" onClick={() => { listPlots().then((d) => setPlots(d.plots || [])); onNotify("Refreshed", "info"); }}>
          <RefreshCw size={16} strokeWidth={2} /> Refresh
        </button>
      </div>

      {loading ? (
        <div className="empty"><div className="skeleton" style={{ width: 300, height: 200 }} /></div>
      ) : plots.length === 0 ? (
        <div className="empty">No plots yet. Run a sweep or simulation to generate outputs.</div>
      ) : (
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))" }}>
          {plots.map((p) => (
            <div key={p.name} className="card" style={{ display: "flex", flexDirection: "column", gap: 10, padding: 14 }}>
              <div style={{ fontSize: 12, color: "#94a3b8", fontFamily: "ui-monospace, Menlo, monospace", wordBreak: "break-all" }}>{p.name}</div>
              <PlotPanel src={plotUrl(p.name)} />
              <div style={{ display: "flex", gap: 8 }}>
                <a href={plotUrl(p.name)} target="_blank" rel="noopener noreferrer"><button className="small">Open</button></a>
                <a href={plotUrl(p.name)} download><button className="small"><Download size={14} strokeWidth={2} /> Save</button></a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
