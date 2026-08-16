import React, { useState } from "react";
import { Plus, Sliders, CheckCircle2, AlertCircle } from "lucide-react";
import { createRule } from "../services/api";

export default function RulesPage({ rules, refreshRules, showToast }) {
  const [showModal, setShowModal] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [dmMessage, setDmMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!keyword.trim() || !dmMessage.trim()) return;

    setLoading(true);
    try {
      const res = await createRule(keyword.trim(), dmMessage.trim());
      showToast(`Rule created successfully! Rule ID: ${res.rule_id}`, "success");
      setKeyword("");
      setDmMessage("");
      setShowModal(false);
      await refreshRules();
    } catch (err) {
      showToast(`Rule could not be created: ${err.message}`, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Keyword Automation Rules</h2>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            When a comment contains a rule keyword, LinkPlease automatically claims (rule_id, user_id) and sends the DM message.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <Plus size={16} />
          <span>Create Rule</span>
        </button>
      </div>

      {/* Rules Table */}
      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          {rules && rules.length > 0 ? (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Keyword</th>
                    <th>DM Message</th>
                    <th>Rule ID</th>
                    <th>Matching</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((r) => (
                    <tr key={r.rule_id}>
                      <td>
                        <strong style={{ color: "var(--primary)", fontSize: "15px" }}>{r.keyword}</strong>
                      </td>
                      <td style={{ maxWidth: "350px" }}>{r.dm_message}</td>
                      <td><code>{r.rule_id}</code></td>
                      <td>
                        <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Case-insensitive Substring</span>
                      </td>
                      <td>
                        <span className="badge badge-delivered">Active</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <Sliders className="empty-state-icon" />
              <h3>No rules created yet</h3>
              <p style={{ marginTop: "4px" }}>Click "+ Create Rule" to set up your first comment automation rule.</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Rule Modal */}
      {showModal && (
        <div
          style={{
            position: "fixed",
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            backdropFilter: "blur(4px)"
          }}
        >
          <div className="card" style={{ width: "100%", maxWidth: "500px", margin: "20px" }}>
            <div className="card-header">
              <span className="card-title">Create New Automation Rule</span>
              <button
                onClick={() => setShowModal(false)}
                style={{ background: "none", border: "none", fontSize: "20px", cursor: "pointer", color: "var(--text-muted)" }}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="card-body">
                <div className="form-group">
                  <label className="form-label">Keyword</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. PRICE"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    required
                  />
                  <span style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
                    Matching is case-insensitive and works anywhere in the comment text.
                  </span>
                </div>

                <div className="form-group">
                  <label className="form-label">DM Message</label>
                  <textarea
                    className="form-textarea"
                    placeholder="e.g. Here's the price list: https://example.com/pricing"
                    value={dmMessage}
                    onChange={(e) => setDmMessage(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="card-header" style={{ justifyContent: "flex-end", gap: "12px", backgroundColor: "#f8fafc" }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowModal(false)}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? "Creating..." : "Create Rule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
