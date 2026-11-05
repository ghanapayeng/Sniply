/**
 * Administrator Dashboard Controller
 */
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  const user = await AuthService.requireAdmin();
  if (!user) return;

  AuthService.renderNavbarAuth(user);
  setupTabs();

  await loadAdminOverview();
  await loadUsers();
  await loadGlobalUrls();
  await loadBlacklistedDomains();
  await loadAuditLogs();
});

function setupTabs() {
  document.querySelectorAll(".admin-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".admin-tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".admin-tab-content").forEach((c) => c.style.display = "none");

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const targetEl = document.getElementById(targetId);
      if (targetEl) targetEl.style.display = "block";
    });
  });
}

async function loadAdminOverview() {
  try {
    const res = await ApiClient.get("/admin/overview");
    const data = res.data;

    document.getElementById("stat-admin-users").textContent = data.total_users.toLocaleString();
    document.getElementById("stat-admin-urls").textContent = data.total_urls.toLocaleString();
    document.getElementById("stat-admin-clicks").textContent = data.total_clicks.toLocaleString();
    document.getElementById("stat-admin-active").textContent = data.active_urls.toLocaleString();
  } catch (err) {
    showToast(err.message || "Failed to load admin metrics.", "error");
  }
}

async function loadUsers() {
  const container = document.getElementById("admin-users-table-body");
  try {
    const res = await ApiClient.get("/admin/users?per_page=50");
    const users = res.data.items;

    if (!users || users.length === 0) {
      container.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No users found.</td></tr>`;
      return;
    }

    container.innerHTML = users.map((u) => {
      const createdStr = u.created_at ? new Date(u.created_at).toLocaleDateString() : "-";
      const statusBadge = u.is_active
        ? '<span class="badge badge-success">Active</span>'
        : '<span class="badge badge-danger">Suspended</span>';

      return `
        <tr>
          <td>
            <strong>${escapeHtml(u.username)}</strong>
            ${u.role === 'admin' ? '<span class="badge badge-info" style="margin-left: 6px;">ADMIN</span>' : ''}
          </td>
          <td>${escapeHtml(u.email)}</td>
          <td>${createdStr}</td>
          <td>${statusBadge}</td>
          <td>
            ${u.role !== 'admin' ? `
              <button class="btn btn-outline btn-sm toggle-user-btn" data-id="${u.id}" data-active="${u.is_active}">
                ${u.is_active ? 'Suspend' : 'Activate'}
              </button>
            ` : '<small style="color: var(--text-muted);">Protected</small>'}
          </td>
        </tr>
      `;
    }).join("");

    document.querySelectorAll(".toggle-user-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const userId = btn.getAttribute("data-id");
        const currentActive = btn.getAttribute("data-active") === "true";
        const newActive = !currentActive;

        try {
          await ApiClient.patch(`/admin/users/${userId}/status`, { is_active: newActive });
          showToast(`User status updated to ${newActive ? 'active' : 'suspended'}.`, "success");
          loadUsers();
          loadAdminOverview();
        } catch (err) {
          showToast(err.message || "Failed to update user status.", "error");
        }
      });
    });
  } catch (err) {
    container.innerHTML = `<tr><td colspan="5" style="color: var(--danger); text-align: center;">Failed to load users: ${escapeHtml(err.message)}</td></tr>`;
  }
}

async function loadGlobalUrls() {
  const container = document.getElementById("admin-urls-table-body");
  try {
    const res = await ApiClient.get("/admin/urls?per_page=50");
    const items = res.data.items;

    if (!items || items.length === 0) {
      container.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No URLs found.</td></tr>`;
      return;
    }

    container.innerHTML = items.map((u) => {
      const fullShort = u.short_url.startsWith("http") ? u.short_url : `${window.AppConfig.BASE_URL}${u.short_url}`;
      return `
        <tr>
          <td>
            <a href="${fullShort}" target="_blank" style="font-weight: 700;">${escapeHtml(u.custom_alias || u.short_code)} ↗</a>
          </td>
          <td class="url-original-cell" title="${escapeHtml(u.original_url)}">${escapeHtml(u.original_url)}</td>
          <td>${u.click_count.toLocaleString()}</td>
          <td>${u.is_anonymous ? '<span class="badge badge-info">Anonymous</span>' : 'Registered User'}</td>
          <td>
            <button class="btn btn-outline btn-sm text-danger admin-delete-url-btn" data-code="${u.short_code}">Delete</button>
          </td>
        </tr>
      `;
    }).join("");

    document.querySelectorAll(".admin-delete-url-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const code = btn.getAttribute("data-code");
        if (!confirm(`Delete short URL '${code}'?`)) return;
        try {
          await ApiClient.delete(`/admin/urls/${code}`);
          showToast("URL deleted by administrator.", "success");
          loadGlobalUrls();
          loadAdminOverview();
        } catch (err) {
          showToast(err.message || "Failed to delete URL.", "error");
        }
      });
    });
  } catch (err) {
    container.innerHTML = `<tr><td colspan="5" style="color: var(--danger); text-align: center;">Failed to load global URLs.</td></tr>`;
  }
}

