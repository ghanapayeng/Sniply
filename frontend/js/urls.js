/**
 * URL Management Controller
 */
let currentPage = 1;
let currentSearch = "";
let currentStatus = "";
let currentSort = "created_at";
let currentOrder = "desc";
let activeEditCode = null;
let activeDeleteCode = null;

document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  const user = await AuthService.requireAuth();
  if (!user) return;

  AuthService.renderNavbarAuth(user);
  setupFiltersAndSearch();
  setupModals();
  await loadUrls();
});

async function loadUrls() {
  const tableBody = document.getElementById("urls-table-body");
  tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 3rem; color: var(--text-muted);">Loading your links...</td></tr>`;

  try {
    const params = new URLSearchParams({
      page: currentPage,
      per_page: 15,
      sort_by: currentSort,
      sort_order: currentOrder,
    });
    if (currentSearch) params.set("search", currentSearch);
    if (currentStatus) params.set("status", currentStatus);

    const res = await ApiClient.get(`/urls?${params.toString()}`);
    const data = res.data;

    renderTable(data.items);
    renderPagination(data);
  } catch (err) {
    tableBody.innerHTML = `<tr><td colspan="7" class="empty-state"><div class="empty-title">Error loading links</div><p class="empty-desc">${escapeHtml(err.message)}</p></td></tr>`;
    showToast(err.message || "Failed to load links.", "error");
  }
}

function renderTable(items) {
  const tableBody = document.getElementById("urls-table-body");
  if (!items || items.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="7" class="empty-state">
          <div class="empty-icon">🔗</div>
          <div class="empty-title">No links found</div>
          <p class="empty-desc">Try clearing your search filters or shorten a new URL.</p>
        </td>
      </tr>
    `;
    return;
  }

  tableBody.innerHTML = items.map((link) => {
    const fullShortUrl = link.short_url.startsWith("http")
      ? link.short_url
      : `${window.AppConfig.BASE_URL}${link.short_url}`;

    const createdStr = link.created_at ? new Date(link.created_at).toLocaleDateString() : "-";
    const expiresStr = link.expires_at ? new Date(link.expires_at).toLocaleDateString() : "Never";

    let statusBadge = '<span class="badge badge-success">Active</span>';
    if (link.is_expired) {
      statusBadge = '<span class="badge badge-danger">Expired</span>';
    } else if (!link.is_active) {
      statusBadge = '<span class="badge badge-warning">Disabled</span>';
    }

    return `
      <tr data-code="${link.short_code}">
        <td>
          <div style="font-weight: 700; color: var(--text-main); margin-bottom: 2px;">
            ${escapeHtml(link.title || link.custom_alias || link.short_code)}
          </div>
          <div class="url-original-cell" title="${escapeHtml(link.original_url)}">
            ${escapeHtml(link.original_url)}
          </div>
        </td>
        <td>
          <a href="${fullShortUrl}" target="_blank" class="url-short-cell">
            ${escapeHtml(link.custom_alias || link.short_code)} ↗
          </a>
        </td>
        <td><span style="font-weight: 700;">${link.click_count.toLocaleString()}</span></td>
        <td>${createdStr}</td>
        <td><small style="color: var(--text-muted);">${expiresStr}</small></td>
        <td>${statusBadge}</td>
        <td>
          <div class="action-btn-group">
            <button class="icon-btn copy-btn" data-url="${fullShortUrl}" title="Copy Link">📋</button>
            <button class="icon-btn qr-btn" data-code="${link.short_code}" title="QR Code">📱</button>
            <a href="/pages/analytics.html?code=${link.short_code}" class="icon-btn" title="Analytics">📈</a>
            <button class="icon-btn edit-btn" data-code="${link.short_code}" title="Edit Link">✏️</button>
            <button class="icon-btn danger delete-btn" data-code="${link.short_code}" title="Delete Link">🗑️</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  attachTableEventListeners();
}

function attachTableEventListeners() {
  document.querySelectorAll(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const url = btn.getAttribute("data-url");
      await navigator.clipboard.writeText(url);
      btn.innerHTML = "✓";
      showToast("Link copied to clipboard!", "success");
      setTimeout(() => { btn.innerHTML = "📋"; }, 2000);
    });
  });

  document.querySelectorAll(".qr-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const code = btn.getAttribute("data-code");
      openQrModal(code);
    });
  });

  document.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const code = btn.getAttribute("data-code");
      openEditModal(code);
    });
  });

  document.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const code = btn.getAttribute("data-code");
      openDeleteModal(code);
    });
  });
}

