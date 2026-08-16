import React from "react";

export default function StatCard({ title, value, description, icon: Icon, color = "#4f46e5" }) {
  return (
    <div className="stat-card">
      <div className="stat-header">
        <span className="stat-title">{title}</span>
        <div className="stat-icon" style={{ color: color, backgroundColor: `${color}15` }}>
          <Icon size={20} />
        </div>
      </div>
      <div className="stat-value">{value !== undefined && value !== null ? value : "-"}</div>
      <div className="stat-desc">{description}</div>
    </div>
  );
}
