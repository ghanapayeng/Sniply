import uuid
from flask import Blueprint, request, g, current_app, make_response
from backend.app.extensions import limiter, db
from backend.app.services.auth_service import AuthService
from backend.app.services.security_service import SecurityService
from backend.app.models.api_key import APIKey
from backend.app.utils.validators import validate_username, validate_email, validate_password, hash_token
from backend.app.utils.short_code import generate_api_key
from backend.app.utils.responses import success_response, error_response
from backend.app.utils.decorators import login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per minute; 30 per hour")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")

    # Validate inputs
    val_u, err_u = validate_username(username)
    if not val_u:
        return error_response(err_u, status_code=400, code="INVALID_USERNAME")

    val_e, err_e = validate_email(email)
    if not val_e:
        return error_response(err_e, status_code=400, code="INVALID_EMAIL")

    val_p, err_p = validate_password(password)
    if not val_p:
        return error_response(err_p, status_code=400, code="WEAK_PASSWORD")

    user, err = AuthService.register_user(username, email, password)
    if err:
        return error_response(err, status_code=409, code="REGISTRATION_CONFLICT")

    # Automatically create session upon successful registration
    token, session = AuthService.create_session(user, request)
    resp_data = {
        "user": user.to_dict(),
        "token": token,
    }
    response, status = success_response(
        data=resp_data,
        message="Registration successful.",
        status_code=201,
    )

    # Set secure HTTP-only cookie
    resp = make_response(response, status)
    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "sniply_session")
    resp.set_cookie(
        cookie_name,
        token,
        httponly=True,
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        samesite=current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
        max_age=14 * 86400,
        path="/",
    )
    return resp


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute; 50 per hour")
def login():
    data = request.get_json(silent=True) or {}
    identifier = data.get("identifier") or data.get("email") or data.get("username", "")
    password = data.get("password", "")

    if not identifier or not password:
        return error_response("Email/Username and password are required.", status_code=400, code="MISSING_CREDENTIALS")

    user, err = AuthService.authenticate_user(identifier, password)
    if err:
        return error_response(err, status_code=401, code="AUTH_FAILED")

    token, session = AuthService.create_session(user, request)
    resp_data = {
        "user": user.to_dict(),
        "token": token,
    }
    response, status = success_response(
        data=resp_data,
        message="Login successful.",
        status_code=200,
    )

    resp = make_response(response, status)
    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "sniply_session")
    resp.set_cookie(
        cookie_name,
        token,
        httponly=True,
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        samesite=current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
        max_age=14 * 86400,
        path="/",
    )
    return resp


@auth_bp.route("/logout", methods=["POST"])
def logout():
    token = getattr(g, "session_token", None)
    if token:
        AuthService.revoke_session(token)

    response, status = success_response(message="Logged out successfully.")
    resp = make_response(response, status)
    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "sniply_session")
    resp.delete_cookie(cookie_name, path="/")
    return resp


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return success_response(data={"user": g.current_user.to_dict(include_admin_fields=True)})


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        return error_response("Current password and new password are required.", status_code=400)

    val_p, err_p = validate_password(new_password)
    if not val_p:
        return error_response(err_p, status_code=400, code="WEAK_PASSWORD")

    ok, err = AuthService.change_password(g.current_user, old_password, new_password)
    if not ok:
        return error_response(err, status_code=400)

    # Issue a fresh new session
    token, session = AuthService.create_session(g.current_user, request)
    resp_data = {"token": token}
    response, status = success_response(data=resp_data, message="Password updated successfully.")
    resp = make_response(response, status)
    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "sniply_session")
    resp.set_cookie(
        cookie_name,
        token,
        httponly=True,
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        samesite=current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
        max_age=14 * 86400,
        path="/",
    )
    return resp


@auth_bp.route("/account", methods=["DELETE"])
@login_required
def delete_account():
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    if not password:
        return error_response("Password is required to confirm account deletion.", status_code=400)

    ok, err = AuthService.delete_account(g.current_user, password)
    if not ok:
        return error_response(err, status_code=400)

    response, status = success_response(message="Account permanently deleted.")
    resp = make_response(response, status)
    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "sniply_session")
    resp.delete_cookie(cookie_name, path="/")
    return resp


@auth_bp.route("/api-keys", methods=["GET"])
@login_required
def list_api_keys():
    keys = APIKey.query.filter_by(user_id=g.current_user.id).order_by(APIKey.created_at.desc()).all()
    return success_response(data={"api_keys": [k.to_dict() for k in keys]})


@auth_bp.route("/api-keys", methods=["POST"])
@login_required
def create_api_key():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "Default API Key").strip()
    raw_key = generate_api_key()
    key_h = hash_token(raw_key)

    api_key_obj = APIKey(
        user_id=g.current_user.id,
        name=name[:100],
        key_hash=key_h,
        is_active=True,
    )
    db.session.add(api_key_obj)
    db.session.commit()

    return success_response(
        data={
            "api_key": raw_key,  # Returned only once upon creation
            "id": str(api_key_obj.id),
            "name": api_key_obj.name,
            "created_at": api_key_obj.created_at.isoformat(),
        },
        message="API key created. Save this secret key now; it will not be displayed again.",
        status_code=201,
    )


@auth_bp.route("/api-keys/<key_id>", methods=["DELETE"])
@login_required
def delete_api_key(key_id):
    try:
        uid = uuid.UUID(key_id)
    except ValueError:
        return error_response("Invalid API key ID.", status_code=400)

    api_key = APIKey.query.filter_by(id=uid, user_id=g.current_user.id).first()
    if not api_key:
        return error_response("API key not found.", status_code=404)

    db.session.delete(api_key)
    db.session.commit()
    return success_response(message="API key revoked successfully.")