function renderPagination(data) {
  const container = document.getElementById("pagination-container");
  if (!container) return;

  const { page, total, total_pages, has_prev, has_next } = data;
  document.getElementById("pagination-info").textContent = `Showing page ${page} of ${total_pages || 1} (${total} total links)`;

  const prevBtn = document.getElementById("prev-page-btn");
  const nextBtn = document.getElementById("next-page-btn");

  prevBtn.disabled = !has_prev;
  nextBtn.disabled = !has_next;

  prevBtn.onclick = () => {
    if (currentPage > 1) {
      currentPage--;
      loadUrls();
    }
  };
  nextBtn.onclick = () => {
    if (has_next) {
      currentPage++;
      loadUrls();
    }
  };
}

function setupFiltersAndSearch() {
  const searchInput = document.getElementById("search-input");
  const statusFilter = document.getElementById("status-filter");
  const sortSelect = document.getElementById("sort-select");

  let debounceTimer;
  searchInput.addEventListener("input", (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentSearch = e.target.value.trim();
      currentPage = 1;
      loadUrls();
    }, 350);
  });

  statusFilter.addEventListener("change", (e) => {
    currentStatus = e.target.value;
    currentPage = 1;
    loadUrls();
  });

  sortSelect.addEventListener("change", (e) => {
    const val = e.target.value;
    if (val === "clicks") {
      currentSort = "click_count";
      currentOrder = "desc";
    } else if (val === "oldest") {
      currentSort = "created_at";
      currentOrder = "asc";
    } else {
      currentSort = "created_at";
      currentOrder = "desc";
    }
    currentPage = 1;
    loadUrls();
  });
}

/* Modals Logic */
function setupModals() {
  // Edit form submit
  const editForm = document.getElementById("edit-url-form");
  if (editForm) {
    editForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!activeEditCode) return;

      const title = document.getElementById("edit-title").value.trim();
      const alias = document.getElementById("edit-alias").value.trim() || null;
      const isActive = document.getElementById("edit-active").checked;

      try {
        await ApiClient.patch(`/urls/${activeEditCode}`, {
          title,
          custom_alias: alias,
          is_active: isActive,
        });
        showToast("Link updated successfully!", "success");
        closeModal("edit-modal");
        loadUrls();
      } catch (err) {
        showToast(err.message || "Failed to update link.", "error");
      }
    });
  }

  // Delete confirm button
  const confirmDeleteBtn = document.getElementById("confirm-delete-btn");
  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener("click", async () => {
      if (!activeDeleteCode) return;
      try {
        await ApiClient.delete(`/urls/${activeDeleteCode}`);
        showToast("Link deleted successfully.", "success");
        closeModal("delete-modal");
        loadUrls();
      } catch (err) {
        showToast(err.message || "Failed to delete link.", "error");
      }
    });
  }

  // Close modals on backdrop or X
  document.querySelectorAll(".modal-close-btn, .modal-cancel-btn").forEach((el) => {
    el.addEventListener("click", () => {
      document.querySelectorAll(".modal-overlay").forEach((m) => m.classList.remove("active"));
    });
  });
}

async function openEditModal(code) {
  activeEditCode = code;
  try {
    const res = await ApiClient.get(`/urls/${code}`);
    const item = res.data;

    document.getElementById("edit-title").value = item.title || "";
    document.getElementById("edit-alias").value = item.custom_alias || "";
    document.getElementById("edit-active").checked = item.is_active;
    document.getElementById("edit-modal").classList.add("active");
  } catch (err) {
    showToast(err.message || "Failed to load link details.", "error");
  }
}

function openQrModal(code) {
  const qrEndpoint = `${window.AppConfig.API_BASE_URL}/urls/${code}/qr`;
  document.getElementById("modal-qr-img").src = qrEndpoint;
  document.getElementById("modal-qr-download").href = qrEndpoint;
  document.getElementById("qr-modal").classList.add("active");
}

function openDeleteModal(code) {
  activeDeleteCode = code;
  document.getElementById("delete-modal").classList.add("active");
}

function closeModal(modalId) {
  document.getElementById(modalId)?.classList.remove("active");
}
