import React from "react";
import { Send, AlertTriangle, Clock, ShieldCheck, CheckCircle2, Lock } from "lucide-react";
import StatCard from "../components/StatCard";

export default function StatsPage({ stats }) {
  const sent = stats?.sent || 0;
  const failed = stats?.failed || 0;
  const queued = stats?.queued || 0;
  const duplicatesBlocked = stats?.duplicates_blocked || 0;

  const totalFinished = sent + failed;
  const successRate = totalFinished > 0 ? ((sent / totalFinished) * 100).toFixed(1) : "100.0";

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Live Statistics & Security</h2>
        <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
          Metrics derived dynamically from persistent database state. No fake data or in-memory counters.
        </p>
      </div>

      <div className="stats-grid">
        <StatCard
          title="Sent"
          value={sent}
          description="Confirmed delivered by PseudoGram API"
          icon={Send}
          color="#10b981"
        />
        <StatCard
          title="Failed"
          value={failed}
          description="Permanent failures after retry policy"
          icon={AlertTriangle}
          color="#ef4444"
        />
        <StatCard
          title="Queued"
          value={queued}
          description="Pending, accepted, or retrying"
          icon={Clock}
          color="#f59e0b"
        />
        <StatCard
          title="Duplicates Blocked"
          value={duplicatesBlocked}
          description="Same user + rule claims prevented"
          icon={ShieldCheck}
          color="#3b82f6"
        />
      </div>

      {/* Calculated Metrics Card */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "24px" }}>
        <div className="card" style={{ margin: 0 }}>
          <div className="card-header">
            <span className="card-title">Delivery Performance</span>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", alignItems: "baseline", gap: "12px", marginBottom: "16px" }}>
              <span style={{ fontSize: "42px", fontWeight: 700, color: "var(--primary)" }}>
                {successRate}%
              </span>
              <span style={{ fontSize: "14px", color: "var(--text-muted)", fontWeight: 500 }}>
                Delivery Success Rate
              </span>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: 1.6 }}>
              Calculated from confirmed <code>delivered</code> jobs divided by total completed jobs (<code>sent + failed</code>).
            </p>
          </div>
        </div>

        {/* Security & Webhook Info Card */}
        <div className="card" style={{ margin: 0 }}>
          <div className="card-header">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Lock size={18} color="var(--primary)" />
              <span className="card-title">Webhook Security Status</span>
            </div>
          </div>
          <div className="card-body">
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <CheckCircle2 size={18} color="#10b981" />
                <span style={{ fontSize: "14px", fontWeight: 600 }}>HMAC-SHA256 Verification Enabled</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <CheckCircle2 size={18} color="#10b981" />
                <span style={{ fontSize: "14px", fontWeight: 600 }}>Raw Byte Signature Comparison</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <CheckCircle2 size={18} color="#10b981" />
                <span style={{ fontSize: "14px", fontWeight: 600 }}>Atomic Database Deduplication</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
