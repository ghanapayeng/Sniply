/**
 * Centralized Application & API Configuration
 * Supports production Render deployment and local development without code modification.
 */
const AppConfig = (() => {
  // Allow build-time or HTML window injection
  const injected = window.__SNIPLY_CONFIG__ || {};

  // Determine current host context
  const host = window.location.hostname;
  const isLocal = host === "localhost" || host === "127.0.0.1";

  // Production vs local defaults
  const defaultApiBase = isLocal
    ? "http://localhost:5000/api/v1"
    : (window.location.origin.includes("onrender.com")
        ? `${window.location.origin.replace("-web", "-api").replace("-client", "-api")}/api/v1`
        : `${window.location.origin}/api/v1`);

  const defaultShortUrlBase = isLocal
    ? "http://localhost:5000"
    : (window.location.origin.includes("onrender.com")
        ? window.location.origin.replace("-web", "-api").replace("-client", "-api")
        : window.location.origin);

  return {
    API_BASE_URL: injected.API_BASE_URL || defaultApiBase,
    BASE_URL: injected.BASE_URL || defaultShortUrlBase,
    APP_NAME: "Sniply",
    VERSION: "1.0.0",
  };
})();

// Export globally for all vanilla JS scripts
window.AppConfig = AppConfig;
