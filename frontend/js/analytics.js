/**
 * URL Analytics Controller
 */
let timelineChart = null;
let deviceChart = null;
let browserChart = null;

document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  const user = await AuthService.requireAuth();
  if (!user) return;

  AuthService.renderNavbarAuth(user);

  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  if (!code) {
    showToast("No link selected for analytics.", "error");
    window.location.href = "/pages/urls.html";
    return;
  }

  await loadAnalytics(code);
  await loadClicksStream(code, 1);
});

async function loadAnalytics(code) {
  try {
    const res = await ApiClient.get(`/analytics/${code}?days=30`);
    const data = res.data;

    // Link Metadata
    const fullShortUrl = data.url.short_url.startsWith("http")
      ? data.url.short_url
      : `${window.AppConfig.BASE_URL}${data.url.short_url}`;

    document.getElementById("analytics-title").textContent = data.url.title || data.url.custom_alias || data.url.short_code;
    document.getElementById("analytics-short-url").textContent = fullShortUrl;
    document.getElementById("analytics-short-url").href = fullShortUrl;
    document.getElementById("analytics-original-url").textContent = data.url.original_url;
    document.getElementById("analytics-original-url").href = data.url.original_url;

    // Stat Cards
    document.getElementById("stat-total-clicks").textContent = data.total_clicks.toLocaleString();
    document.getElementById("stat-unique-visitors").textContent = data.unique_visitors.toLocaleString();
    
    const clickRate = data.total_clicks > 0 ? (data.unique_visitors / data.total_clicks * 100).toFixed(1) : 0;
    document.getElementById("stat-unique-rate").textContent = `${clickRate}%`;

    // Render Charts
    renderTimelineChart(data.timeline);
    renderDeviceChart(data.devices);
    renderBrowserChart(data.browsers);

    // Render Referrers Table
    renderReferrers(data.referrers);
  } catch (err) {
    showToast(err.message || "Failed to load link analytics.", "error");
  }
}

function renderTimelineChart(timeline) {
  const ctx = document.getElementById("timeline-chart")?.getContext("2d");
  if (!ctx || !window.Chart) return;

  const labels = timeline.map((t) => {
    const parts = t.date.split("-");
    return `${parts[1]}/${parts[2]}`;
  });
  const values = timeline.map((t) => t.clicks);

  if (timelineChart) timelineChart.destroy();

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
  const textColor = isDark ? "#94a3b8" : "#64748b";

  timelineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Clicks",
          data: values,
          borderColor: "#2563eb",
          backgroundColor: isDark ? "rgba(37, 99, 235, 0.2)" : "rgba(37, 99, 235, 0.08)",
          fill: true,
          tension: 0.35,
          pointRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: gridColor }, ticks: { color: textColor } },
        y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor, precision: 0 } },
      },
    },
  });
}

function renderDeviceChart(devices) {
  const ctx = document.getElementById("device-chart")?.getContext("2d");
  if (!ctx || !window.Chart) return;

  if (deviceChart) deviceChart.destroy();

  const labels = devices.length > 0 ? devices.map((d) => d.name) : ["No data"];
  const values = devices.length > 0 ? devices.map((d) => d.count) : [1];
  const colors = ["#2563eb", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"];

  deviceChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: devices.length > 0 ? colors : ["#94a3b8"] }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 12, padding: 15 } },
      },
    },
  });
}

function renderBrowserChart(browsers) {
  const ctx = document.getElementById("browser-chart")?.getContext("2d");
  if (!ctx || !window.Chart) return;

  if (browserChart) browserChart.destroy();

  const labels = browsers.map((b) => b.name);
  const values = browsers.map((b) => b.count);

  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const gridColor = isDark ? "rgba(255, 255, 255, 0.08)" : "rgba(0, 0, 0, 0.06)";
  const textColor = isDark ? "#94a3b8" : "#64748b";

  browserChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Clicks", data: values, backgroundColor: "#3b82f6", borderRadius: 4 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: textColor } },
        y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor, precision: 0 } },
      },
    },
  });
}

function renderReferrers(referrers) {
  const container = document.getElementById("referrers-table-body");
  if (!container) return;

  if (!referrers || referrers.length === 0) {
    container.innerHTML = `<tr><td colspan="2" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No referrer traffic recorded yet.</td></tr>`;
    return;
  }

  container.innerHTML = referrers.map((r) => `
    <tr>
      <td style="font-weight: 600;">${escapeHtml(r.name)}</td>
      <td style="text-align: right; font-weight: 700;">${r.count.toLocaleString()}</td>
    </tr>
  `).join("");
}

async function loadClicksStream(code, page = 1) {
  const container = document.getElementById("click-stream-table-body");
  if (!container) return;

  try {
    const res = await ApiClient.get(`/analytics/${code}/clicks?page=${page}&per_page=10`);
    const items = res.data.items;

    if (!items || items.length === 0) {
      container.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No clicks recorded yet.</td></tr>`;
      return;
    }

    container.innerHTML = items.map((c) => {
      const dateStr = c.clicked_at ? new Date(c.clicked_at).toLocaleString() : "-";
      return `
        <tr>
          <td>${dateStr}</td>
          <td>${escapeHtml(c.referrer || "Direct")}</td>
          <td>${escapeHtml(c.browser || "Unknown")}</td>
          <td>${escapeHtml(c.operating_system || "Unknown")}</td>
          <td><span class="badge badge-info">${escapeHtml(c.device_type || "other")}</span></td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    container.innerHTML = `<tr><td colspan="5" style="color: var(--danger); text-align: center;">Failed to load click stream.</td></tr>`;
  }
}
