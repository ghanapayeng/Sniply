/**
 * Sniply API Client - Centralized HTTP Fetch wrapper
 */
const ApiClient = (() => {
  const TOKEN_KEY = "sniply_auth_token";
  const USER_KEY = "sniply_user_data";

  function getToken() {
    return sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
  }

  function setToken(token, persist = false) {
    if (token) {
      sessionStorage.setItem(TOKEN_KEY, token);
      if (persist) {
        localStorage.setItem(TOKEN_KEY, token);
      }
    } else {
      sessionStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(TOKEN_KEY);
    }
  }

  function getUser() {
    const raw = sessionStorage.getItem(USER_KEY) || localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  function setUser(user, persist = false) {
    if (user) {
      const serialized = JSON.stringify(user);
      sessionStorage.setItem(USER_KEY, serialized);
      if (persist) {
        localStorage.setItem(USER_KEY, serialized);
      }
    } else {
      sessionStorage.removeItem(USER_KEY);
      localStorage.removeItem(USER_KEY);
    }
  }

  async function request(endpoint, options = {}) {
    const baseUrl = window.AppConfig.API_BASE_URL.replace(/\/$/, "");
    const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    const url = `${baseUrl}${cleanEndpoint}`;

    const headers = {
      "Content-Type": "application/json",
      "Accept": "application/json",
      ...(options.headers || {}),
    };

    const token = getToken();
    if (token && !headers["Authorization"]) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers,
      credentials: "include", // Send HTTP-only cookies
    };

    try {
      const response = await fetch(url, config);
      let data = null;
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      } else {
        const text = await response.text();
        data = { message: text };
      }

      if (!response.ok) {
        const errorMsg = data?.message || `Request failed with status ${response.status}`;
        const error = new Error(errorMsg);
        error.status = response.status;
        error.code = data?.code || "ERROR";
        error.errors = data?.errors;
        throw error;
      }

      return data;
    } catch (err) {
      if (err.name === "TypeError" && err.message.includes("fetch")) {
        const netErr = new Error("Unable to connect to Sniply server. Please check your network or server status.");
        netErr.status = 0;
        throw netErr;
      }
      throw err;
    }
  }

  return {
    get: (endpoint, options = {}) => request(endpoint, { ...options, method: "GET" }),
    post: (endpoint, body, options = {}) => request(endpoint, { ...options, method: "POST", body: JSON.stringify(body) }),
    patch: (endpoint, body, options = {}) => request(endpoint, { ...options, method: "PATCH", body: JSON.stringify(body) }),
    delete: (endpoint, options = {}) => request(endpoint, { ...options, method: "DELETE" }),
    getToken,
    setToken,
    getUser,
    setUser,
  };
})();

/**
 * Global Toast Notification Utility
 */
function showToast(message, type = "info", duration = 4000) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === "success" ? "✓" : (type === "error" ? "✕" : "ℹ")}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("fade-out");
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

window.ApiClient = ApiClient;
window.showToast = showToast;
window.escapeHtml = escapeHtml;
