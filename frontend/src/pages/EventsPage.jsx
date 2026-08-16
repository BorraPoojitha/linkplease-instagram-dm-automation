import React from "react";
import { Activity } from "lucide-react";

export default function EventsPage({ events }) {
  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Webhook Event Audit Log</h2>
        <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
          Audit log of incoming webhook events. HMAC-SHA256 verified and deduplicated by <code>event_id</code>.
        </p>
      </div>

      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          {events && events.length > 0 ? (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Event ID</th>
                    <th>Event Type</th>
                    <th>Comment ID</th>
                    <th>User ID</th>
                    <th>Comment Text</th>
                    <th>Received At</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.event_id}>
                      <td><code>{e.event_id}</code></td>
                      <td>
                        <span
                          className="badge"
                          style={{
                            backgroundColor: e.event_type === "comment.created" ? "#e0e7ff" : "#fee2e2",
                            color: e.event_type === "comment.created" ? "#3730a3" : "#991b1b"
                          }}
                        >
                          {e.event_type}
                        </span>
                      </td>
                      <td>{e.comment_id ? <code>{e.comment_id}</code> : <span style={{ color: "#cbd5e1" }}>-</span>}</td>
                      <td>{e.user_id ? <code>{e.user_id}</code> : <span style={{ color: "#cbd5e1" }}>-</span>}</td>
                      <td style={{ maxWidth: "250px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {e.comment_text || "-"}
                      </td>
                      <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                        {e.created_at ? new Date(e.created_at).toLocaleTimeString() : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <Activity className="empty-state-icon" />
              <h3>No webhook events received yet</h3>
              <p style={{ marginTop: "4px" }}>Events received via <code>POST /webhook</code> will be logged here in real-time.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
