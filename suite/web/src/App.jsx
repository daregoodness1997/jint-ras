import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import TestConfig from "./pages/TestConfig";
import RunDetail from "./pages/RunDetail";
import Runs from "./pages/Runs";
import Plots from "./pages/Plots";
import Settings from "./pages/Settings";
import { Toast } from "./components/Common";

export default function App() {
  const [toast, setToast] = React.useState(null);

  const show = (msg, type = "info") => {
    setToast({ message: msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  return (
    <BrowserRouter>
      <div className="page">
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard onNotify={show} />} />
            <Route path="/test" element={<TestConfig onNotify={show} />} />
            <Route path="/runs" element={<Runs onNotify={show} />} />
            <Route path="/runs/:runId" element={<RunDetail onNotify={show} />} />
            <Route path="/plots" element={<Plots onNotify={show} />} />
            <Route path="/settings" element={<Settings onNotify={show} />} />
          </Routes>
        </Layout>
        {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </div>
    </BrowserRouter>
  );
}
