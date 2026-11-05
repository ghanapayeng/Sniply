from flask import Flask
from backend.app.routes.auth import auth_bp
from backend.app.routes.urls import urls_bp
from backend.app.routes.analytics import analytics_bp
from backend.app.routes.admin import admin_bp
from backend.app.routes.redirects import redirects_bp


def register_routes(app: Flask):
    app.register_blueprint(auth_bp)
    app.register_blueprint(urls_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(admin_bp)
    # The redirects blueprint captures /<short_code>, so register it last
    app.register_blueprint(redirects_bp)

