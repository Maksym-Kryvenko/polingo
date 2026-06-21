export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  `http://${window.location.hostname}:8000/api`;

// New client convention: paths carry a LEADING slash (e.g. "/session").
// API_BASE_URL has no trailing slash, so the join is exact. (This replaces the
// old App.jsx buildUrl("session") no-slash convention, which is removed in Task 4.)
export async function apiFetch(path, { method = "GET", body, headers, raw } = {}) {
  const opts = { method, headers: { ...(headers || {}) } };
  if (body instanceof FormData) {
    opts.body = body;
  } else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(`${API_BASE_URL}${path}`, opts);
  if (raw) return resp;          // caller inspects resp.ok / blob itself
  if (!resp.ok) return null;     // NON-THROWING: mirrors the old `if (r.ok) {...}` swallow
  const text = await resp.text();
  return text ? JSON.parse(text) : null;  // tolerate empty/204 bodies (DELETEs)
}
