import React from "react";
import { RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useRuns } from "../hooks/useRuns";
import { RunTable } from "../components/Common";

export default function Runs({ onNotify }) {
  const navigate = useNavigate();
  const { runs, loading, refetch } = useRuns();
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Test Runs</h1>
          <p className="page-sub">All research sweep runs with live status.</p>
        </div>
        <button className="primary" onClick={refetch}>
          <RefreshCw size={16} strokeWidth={2} /> Refresh
        </button>
      </div>
      {loading ? (
        <div className="empty"><div className="skeleton" style={{ width: 600, height: 260 }} /></div>
      ) : (
        <RunTable runs={runs} onRunClick={(id) => navigate(`/runs/${id}`)} />
      )}
    </div>
  );
}
