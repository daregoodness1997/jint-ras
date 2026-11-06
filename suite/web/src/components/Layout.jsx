import React from "react";
import { NavLink } from "react-router-dom";
import { LayoutDashboard, Play, List, BarChart3, Settings } from "lucide-react";

const ICONS = {
  dashboard: LayoutDashboard,
  test: Play,
  runs: List,
  plots: BarChart3,
  settings: Settings,
};

const ITEMS = [
  { key: "dashboard", label: "Dashboard", icon: "dashboard", to: "/" },
  { key: "test", label: "New Test", icon: "test", to: "/test" },
  { key: "runs", label: "Test Runs", icon: "runs", to: "/runs" },
  { key: "plots", label: "Plots & Outputs", icon: "plots", to: "/plots" },
  { key: "settings", label: "Settings", icon: "settings", to: "/settings" },
];

export default function Layout({ children }) {
  return (
    <React.Fragment>
      <aside className="sidebar">
        <div className="brand">RESEARCH<span style={{ color: "#38bdf8" }}>SUITE</span></div>
        <nav>
          {ITEMS.map((item) => {
            const Icon = ICONS[item.icon];
            return (
              <NavLink
                key={item.key}
                to={item.to}
                end={item.key === "dashboard"}
                className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
              >
                <Icon size={17} strokeWidth={2} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
        <div className="divider" />
        <div className="foot">Snakeboard JINT/RAS gait testbed &bull; FastAPI + React</div>
      </aside>
      <main className="main">{children}</main>
    </React.Fragment>
  );
}
