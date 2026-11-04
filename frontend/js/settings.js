/**
 * Settings Controller
 */
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  const user = await AuthService.requireAuth();
  if (!user) return;

  AuthService.renderNavbarAuth(user);

  // Fill in profile fields
  document.getElementById("profile-username").value = user.username;
  document.getElementById("profile-email").value = user.email;
  document.getElementById("profile-role").textContent = user.role.toUpperCase();
  document.getElementById("profile-joined").textContent = user.created_at ? new Date(user.created_at).toLocaleDateString() : "-";

  setupPasswordChange();
  setupApiKeys();
  setupAccountDeletion();
});

function setupPasswordChange() {
  const form = document.getElementById("password-change-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const oldPass = document.getElementById("old-password").value;
    const newPass = document.getElementById("new-password").value;
    const confirmPass = document.getElementById("confirm-password").value;

    if (newPass !== confirmPass) {
      showToast("New passwords do not match.", "error");
      return;
    }

    try {
      await ApiClient.post("/auth/change-password", {
        old_password: oldPass,
        new_password: newPass,
      });
      showToast("Password updated successfully!", "success");
      form.reset();
    } catch (err) {
      showToast(err.message || "Failed to update password.", "error");
    }
  });
}

async function setupApiKeys() {
  const listEl = document.getElementById("api-keys-list");
  const createForm = document.getElementById("create-api-key-form");

  async function loadKeys() {
    try {
      const res = await ApiClient.get("/auth/api-keys");
      const keys = res.data.api_keys;

      if (!keys || keys.length === 0) {
        listEl.innerHTML = `<div style="color: var(--text-muted); font-size: 0.9rem; padding: 1rem 0;">No active API keys found. Create one below for programmatic access.</div>`;
        return;
      }

      listEl.innerHTML = keys.map((k) => `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px solid var(--border);">
          <div>
            <div style="font-weight: 600;">${escapeHtml(k.name)}</div>
            <small style="color: var(--text-muted);">Created on ${new Date(k.created_at).toLocaleDateString()}</small>
          </div>
          <button class="btn btn-outline btn-sm text-danger revoke-key-btn" data-id="${k.id}">Revoke</button>
        </div>
      `).join("");

      document.querySelectorAll(".revoke-key-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-id");
          if (!confirm("Are you sure you want to revoke this API key? Applications using it will lose access.")) return;
          try {
            await ApiClient.delete(`/auth/api-keys/${id}`);
            showToast("API key revoked.", "success");
            loadKeys();
          } catch (err) {
            showToast(err.message || "Failed to revoke key.", "error");
          }
        });
      });
    } catch (err) {
      listEl.innerHTML = `<div style="color: var(--danger);">Failed to load API keys.</div>`;
    }
  }

  await loadKeys();

  if (createForm) {
    createForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const nameInput = document.getElementById("api-key-name");
      const name = nameInput.value.trim() || "Default API Key";

      try {
        const res = await ApiClient.post("/auth/api-keys", { name });
        nameInput.value = "";
        
        // Show the generated secret key in a modal or prompt
        const rawKey = res.data.api_key;
        alert(`Your new API Key:\n\n${rawKey}\n\nMake sure to copy it now. For security reasons, it cannot be shown again.`);
        loadKeys();
      } catch (err) {
        showToast(err.message || "Failed to create API key.", "error");
      }
    });
  }
}

function setupAccountDeletion() {
  const form = document.getElementById("delete-account-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const pass = document.getElementById("delete-password").value;
    if (!confirm("WARNING: This will permanently delete your account and all associated URLs. Are you absolutely certain?")) {
      return;
    }

    try {
      await ApiClient.delete("/auth/account", { body: JSON.stringify({ password: pass }) });
      alert("Your account has been deleted.");
      ApiClient.setToken(null);
      ApiClient.setUser(null);
      window.location.href = "/index.html";
    } catch (err) {
      showToast(err.message || "Failed to delete account. Verify password.", "error");
    }
  });
}
