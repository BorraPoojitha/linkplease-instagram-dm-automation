import React from "react";
import { Send, AlertTriangle, Clock, ShieldCheck, CheckCircle, XCircle, Sliders, MessageSquare } from "lucide-react";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";

export default function DashboardPage({ stats, healthStatus, rules, jobs }) {
  const isOnline = healthStatus?.status === "ok";

  return (
    <div>
      <div className="stats-grid">
        <StatCard
          title="Sent"
          value={stats?.sent}
          description="Confirmed delivered DMs"
          icon={Send}
          color="#10b981"
        />
        <StatCard
          title="Failed"
          value={stats?.failed}
          description="Permanent failures"
          icon={AlertTriangle}
          color="#ef4444"
        />
        <StatCard
          title="Queued"
          value={stats?.queued}
          description="Pending or retrying jobs"
          icon={Clock}
          color="#f59e0b"
        />
        <StatCard
          title="Duplicates Blocked"
          value={stats?.duplicates_blocked}
          description="Duplicate DMs prevented"
          icon={ShieldCheck}
          color="#3b82f6"
        />
      </div>

      {/* System Status Banner */}
      <div className="card" style={{ padding: "20px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {isOnline ? (
              <CheckCircle size={24} color="#10b981" />
            ) : (
              <XCircle size={24} color="#ef4444" />
            )}
            <div>
              <div style={{ fontWeight: 700, fontSize: "16px" }}>
                {isOnline ? "System Operational" : "System Unavailable"}
              </div>
              <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                {isOnline
                  ? "All background workers, database claims, and rate limiters operating smoothly."
                  : "Unable to connect to the backend server. Please check python run.py status."}
              </div>
            </div>
          </div>
          <span className={`badge ${isOnline ? "badge-delivered" : "badge-failed"}`}>
            {isOnline ? "GET /health 200 OK" : "Offline"}
          </span>
        </div>
      </div>

      {/* Quick Overview Tables */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "24px" }}>
        {/* Active Rules Preview */}
        <div className="card" style={{ margin: 0 }}>
          <div className="card-header">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Sliders size={18} color="var(--primary)" />
              <span className="card-title">Active Rules</span>
            </div>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {rules?.length || 0} Total Rules
            </span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {rules && rules.length > 0 ? (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Keyword</th>
                    <th>DM Message</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.slice(0, 5).map((r) => (
                    <tr key={r.rule_id}>
                      <td><strong style={{ color: "var(--primary)" }}>{r.keyword}</strong></td>
                      <td style={{ maxWidth: "250px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {r.dm_message}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">No rules created yet.</div>
            )}
          </div>
        </div>

        {/* Recent Jobs Preview */}
        <div className="card" style={{ margin: 0 }}>
          <div className="card-header">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <MessageSquare size={18} color="var(--primary)" />
              <span className="card-title">Recent DM Jobs</span>
            </div>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {jobs?.length || 0} Jobs Logged
            </span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {jobs && jobs.length > 0 ? (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>User ID</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.slice(0, 5).map((j) => (
                    <tr key={j.id}>
                      <td><code>{j.user_id}</code></td>
                      <td><StatusBadge status={j.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">No DM jobs available.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
