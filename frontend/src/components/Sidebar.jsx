import React from "react";
import { LayoutDashboard, Sliders, MessageSquare, Activity, BarChart3, FileText } from "lucide-react";
import { BASE_URL } from "../services/api";

export default function Sidebar({ currentPage, setCurrentPage, healthStatus }) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "rules", label: "Rules", icon: Sliders },
    { id: "jobs", label: "DM Jobs", icon: MessageSquare },
    { id: "events", label: "Events", icon: Activity },
    { id: "stats", label: "Statistics", icon: BarChart3 },
  ];

  const handleDocsClick = () => {
    const docsUrl = BASE_URL.endsWith("/") ? `${BASE_URL}docs` : `${BASE_URL}/docs`;
    window.open(docsUrl, "_blank");
  };

  const isOnline = healthStatus?.status === "ok";

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-icon">LP</div>
        <div>
          <div className="logo-title">LinkPlease</div>
          <div className="logo-subtitle">Automation Engine</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? "active" : ""}`}
              onClick={() => setCurrentPage(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}

        <button className="nav-item" onClick={handleDocsClick}>
          <FileText size={18} />
          <span>API Docs</span>
        </button>
      </nav>

      <div className="sidebar-footer">
        <div className={`status-indicator ${isOnline ? "" : "offline"}`} />
        <span style={{ color: "#ffffff", fontWeight: 500 }}>
          {isOnline ? "System Online" : "System Offline"}
        </span>
      </div>
    </aside>
  );
}
