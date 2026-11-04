from backend.app.services.blacklist_service import BlacklistService
from backend.app.utils.validators import validate_url_ssrf


def test_ssrf_blocking_local_and_private_ips():
    # Loopback
    ok, err, _ = validate_url_ssrf("http://localhost/admin")
    assert ok is False
    assert "restricted" in err.lower() or "local" in err.lower()

    ok, err, _ = validate_url_ssrf("http://127.0.0.1:8080/secret")
    assert ok is False
    assert "restricted" in err.lower()

    # Private IP
    ok, err, _ = validate_url_ssrf("http://192.168.1.1/")
    assert ok is False

    ok, err, _ = validate_url_ssrf("http://10.0.0.5/api")
    assert ok is False

    # Cloud metadata service (169.254.169.254)
    ok, err, _ = validate_url_ssrf("http://169.254.169.254/latest/meta-data/")
    assert ok is False

    # Disallowed scheme
    ok, err, _ = validate_url_ssrf("ftp://example.com/file.txt")
    assert ok is False
    assert "scheme" in err.lower()

    ok, err, _ = validate_url_ssrf("javascript:alert(1)")
    assert ok is False

    # Embedded credentials
    ok, err, _ = validate_url_ssrf("http://admin:secret@example.com")
    assert ok is False
    assert "embedded credentials" in err.lower()


def test_ssrf_rejection_at_endpoint(client):
    res = client.post("/api/v1/urls", json={
        "original_url": "http://127.0.0.1:5000/internal",
    })
    assert res.status_code == 400


def test_blacklisted_domain(client, admin_headers):
    # Add domain to blacklist via admin API
    res_add = client.post("/api/v1/admin/domains", headers=admin_headers, json={
        "domain": "malicious-phishing.com",
        "reason": "Phishing detection",
    })
    assert res_add.status_code == 201

    # Attempt to shorten URL pointing to blacklisted domain
    res_shorten = client.post("/api/v1/urls", json={
        "original_url": "https://malicious-phishing.com/login",
    })
    assert res_shorten.status_code == 400
    assert "prohibited" in res_shorten.get_json()["message"]

    # Subdomain must also be blocked
    res_sub = client.post("/api/v1/urls", json={
        "original_url": "https://sub.malicious-phishing.com/login",
    })
    assert res_sub.status_code == 400


def test_security_headers_present(client):
    res = client.get("/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in res.headers
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_admin_authorization(client, user_headers):
    # Normal user cannot access admin endpoint
    res = client.get("/api/v1/admin/overview", headers=user_headers)
    assert res.status_code == 403
    assert res.get_json()["code"] == "FORBIDDEN"
