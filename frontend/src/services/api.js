// Centralized API Service Layer for LinkPlease Backend
// Configured to point to Render backend URL by default when deployed on Vercel

export const RENDER_BACKEND_URL = "https://linkplease-ttp8.onrender.com";
export const BASE_URL = import.meta.env.VITE_API_BASE_URL || RENDER_BACKEND_URL;

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
