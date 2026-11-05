import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, g, current_app
from sqlalchemy import func, desc, or_
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.url import URL
from backend.app.models.audit_log import AuditLog
from backend.app.services.blacklist_service import BlacklistService
from backend.app.services.url_service import URLService
from backend.app.services.security_service import SecurityService
from backend.app.utils.responses import success_response, error_response
from backend.app.utils.decorators import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


@admin_bp.route("/overview", methods=["GET"])
@admin_required
def overview():
    """System-wide summary metrics for administrator dashboard."""
    now = datetime.now(timezone.utc)
    total_users = User.query.count()
    total_urls = URL.query.count()
    total_clicks = db.session.query(func.coalesce(func.sum(URL.click_count), 0)).scalar() or 0
    active_urls = URL.query.filter(
        URL.is_active == True,
        or_(URL.expires_at == None, URL.expires_at > now),
    ).count()
    expired_urls = URL.query.filter(
        URL.expires_at != None,
        URL.expires_at <= now,
    ).count()

    return success_response(
        data={
            "total_users": total_users,
            "total_urls": total_urls,
            "total_clicks": total_clicks,
            "active_urls": active_urls,
            "expired_urls": expired_urls,
        }
    )


@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """List all registered users with pagination and search."""
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    search = request.args.get("search", "").strip().lower()

    query = User.query
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(User.username.ilike(pattern), User.email.ilike(pattern)))

    pagination = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return success_response(
        data={
            "items": [u.to_dict(include_admin_fields=True) for u in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
        }
    )


@admin_bp.route("/users/<user_id>/status", methods=["PATCH"])
@admin_required
def update_user_status(user_id):
    """Suspend or activate a user account."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return error_response("Invalid user ID.", status_code=400)

    user = User.query.get(uid)
    if not user:
        return error_response("User not found.", status_code=404)

    if user.id == g.current_user.id:
        return error_response("Cannot modify your own administrator account status.", status_code=400)

    data = request.get_json(silent=True) or {}
    is_active = data.get("is_active")
    if is_active is None:
        return error_response("is_active boolean required.", status_code=400)

    user.is_active = bool(is_active)
    db.session.commit()

    SecurityService.log_audit(
        action="admin.user_status_changed",
        user_id=g.current_user.id,
        resource_type="user",
        resource_id=str(user.id),
        details=f"Changed user {user.username} active status to {user.is_active}",
    )
    return success_response(data={"user": user.to_dict(include_admin_fields=True)}, message="User status updated.")


@admin_bp.route("/urls", methods=["GET"])
@admin_required
def list_all_urls():
    """List system-wide URLs across all users."""
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    search = request.args.get("search", "").strip()

    query = URL.query
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                URL.original_url.ilike(pattern),
                URL.short_code.ilike(pattern),
                URL.custom_alias.ilike(pattern),
                URL.title.ilike(pattern),
            )
        )

    pagination = query.order_by(desc(URL.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    base_url = current_app.config.get("BASE_URL", "")

    return success_response(
        data={
            "items": [u.to_dict(base_url=base_url) for u in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
        }
    )


@admin_bp.route("/urls/<short_code>", methods=["DELETE"])
@admin_required
def delete_url(short_code):
    """Admin delete URL."""
    code = short_code.strip().lower()
    url_obj = URL.query.filter((URL.short_code == code) | (URL.custom_alias == code)).first()
    if not url_obj:
        return error_response("URL not found.", status_code=404)

    URLService.delete_url(url_obj)
    SecurityService.log_audit(
        action="admin.url_deleted",
        user_id=g.current_user.id,
        resource_type="url",
        resource_id=str(url_obj.id),
        details=f"Admin deleted URL {short_code}",
    )
    return success_response(message="URL deleted by administrator.")


@admin_bp.route("/domains", methods=["GET"])
@admin_required
def list_blacklisted_domains():
    """List all prohibited domain names."""
    domains = BlacklistService.list_domains()
    return success_response(data={"domains": [d.to_dict() for d in domains]})


@admin_bp.route("/domains", methods=["POST"])
@admin_required
def add_blacklisted_domain():
    """Add a domain to the blacklist."""
    data = request.get_json(silent=True) or {}
    domain = data.get("domain", "").strip()
    reason = data.get("reason", "").strip() or "Safety policy violation"

    if not domain:
        return error_response("Domain is required.", status_code=400)

    entry = BlacklistService.add_domain(domain, reason=reason, user_id=g.current_user.id)
    SecurityService.log_audit(
        action="admin.blacklist_added",
        user_id=g.current_user.id,
        resource_type="domain",
        resource_id=str(entry.id),
        details=f"Blacklisted domain: {entry.domain}",
    )
    return success_response(data={"domain": entry.to_dict()}, message="Domain added to blacklist.", status_code=201)


@admin_bp.route("/domains/<path:domain>", methods=["DELETE"])
@admin_required
def remove_blacklisted_domain(domain):
    """Remove a domain from the blacklist."""
    ok = BlacklistService.remove_domain(domain)
    if not ok:
        return error_response("Domain not found in blacklist.", status_code=404)

    SecurityService.log_audit(
        action="admin.blacklist_removed",
        user_id=g.current_user.id,
        resource_type="domain",
        details=f"Removed domain {domain} from blacklist",
    )
    return success_response(message="Domain removed from blacklist.")


@admin_bp.route("/audit-logs", methods=["GET"])
@admin_required
def view_audit_logs():
    """List system audit logs."""
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 50))))

    pagination = AuditLog.query.order_by(desc(AuditLog.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return success_response(
        data={
            "items": [log.to_dict() for log in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
        }
    )

