from flask import Flask, request, g
from backend.app.services.auth_service import AuthService


def register_auth_middleware(app: Flask):
    @app.before_request
    def load_authenticated_user():
        g.current_user = None
        g.session_token = None

        # 1. Check Authorization header: Bearer <token>
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header.split(" ", 1)[1].strip()
            user = AuthService.get_user_from_token(raw_token)
            if user:
                g.current_user = user
                g.session_token = raw_token
                return

        # 2. Check Cookie: sniply_session
        cookie_token = request.cookies.get(app.config.get("SESSION_COOKIE_NAME", "sniply_session"))
        if cookie_token:
            user = AuthService.get_user_from_token(cookie_token)
            if user:
                g.current_user = user
                g.session_token = cookie_token
                return

        # 3. Check X-API-Key header
        api_key = request.headers.get("X-API-Key", "").strip()
        if api_key:
            user = AuthService.get_user_from_api_key(api_key)
            if user:
                g.current_user = user
                g.session_token = None
                return

