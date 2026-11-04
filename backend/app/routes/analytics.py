from flask import Blueprint, request, g
from backend.app.services.analytics_service import AnalyticsService
from backend.app.models.url import URL
from backend.app.utils.responses import success_response, error_response
from backend.app.utils.decorators import login_required

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v1/analytics")


@analytics_bp.route("/overview", methods=["GET"])
@login_required
def get_overview():
    """Retrieve summary analytics for current user's dashboard."""
    data = AnalyticsService.get_overview_analytics(user_id=g.current_user.id)
    return success_response(data=data)


@analytics_bp.route("/<short_code>", methods=["GET"])
@login_required
def get_url_analytics(short_code):
    """Retrieve detailed analytics breakdown for a single URL owned by current user."""
    code = short_code.strip()
    url_obj = URL.query.filter(
        (URL.short_code == code) | (URL.custom_alias == code.lower()),
        URL.user_id == g.current_user.id,
    ).first()

    if not url_obj:
        return error_response("URL not found or unauthorized.", status_code=404)

    days = int(request.args.get("days", 30))
    data = AnalyticsService.get_url_analytics(url_id=url_obj.id, days=days)
    return success_response(data=data)


@analytics_bp.route("/<short_code>/clicks", methods=["GET"])
@login_required
def get_url_clicks(short_code):
    """Retrieve paginated raw click events stream for a URL."""
    code = short_code.strip()
    url_obj = URL.query.filter(
        (URL.short_code == code) | (URL.custom_alias == code.lower()),
        URL.user_id == g.current_user.id,
    ).first()

    if not url_obj:
        return error_response("URL not found or unauthorized.", status_code=404)

    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 20))))

    data = AnalyticsService.get_url_clicks_paginated(url_id=url_obj.id, page=page, per_page=per_page)
    return success_response(data=data)
