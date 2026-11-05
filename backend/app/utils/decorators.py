from functools import wraps
from flask import request, g
from backend.app.utils.responses import error_response


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "current_user", None):
            return error_response("Authentication required.", status_code=401, code="UNAUTHORIZED")
        if not g.current_user.is_active:
            return error_response("Account has been suspended.", status_code=403, code="ACCOUNT_SUSPENDED")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "current_user", None):
            return error_response("Authentication required.", status_code=401, code="UNAUTHORIZED")
        if not g.current_user.is_admin():
            return error_response("Administrator privileges required.", status_code=403, code="FORBIDDEN")
        return f(*args, **kwargs)
    return decorated_function

