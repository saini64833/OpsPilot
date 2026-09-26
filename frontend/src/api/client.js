const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  getOrders: () => request("/orders/"),
  getOrder: (id) => request(`/orders/${id}`),
  createOrder: (payload) =>
    request("/orders/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getRiders: () => request("/riders/"),
  createRider: (payload) =>
    request("/riders/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  breakdownRider: (id) =>
    request(`/riders/${id}/breakdown`, {
      method: "POST",
    }),

  restoreRider: (id) =>
    request(`/riders/${id}/restore`, {
      method: "POST",
    }),

  getProposals: (status) =>
    request(`/proposals/${status ? `?status=${status}` : ""}`),

  acceptProposal: (id, payload = {}) =>
    request(`/proposals/${id}/accept`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  rejectProposal: (id, payload = {}) =>
    request(`/proposals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getAuditLog: () => request("/audit-log/"),
    // Live rider -> destination road route (rider -> pickup while ASSIGNED,
    // rider -> delivery once IN_TRANSIT). Routed through the backend rather
    // than calling OSRM directly from the browser, per services/road_routing.py.
  getOrderRoute: (orderId) => request(`/routes/order/${orderId}`),

  uploadOcrImage: async (orderId, file) => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${BASE_URL}/orders/${orderId}/ocr`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${body}`);
    }

    return res.json();
  },
};

export { BASE_URL };
