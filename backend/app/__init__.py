import os
import logging
from flask import Flask, jsonify, send_from_directory
from backend.app.config import config_by_name
from backend.app.extensions import db, migrate, cors, limiter, init_redis, get_redis
from backend.app.middleware.security_headers import register_security_headers
from backend.app.middleware.authentication import register_auth_middleware
from backend.app.routes import register_routes
from backend.app.utils.responses import error_response

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_name: str | None = None) -> Flask:
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development").lower()

    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

    app = Flask(
        __name__,
        static_folder=frontend_dir,
        static_url_path="",
    )
    config_cls = config_by_name.get(config_name, config_by_name["development"])
    app.config.from_object(config_cls)

    # Initialize Database & Migrations
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize CORS for frontend communication
    cors.init_app(
        app,
        resources={r"/*": {"origins": app.config.get("CORS_ALLOWED_ORIGINS", "*")}},
        supports_credentials=True,
        expose_headers=["Content-Type", "Authorization", "X-Total-Count"],
    )

    # Initialize Rate Limiter
    limiter.init_app(app)

    # Initialize Redis (with graceful fallback)
    with app.app_context():
        init_redis(app)

    # Register Middlewares
    register_security_headers(app)
    register_auth_middleware(app)

    # Serve index.html at root if static frontend is present
    @app.route("/", methods=["GET"])
    def serve_frontend_root():
        if os.path.exists(os.path.join(frontend_dir, "index.html")):
            return send_from_directory(frontend_dir, "index.html")
        return jsonify({"name": "Sniply API", "version": "1.0.0", "status": "running"})

    # Health Check Endpoint (used by Render, Docker, monitoring)
    @app.route("/health", methods=["GET"])
    @app.route("/api/v1/health", methods=["GET"])
    def health_check():
        db_status = "healthy"
        try:
            db.session.execute(db.text("SELECT 1"))
        except Exception as e:
            logger.error("Health check DB failure: %s", e)
            db_status = "unhealthy"

        redis_status = "healthy" if get_redis() is not None else "degraded"

        overall_status = "healthy" if db_status == "healthy" else "unhealthy"
        code = 200 if overall_status == "healthy" else 503

        return jsonify({
            "status": overall_status,
            "database": db_status,
            "cache": redis_status,
            "version": "1.0.0",
        }), code

    # Centralized Error Handlers
    @app.errorhandler(400)
    def bad_request_handler(e):
        return error_response(str(e.description or "Bad request"), status_code=400, code="BAD_REQUEST")

    @app.errorhandler(401)
    def unauthorized_handler(e):
        return error_response(str(e.description or "Unauthorized"), status_code=401, code="UNAUTHORIZED")

    @app.errorhandler(403)
    def forbidden_handler(e):
        return error_response(str(e.description or "Forbidden"), status_code=403, code="FORBIDDEN")

    @app.errorhandler(404)
    def not_found_handler(e):
        return error_response(str(e.description or "Resource not found"), status_code=404, code="NOT_FOUND")

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return error_response(
            "Too many requests. You have exceeded your rate limit. Please try again later.",
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
        )

    @app.errorhandler(500)
    def internal_error_handler(e):
        logger.error("Internal Server Error: %s", e)
        return error_response("An internal server error occurred.", status_code=500, code="INTERNAL_SERVER_ERROR")

    # Register all API and Redirect routes
    register_routes(app)

    return app
