/**
 * Authentication & Session Management Module
 */
const AuthService = (() => {
  async function checkAuth() {
    try {
      const res = await ApiClient.get("/auth/me");
      if (res?.data?.user) {
        ApiClient.setUser(res.data.user);
        return res.data.user;
      }
    } catch {
      ApiClient.setToken(null);
      ApiClient.setUser(null);
    }
    return null;
  }

  async function login(identifier, password, remember = false) {
    const res = await ApiClient.post("/auth/login", { identifier, password });
    if (res?.data?.token) {
      ApiClient.setToken(res.data.token, remember);
      ApiClient.setUser(res.data.user, remember);
    }
    return res.data.user;
  }

  async function register(username, email, password) {
    const res = await ApiClient.post("/auth/register", { username, email, password });
    if (res?.data?.token) {
      ApiClient.setToken(res.data.token, true);
      ApiClient.setUser(res.data.user, true);
    }
    return res.data.user;
  }

  async function logout() {
    try {
      await ApiClient.post("/auth/logout", {});
    } catch {
      // Ignore network errors on logout
    } finally {
      ApiClient.setToken(null);
      ApiClient.setUser(null);
      window.location.href = "/index.html";
    }
  }

  async function requireAuth() {
    const user = await checkAuth();
    if (!user) {
      const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/pages/login.html?returnUrl=${returnUrl}`;
      return null;
    }
    return user;
  }

  async function requireAdmin() {
    const user = await requireAuth();
    if (user && user.role !== "admin") {
      window.location.href = "/pages/dashboard.html";
      return null;
    }
    return user;
  }

  function renderNavbarAuth(user) {
    const authContainer = document.getElementById("nav-auth-container");
    if (!authContainer) return;

    if (user) {
      authContainer.innerHTML = `
        <a href="/pages/dashboard.html" class="nav-link dashboard-link">Dashboard</a>
        ${user.role === 'admin' ? '<a href="/pages/admin.html" class="nav-link admin-pill">Admin</a>' : ''}
        <div class="user-menu-dropdown">
          <button class="btn btn-outline btn-sm user-menu-btn" id="user-menu-btn">
            <span class="user-avatar-initial">${user.username.charAt(0).toUpperCase()}</span>
            <span class="username-text">${escapeHtml(user.username)}</span>
          </button>
          <div class="dropdown-menu" id="user-dropdown-menu">
            <a href="/pages/urls.html" class="dropdown-item">My Links</a>
            <a href="/pages/settings.html" class="dropdown-item">Settings</a>
            <div class="dropdown-divider"></div>
            <button class="dropdown-item text-danger" id="logout-btn">Log Out</button>
          </div>
        </div>
      `;

      const userBtn = document.getElementById("user-menu-btn");
      const dropdown = document.getElementById("user-dropdown-menu");
      if (userBtn && dropdown) {
        userBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          dropdown.classList.toggle("show");
        });
        document.addEventListener("click", () => dropdown.classList.remove("show"));
      }

      const logoutBtn = document.getElementById("logout-btn");
      if (logoutBtn) {
        logoutBtn.addEventListener("click", logout);
      }
    } else {
      authContainer.innerHTML = `
        <a href="/pages/login.html" class="btn btn-ghost">Log In</a>
        <a href="/pages/register.html" class="btn btn-primary">Sign Up</a>
      `;
    }
  }

  return {
    checkAuth,
    login,
    register,
    logout,
    requireAuth,
    requireAdmin,
    renderNavbarAuth,
  };
})();

window.AuthService = AuthService;

