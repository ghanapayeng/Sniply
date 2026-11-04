from flask import Flask, Response, request


def register_security_headers(app: Flask):
    @app.after_request
    def set_security_headers(response: Response) -> Response:
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy: send origin only when cross-origin, full URL when same-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict dangerous browser features
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # Modern Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self' *",
            "frame-ancestors 'none'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Enforce HTTPS HSTS when in production or HTTPS request
        if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response
