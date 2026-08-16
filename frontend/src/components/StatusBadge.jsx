import React from "react";

export default function StatusBadge({ status }) {
  const normalized = (status || "").toLowerCase();
  return (
    <span className={`badge badge-${normalized}`}>
      {status || "Unknown"}
    </span>
  );
}
