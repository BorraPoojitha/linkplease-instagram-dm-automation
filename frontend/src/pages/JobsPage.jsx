import React from "react";
import { MessageSquare } from "lucide-react";
import StatusBadge from "../components/StatusBadge";

export default function JobsPage({ jobs }) {
  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 700 }}>DM Job Processing Queue</h2>
        <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
          Real-time queue tracking persistent DM jobs, atomic worker claims, sliding window rate limits, and delivery reconciliation.
        </p>
      </div>

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          {jobs && jobs.length > 0 ? (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>User ID</th>
                    <th>Comment ID</th>
                    <th>Rule ID</th>
                    <th>Status</th>
                    <th>Attempts</th>
                    <th>Remote DM ID</th>
                    <th>Idempotency Key</th>
                    <th>Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((j) => (
                    <tr key={j.id}>
                      <td><code>{j.user_id}</code></td>
                      <td><code>{j.comment_id}</code></td>
                      <td><code>{j.rule_id}</code></td>
                      <td><StatusBadge status={j.status} /></td>
                      <td><span style={{ fontWeight: 600 }}>{j.attempts}</span></td>
                      <td>{j.dm_id ? <code>{j.dm_id}</code> : <span style={{ color: "#cbd5e1" }}>-</span>}</td>
                      <td><code style={{ fontSize: "11px", color: "#64748b" }}>{j.idempotency_key}</code></td>
                      <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                        {j.updated_at ? new Date(j.updated_at).toLocaleTimeString() : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <MessageSquare className="empty-state-icon" />
              <h3>No DM jobs available yet</h3>
              <p style={{ marginTop: "4px" }}>DM jobs will appear here automatically when matching comment webhooks arrive.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
