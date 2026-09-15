const API_BASE = import.meta.env.VITE_API_BASE || "";

async function request(path, { method = "GET", body, token, form } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form).toString();
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, { method, headers, body: payload });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    const detail = data?.detail;
    const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : res.statusText;
    const err = new Error(msg || "Request failed");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const api = {
  register: (body) => request("/api/auth/register", { method: "POST", body }),
  login: (email, password) =>
    request("/api/auth/login", { method: "POST", form: { username: email, password } }),
  me: (token) => request("/api/auth/me", { token }),
  spaces: (token) => request("/api/spaces", { token }),
  space: (id, token) => request(`/api/spaces/${id}`, { token }),
  slots: (id, date, token) => request(`/api/spaces/${id}/slots?date=${date}`, { token }),
  book: (body, token) => request("/api/reservations", { method: "POST", body, token }),
  mine: (token) => request("/api/reservations/mine", { token }),
  cancel: (id, token) => request(`/api/reservations/${id}/cancel`, { method: "POST", token }),
  checkIn: (id, token) => request(`/api/reservations/${id}/check-in`, { method: "POST", token }),
  checkOut: (id, token) => request(`/api/reservations/${id}/check-out`, { method: "POST", token }),
  settings: (token) => request("/api/admin/settings", { token }),
  updateSettings: (body, token) => request("/api/admin/settings", { method: "PUT", body, token }),
  adminReservations: (date, spaceId, token) =>
    request(
      `/api/admin/reservations?date=${date}${spaceId ? `&space_id=${spaceId}` : ""}`,
      { token }
    ),
  createBlock: (body, token) => request("/api/admin/blocks", { method: "POST", body, token }),
};