async function loadBlacklistedDomains() {
  const container = document.getElementById("admin-domains-table-body");
  const form = document.getElementById("add-domain-form");

  async function refresh() {
    try {
      const res = await ApiClient.get("/admin/domains");
      const domains = res.data.domains;

      if (!domains || domains.length === 0) {
        container.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 2rem;">No domains blacklisted. All domains permitted subject to standard SSRF rules.</td></tr>`;
        return;
      }

      container.innerHTML = domains.map((d) => `
        <tr>
          <td><strong>${escapeHtml(d.domain)}</strong></td>
          <td>${escapeHtml(d.reason || "-")}</td>
          <td>${new Date(d.created_at).toLocaleDateString()}</td>
          <td>
            <button class="btn btn-outline btn-sm text-danger remove-domain-btn" data-domain="${d.domain}">Remove</button>
          </td>
        </tr>
      `).join("");

      document.querySelectorAll(".remove-domain-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const dom = btn.getAttribute("data-domain");
          if (!confirm(`Remove '${dom}' from blacklist?`)) return;
          try {
            await ApiClient.delete(`/admin/domains/${dom}`);
            showToast("Domain removed from blacklist.", "success");
            refresh();
          } catch (err) {
            showToast(err.message || "Failed to remove domain.", "error");
          }
        });
      });
    } catch (err) {
      container.innerHTML = `<tr><td colspan="4" style="color: var(--danger); text-align: center;">Failed to load domain blacklist.</td></tr>`;
    }
  }

  await refresh();

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const domInput = document.getElementById("new-domain-input");
      const reasonInput = document.getElementById("new-domain-reason");
      const domain = domInput.value.trim();
      const reason = reasonInput.value.trim();

      if (!domain) return;

      try {
        await ApiClient.post("/admin/domains", { domain, reason });
        showToast(`Domain '${domain}' added to blacklist.`, "success");
        domInput.value = "";
        reasonInput.value = "";
        refresh();
      } catch (err) {
        showToast(err.message || "Failed to add domain.", "error");
      }
    });
  }
}

async function loadAuditLogs() {
  const container = document.getElementById("admin-logs-table-body");
  try {
    const res = await ApiClient.get("/admin/audit-logs?per_page=50");
    const logs = res.data.items;

    if (!logs || logs.length === 0) {
      container.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No audit records.</td></tr>`;
      return;
    }

    container.innerHTML = logs.map((l) => `
      <tr>
        <td>${new Date(l.created_at).toLocaleString()}</td>
        <td><strong>${escapeHtml(l.action)}</strong></td>
        <td>${escapeHtml(l.username || "System/Anonymous")}</td>
        <td>${escapeHtml(l.resource_type || "-")}</td>
        <td><small style="color: var(--text-muted);">${escapeHtml(l.details || "-")}</small></td>
      </tr>
    `).join("");
  } catch (err) {
    container.innerHTML = `<tr><td colspan="5" style="color: var(--danger); text-align: center;">Failed to load audit logs.</td></tr>`;
  }
}

