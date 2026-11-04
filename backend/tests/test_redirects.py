from datetime import datetime, timezone, timedelta
from backend.app.models.url import URL
from backend.app.extensions import db


def test_redirect_success(client):
    create_res = client.post("/api/v1/urls", json={
        "original_url": "https://example.com/target-redirect",
    })
    code = create_res.get_json()["data"]["short_code"]

    res = client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["Location"] == "https://example.com/target-redirect"

    # Verify click count increased
    url_obj = URL.query.filter_by(short_code=code).first()
    assert url_obj.click_count == 1


def test_redirect_via_custom_alias(client, user_headers):
    client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/special-offer",
        "custom_alias": "special-offer",
    })

    res = client.get("/special-offer", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["Location"] == "https://example.com/special-offer"


def test_redirect_disabled_url(client, user_headers):
    create_res = client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/disabled-link",
    })
    code = create_res.get_json()["data"]["short_code"]

    # Disable it
    client.patch(f"/api/v1/urls/{code}", headers=user_headers, json={"is_active": False})

    res = client.get(f"/{code}")
    assert res.status_code == 403


def test_redirect_expired_url(client, user_headers):
    create_res = client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/expired-link",
    })
    code = create_res.get_json()["data"]["short_code"]

    # Manually set expiration in the past and invalidate cache
    url_obj = URL.query.filter_by(short_code=code).first()
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    url_obj.expires_at = past_time
    db.session.commit()
    from backend.app.services.cache_service import CacheService
    CacheService.invalidate(code)

    res = client.get(f"/{code}")
    assert res.status_code == 410


def test_redirect_not_found(client):
    res = client.get("/nonexistentcode999")
    assert res.status_code == 404
