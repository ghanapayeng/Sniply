/**
 * User Dashboard Controller
 */
let clickChartInstance = null;

document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  const user = await AuthService.requireAuth();
  if (!user) return;

  AuthService.renderNavbarAuth(user);
  setupQuickShortenForm();
  await loadDashboardData();
});

async function loadDashboardData() {
  try {
    const res = await ApiClient.get("/analytics/overview");
    const data = res.data;

    // Populate stat counters
    document.getElementById("stat-total-links").textContent = data.total_links.toLocaleString();
    document.getElementById("stat-total-clicks").textContent = data.total_clicks.toLocaleString();
    document.getElementById("stat-active-links").textContent = data.active_links.toLocaleString();
    document.getElementById("stat-expired-links").textContent = data.expired_links.toLocaleString();

    // Render 14-day Chart
    renderClicksChart(data.daily_clicks);

    // Render Recent Links
    renderRecentLinks(data.recent_links);
  } catch (err) {
    showToast(err.message || "Failed to load dashboard data.", "error");
  }
}

function renderClicksChart(dailyData) {
  const ctx = document.getElementById("clicks-trend-chart")?.getContext("2d");
  if (!ctx || !window.Chart) return;

  const labels = dailyData.map((d) => {
    const parts = d.date.split("-");
    return `${parts[1]}/${parts[2]}`;
  });
  const values = dailyData.map((d) => d.clicks);

  if (clickChartInstance) {
    clickChartInstance.destroy();
  }

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
  const textColor = isDark ? "#94a3b8" : "#64748b";

  clickChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Clicks",
          data: values,
          borderColor: "#2563eb",
          backgroundColor: isDark ? "rgba(37, 99, 235, 0.2)" : "rgba(37, 99, 235, 0.08)",
          borderWidth: 2.5,
          pointBackgroundColor: "#2563eb",
          pointRadius: 4,
          fill: true,
          tension: 0.35,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: isDark ? "#1e293b" : "#0f172a",
          padding: 10,
          cornerRadius: 6,
        },
      },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: { color: textColor },
        },
        y: {
          beginAtZero: true,
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            precision: 0,
          },
        },
      },
    },
  });
}

function renderRecentLinks(links) {
  const container = document.getElementById("recent-links-table-body");
  if (!container) return;

  if (!links || links.length === 0) {
    container.innerHTML = `
      <tr>
        <td colspan="5" class="empty-state" style="padding: 2.5rem 1rem;">
          <div class="empty-title">No links created yet</div>
          <p class="empty-desc">Shorten your first link above to start tracking clicks!</p>
        </td>
      </tr>
    `;
    return;
  }

  container.innerHTML = links.map((link) => {
    const fullShortUrl = link.short_url.startsWith("http")
      ? link.short_url
      : `${window.AppConfig.BASE_URL}${link.short_url}`;

    const dateStr = link.created_at ? new Date(link.created_at).toLocaleDateString() : "-";
    const statusBadge = link.is_expired
      ? '<span class="badge badge-danger">Expired</span>'
      : (link.is_active ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-warning">Disabled</span>');

    return `
      <tr>
        <td>
          <div style="font-weight: 600; color: var(--text-main);">${escapeHtml(link.title || link.custom_alias || link.short_code)}</div>
          <div class="url-original-cell" title="${escapeHtml(link.original_url)}">${escapeHtml(link.original_url)}</div>
        </td>
        <td>
          <a href="${fullShortUrl}" target="_blank" class="url-short-cell">
            ${escapeHtml(link.custom_alias || link.short_code)} ↗
          </a>
        </td>
        <td>
          <span style="font-weight: 700; font-size: 1rem;">${link.click_count.toLocaleString()}</span>
        </td>
        <td>${statusBadge}</td>
        <td>
          <div class="action-btn-group">
            <button class="icon-btn copy-table-btn" data-url="${fullShortUrl}" title="Copy Link">📋</button>
            <a href="/pages/analytics.html?code=${link.short_code}" class="icon-btn" title="View Analytics">📈</a>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  // Attach copy event listeners
  document.querySelectorAll(".copy-table-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const url = btn.getAttribute("data-url");
      await navigator.clipboard.writeText(url);
      btn.innerHTML = "✓";
      showToast("Link copied to clipboard!", "success");
      setTimeout(() => { btn.innerHTML = "📋"; }, 2000);
    });
  });
}

function setupQuickShortenForm() {
  const form = document.getElementById("dashboard-shorten-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const urlInput = document.getElementById("dash-url-input");
    const aliasInput = document.getElementById("dash-alias-input");
    const submitBtn = document.getElementById("dash-shorten-btn");

    const originalUrl = urlInput.value.trim();
    const customAlias = aliasInput.value.trim() || undefined;

    if (!originalUrl) return;

    submitBtn.disabled = true;
    submitBtn.innerHTML = "Shortening...";

    try {
      const res = await ApiClient.post("/urls", {
        original_url: originalUrl,
        custom_alias: customAlias,
      });

      showToast("Short link created successfully!", "success");
      urlInput.value = "";
      aliasInput.value = "";
      await loadDashboardData();
    } catch (err) {
      showToast(err.message || "Failed to create short link.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = "Shorten";
    }
  });
}

