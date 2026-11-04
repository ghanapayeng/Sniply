/**
 * Sniply Landing Page Application Logic
 */
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  setupNavbar();
  setupShortenerForm();
});

function initTheme() {
  const savedTheme = localStorage.getItem("sniply_theme") || 
    (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme);

  const toggleBtn = document.getElementById("theme-toggle-btn");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("sniply_theme", next);
      updateThemeIcon(next);
    });
  }
}

function updateThemeIcon(theme) {
  const toggleBtn = document.getElementById("theme-toggle-btn");
  if (toggleBtn) {
    toggleBtn.innerHTML = theme === "dark" ? "☀️" : "🌙";
    toggleBtn.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} mode`);
  }
}

async function setupNavbar() {
  const user = await AuthService.checkAuth();
  AuthService.renderNavbarAuth(user);

  // If user is logged in, show alias input in advanced options
  const aliasNotice = document.getElementById("alias-auth-notice");
  const aliasInput = document.getElementById("custom-alias-input");
  if (aliasNotice && aliasInput) {
    if (user) {
      aliasNotice.style.display = "none";
      aliasInput.disabled = false;
    } else {
      aliasNotice.style.display = "block";
    }
  }
}

function setupShortenerForm() {
  const form = document.getElementById("shortener-form");
  const urlInput = document.getElementById("url-input");
  const submitBtn = document.getElementById("shorten-btn");
  const optionsToggle = document.getElementById("options-toggle");
  const optionsPanel = document.getElementById("advanced-options");
  const resultBox = document.getElementById("result-box");
  const shortLinkEl = document.getElementById("short-link");
  const copyBtn = document.getElementById("copy-btn");
  const openBtn = document.getElementById("open-btn");
  const qrImg = document.getElementById("qr-code-img");
  const downloadQrBtn = document.getElementById("download-qr-btn");
  const expiryNote = document.getElementById("expiry-note");

  if (optionsToggle && optionsPanel) {
    optionsToggle.addEventListener("click", () => {
      optionsPanel.classList.toggle("collapsed");
      const isCollapsed = optionsPanel.classList.contains("collapsed");
      optionsToggle.querySelector(".toggle-icon").textContent = isCollapsed ? "▾" : "▴";
    });
  }

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const originalUrl = urlInput.value.trim();
      if (!originalUrl) {
        showToast("Please enter a destination URL to shorten.", "error");
        urlInput.focus();
        return;
      }

      // Collect optional inputs
      const customAlias = document.getElementById("custom-alias-input")?.value.trim() || undefined;
      const expiryDays = document.getElementById("expiry-select")?.value || undefined;

      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span>Shortening...</span>`;

      try {
        const payload = {
          original_url: originalUrl,
          custom_alias: customAlias || undefined,
          expires_in_days: expiryDays ? parseInt(expiryDays) : undefined,
        };

        const res = await ApiClient.post("/urls", payload);
        const urlData = res.data;

        // Render result
        const fullShortUrl = urlData.short_url.startsWith("http")
          ? urlData.short_url
          : `${window.AppConfig.BASE_URL}${urlData.short_url}`;

        shortLinkEl.textContent = fullShortUrl;
        shortLinkEl.href = fullShortUrl;
        openBtn.href = fullShortUrl;

        // Load QR Code
        const qrEndpoint = `${window.AppConfig.API_BASE_URL}/urls/${urlData.short_code}/qr`;
        qrImg.src = qrEndpoint;
        downloadQrBtn.href = qrEndpoint;

        // Expiry note
        if (urlData.expires_at) {
          const expDate = new Date(urlData.expires_at);
          expiryNote.textContent = `Valid until: ${expDate.toLocaleDateString()} ${expDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        } else {
          expiryNote.textContent = "Permanent link (no expiration)";
        }

        resultBox.style.display = "block";
        resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
        showToast("Short link created successfully!", "success");
      } catch (err) {
        showToast(err.message || "Failed to shorten URL. Please check input.", "error");
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>Shorten URL</span>`;
      }
    });
  }

  if (copyBtn && shortLinkEl) {
    copyBtn.addEventListener("click", async () => {
      const textToCopy = shortLinkEl.textContent;
      try {
        await navigator.clipboard.writeText(textToCopy);
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = "<span>✓ Copied!</span>";
        copyBtn.classList.add("btn-primary");
        copyBtn.classList.remove("btn-outline");
        showToast("Short link copied to clipboard!", "success");
        setTimeout(() => {
          copyBtn.innerHTML = originalText;
          copyBtn.classList.remove("btn-primary");
          copyBtn.classList.add("btn-outline");
        }, 2500);
      } catch {
        showToast("Failed to copy automatically. Please copy manually.", "error");
      }
    });
  }
}

window.initTheme = initTheme;
