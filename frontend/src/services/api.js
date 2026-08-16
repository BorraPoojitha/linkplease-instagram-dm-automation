// Centralized API Service Layer for LinkPlease Backend
// Handles Render free-tier cold starts with automatic retry

export const RENDER_BACKEND_URL = "https://linkplease-ttp8.onrender.com";
export const BASE_URL = import.meta.env.VITE_API_BASE_URL || RENDER_BACKEND_URL;

async function fetchWithRetry(url, options = {}, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(url, options);
      if (res.ok) return res;
    } catch (err) {
      if (i === retries - 1) throw err;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  return fetch(url, options);
}

export async function fetchStats() {
  const res = await fetchWithRetry(`${BASE_URL}/stats`);
  if (!res.ok) throw new Error("Failed to fetch statistics");
  return res.json();
}

export async function fetchHealth() {
  try {
    const res = await fetchWithRetry(`${BASE_URL}/health`);
    if (!res.ok) return { status: "unavailable" };
    return res.json();
  } catch (err) {
    return { status: "unavailable" };
  }
}

export async function fetchRules() {
  const res = await fetchWithRetry(`${BASE_URL}/rules`);
  if (!res.ok) throw new Error("Failed to fetch rules");
  return res.json();
}

export async function createRule(keyword, dm_message) {
  const res = await fetchWithRetry(`${BASE_URL}/rules`, {
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
  const res = await fetchWithRetry(`${BASE_URL}/jobs`);
  if (!res.ok) throw new Error("Failed to fetch DM jobs");
  return res.json();
}

export async function fetchEvents() {
  const res = await fetchWithRetry(`${BASE_URL}/events`);
  if (!res.ok) throw new Error("Failed to fetch webhook events");
  return res.json();
}
