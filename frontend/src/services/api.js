// Centralized API Service Layer for LinkPlease Backend

const BASE_URL = ""; // Relative URL (works both on local dev with proxy and production FastAPI mount)

export async function fetchStats() {
  const res = await fetch(`${BASE_URL}/stats`);
  if (!res.ok) throw new Error("Failed to fetch statistics");
  return res.json();
}

export async function fetchHealth() {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    if (!res.ok) return { status: "unavailable" };
    return res.json();
  } catch (err) {
    return { status: "unavailable" };
  }
}

export async function fetchRules() {
  const res = await fetch(`${BASE_URL}/rules`);
  if (!res.ok) throw new Error("Failed to fetch rules");
  return res.json();
}

export async function createRule(keyword, dm_message) {
  const res = await fetch(`${BASE_URL}/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyword, dm_message }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to create rule");
  }
  return res.json();
}

export async function fetchJobs() {
  const res = await fetch(`${BASE_URL}/jobs`);
  if (!res.ok) throw new Error("Failed to fetch DM jobs");
  return res.json();
}

export async function fetchEvents() {
  const res = await fetch(`${BASE_URL}/events`);
  if (!res.ok) throw new Error("Failed to fetch webhook events");
  return res.json();
}
