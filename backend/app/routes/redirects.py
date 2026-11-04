from datetime import datetime, timezone
from flask import Blueprint, redirect, request, abort, jsonify, current_app
from backend.app.services.url_service import URLService
from backend.app.services.analytics_service import AnalyticsService
from backend.app.utils.validators import RESERVED_ALIASES

redirects_bp = Blueprint("redirects", __name__)


@redirects_bp.route("/<short_code>", methods=["GET"])
def handle_redirect(short_code):
    """
    Handle high-performance redirection for shortened URLs:
    1. Filter out reserved keywords and static paths.
    2. Check Redis cache first.
    3. Fallback to PostgreSQL.
    4. Validate expiration and active state.
    5. Non-blocking click tracking.
    6. Return 302/307 redirect.
    """
    code = short_code.strip()
    if not code or code.lower() in RESERVED_ALIASES:
        abort(404)

    payload, db_obj = URLService.get_url_by_code(code)
    if not payload:
        # Not found: return 404 or redirect to frontend 404 page if configured
        frontend_url = current_app.config.get("FRONTEND_URL", "")
        if frontend_url and request.headers.get("Accept", "").find("text/html") != -1:
            return redirect(f"{frontend_url}/pages/404.html", code=302)
        abort(404, description="Short URL not found.")

    # Check active status
    is_active = payload.get("is_active", True)
    if not is_active:
        return jsonify({"status": "error", "message": "This short link has been disabled."}), 403

    # Check expiration
    expires_at_str = payload.get("expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if now > expires_at:
                return jsonify({"status": "error", "message": "This short link has expired."}), 410
        except ValueError:
            pass

    # Record click event (non-blocking)
    url_id = payload.get("id")
    if url_id:
        AnalyticsService.record_click(url_id, request)

    target_url = payload.get("original_url")
    return redirect(target_url, code=302)
