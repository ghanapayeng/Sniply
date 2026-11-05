import io
from datetime import datetime, timezone
from flask import Blueprint, request, g, current_app, send_file
import qrcode
from backend.app.extensions import limiter
from backend.app.services.url_service import URLService, get_effective_base_url
from backend.app.models.url import URL
from backend.app.utils.responses import success_response, error_response
from backend.app.utils.decorators import login_required

urls_bp = Blueprint("urls", __name__, url_prefix="/api/v1/urls")


@urls_bp.route("", methods=["POST"])
@limiter.limit("20 per minute; 100 per hour")
def create_url():
    """Create a shortened URL (supports anonymous visitors and authenticated users)."""
    data = request.get_json(silent=True) or {}
    original_url = data.get("original_url") or data.get("url", "")
    custom_alias = data.get("custom_alias")
    title = data.get("title")
    expires_in_days = data.get("expires_in_days")
    expires_at_str = data.get("expires_at")

    if not original_url:
        return error_response("original_url is required.", status_code=400, code="MISSING_URL")

    # Anonymous user restrictions: custom aliases are only for registered users
    user = getattr(g, "current_user", None)
    if not user and custom_alias:
        return error_response(
            "Custom aliases are available for registered users only. Please sign in or register.",
            status_code=403,
            code="AUTH_REQUIRED_FOR_ALIAS",
        )

    # Parse expiration date if provided
    parsed_expires_at = None
    if expires_at_str:
        try:
            parsed_expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        except ValueError:
            return error_response("Invalid expires_at format. Use ISO 8601 (e.g. 2026-12-31T23:59:59Z).", status_code=400)

    # Convert days
    parsed_days = None
    if expires_in_days is not None:
        try:
            parsed_days = int(expires_in_days)
            if parsed_days <= 0:
                return error_response("expires_in_days must be a positive integer.", status_code=400)
        except (ValueError, TypeError):
            return error_response("expires_in_days must be a valid integer.", status_code=400)

    url_obj, err = URLService.create_url(
        original_url=original_url,
        user=user,
        custom_alias=custom_alias,
        title=title,
        expires_in_days=parsed_days,
        expires_at=parsed_expires_at,
    )
    if err:
        return error_response(err, status_code=400, code="URL_CREATION_FAILED")

    base_url = get_effective_base_url()
    return success_response(
        data=url_obj.to_dict(base_url=base_url),
        message="Short URL created successfully.",
        status_code=201,
    )


@urls_bp.route("", methods=["GET"])
@login_required
def list_urls():
    """List authenticated user's shortened URLs with pagination, search, and filtering."""
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except ValueError:
        return error_response("Invalid pagination parameters.", status_code=400)

    search = request.args.get("search")
    status_filter = request.args.get("status")  # 'active', 'inactive', 'expired'
    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")

    if sort_by not in ("created_at", "click_count", "title", "expires_at"):
        sort_by = "created_at"

    result = URLService.list_user_urls(
        user_id=g.current_user.id,
        page=page,
        per_page=per_page,
        search=search,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return success_response(data=result)


@urls_bp.route("/<short_code>/qr", methods=["GET"])
def get_qr_code(short_code):
    """Generate high-resolution QR code PNG for a shortened URL."""
    code = short_code.strip()
    url_obj = URL.query.filter((URL.short_code == code) | (URL.custom_alias == code.lower())).first()
    if not url_obj:
        return error_response("URL not found.", status_code=404)

    base_url = get_effective_base_url().rstrip("/")
    target_link = f"{base_url}/{url_obj.custom_alias or url_obj.short_code}"

    # Generate QR Code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(target_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e293b", back_color="#ffffff")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=False)


@urls_bp.route("/<short_code>", methods=["GET"])
@login_required
def get_url(short_code):
    """Retrieve details for a specific URL owned by the authenticated user."""
    code = short_code.strip()
    url_obj = URL.query.filter(
        (URL.short_code == code) | (URL.custom_alias == code.lower()),
        URL.user_id == g.current_user.id,
    ).first()

    if not url_obj:
        return error_response("URL not found or unauthorized.", status_code=404)

    base_url = get_effective_base_url()
    return success_response(data=url_obj.to_dict(base_url=base_url))


@urls_bp.route("/<short_code>", methods=["PATCH"])
@login_required
def update_url(short_code):
    """Update title, custom_alias, is_active, or expiration of a URL."""
    code = short_code.strip()
    url_obj = URL.query.filter(
        (URL.short_code == code) | (URL.custom_alias == code.lower()),
        URL.user_id == g.current_user.id,
    ).first()

    if not url_obj:
        return error_response("URL not found or unauthorized.", status_code=404)

    data = request.get_json(silent=True) or {}
    title = data.get("title")
    custom_alias = data.get("custom_alias")
    is_active = data.get("is_active")
    expires_at_str = data.get("expires_at")

    parsed_expires_at = None
    if expires_at_str is not None:
        if expires_at_str == "" or expires_at_str is False:
            parsed_expires_at = None
        else:
            try:
                parsed_expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            except ValueError:
                return error_response("Invalid expires_at format.", status_code=400)

    ok, err = URLService.update_url(
        url_obj=url_obj,
        title=title,
        custom_alias=custom_alias,
        is_active=is_active,
        expires_at=parsed_expires_at,
    )
    if not ok:
        return error_response(err, status_code=400)

    base_url = get_effective_base_url()
    return success_response(
        data=url_obj.to_dict(base_url=base_url),
        message="URL updated successfully.",
    )


@urls_bp.route("/<short_code>", methods=["DELETE"])
@login_required
def delete_url(short_code):
    """Delete a shortened URL."""
    code = short_code.strip()
    url_obj = URL.query.filter(
        (URL.short_code == code) | (URL.custom_alias == code.lower()),
        URL.user_id == g.current_user.id,
    ).first()

    if not url_obj:
        return error_response("URL not found or unauthorized.", status_code=404)

    URLService.delete_url(url_obj)
    return success_response(message="URL deleted successfully.")
