import React from "react";
import { ShieldCheck, Server } from "lucide-react";

export default function Header({ healthStatus }) {
  const isOnline = healthStatus?.status === "ok";

  return (
    <header className="top-header">
      <div className="header-title-group">
        <h1>LinkPlease</h1>
        <p>Instagram Comment-to-DM Automation</p>
      </div>

      <div className="header-right">
        <div className={`badge-health ${isOnline ? "ok" : "error"}`}>
          <Server size={14} />
          <span>{isOnline ? "API Connected" : "API Unavailable"}</span>
        </div>

        <div className="badge-health" style={{ backgroundColor: "#e0e7ff", color: "#3730a3" }}>
          <ShieldCheck size={14} />
          <span>HMAC Protected</span>
        </div>
      </div>
    </header>
  );
}
