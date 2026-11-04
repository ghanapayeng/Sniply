from backend.app.models.click_event import ClickEvent
from backend.app.services.auth_service import AuthService


def test_analytics_recording_and_privacy(client, user_headers):
    # Create URL
    res = client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/analytics-test",
    })
    code = res.get_json()["data"]["short_code"]
    url_id = res.get_json()["data"]["id"]

    # Trigger clicks with distinct User-Agents
    client.get(f"/{code}", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"})
    client.get(f"/{code}", headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"})

    # Check overview
    res_overview = client.get("/api/v1/analytics/overview", headers=user_headers)
    assert res_overview.status_code == 200
    ov_data = res_overview.get_json()["data"]
    assert ov_data["total_links"] == 1
    assert ov_data["total_clicks"] == 2

    # Check URL detailed analytics
    res_detail = client.get(f"/api/v1/analytics/{code}", headers=user_headers)
    assert res_detail.status_code == 200
    detail_data = res_detail.get_json()["data"]
    assert detail_data["total_clicks"] == 2

    # Verify privacy: Raw IP must never be in DB
    events = ClickEvent.query.filter_by(url_id=url_id).all()
    assert len(events) == 2
    for ev in events:
        assert ev.visitor_ip_hash is not None
        assert len(ev.visitor_ip_hash) == 64  # SHA-256 hex digest
        assert not hasattr(ev, "visitor_ip")  # Model does not have raw IP column


def test_analytics_user_isolation(client, user_headers):
    # User 1 creates URL
    res = client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/user1-secret",
    })
    code = res.get_json()["data"]["short_code"]

    # Register user 2
    user2, _ = AuthService.register_user("user2", "user2@example.com", "Password123!")
    token2, _ = AuthService.create_session(user2)
    user2_headers = {"Authorization": f"Bearer {token2}", "Content-Type": "application/json"}

    # User 2 cannot access user 1's URL analytics
    res_unauth = client.get(f"/api/v1/analytics/{code}", headers=user2_headers)
    assert res_unauth.status_code == 404
