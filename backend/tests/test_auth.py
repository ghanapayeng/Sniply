def test_register_success(client):
    res = client.post("/api/v1/auth/register", json={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "Password123!",
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert "token" in data["data"]
    assert data["data"]["user"]["username"] == "newuser"


def test_register_invalid_inputs(client):
    # Weak password
    res = client.post("/api/v1/auth/register", json={
        "username": "weakpw",
        "email": "weak@example.com",
        "password": "123",
    })
    assert res.status_code == 400
    assert res.get_json()["code"] == "WEAK_PASSWORD"

    # Invalid email
    res2 = client.post("/api/v1/auth/register", json={
        "username": "bademail",
        "email": "not-an-email",
        "password": "Password123!",
    })
    assert res2.status_code == 400


def test_register_duplicate(client, test_user):
    res = client.post("/api/v1/auth/register", json={
        "username": "testuser",
        "email": "another@example.com",
        "password": "Password123!",
    })
    assert res.status_code == 409


def test_login_success(client, test_user):
    res = client.post("/api/v1/auth/login", json={
        "identifier": "testuser",
        "password": "ValidPassword123!",
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert "token" in data["data"]


def test_login_invalid_password(client, test_user):
    res = client.post("/api/v1/auth/login", json={
        "identifier": "testuser",
        "password": "WrongPassword999!",
    })
    assert res.status_code == 401


def test_me_authenticated(client, user_headers):
    res = client.get("/api/v1/auth/me", headers=user_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["data"]["user"]["username"] == "testuser"


def test_me_unauthorized(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_logout(client, user_headers):
    res = client.post("/api/v1/auth/logout", headers=user_headers)
    assert res.status_code == 200

    # Old token should now be revoked
    res2 = client.get("/api/v1/auth/me", headers=user_headers)
    assert res2.status_code == 401


def test_change_password(client, user_headers):
    res = client.post("/api/v1/auth/change-password", headers=user_headers, json={
        "old_password": "ValidPassword123!",
        "new_password": "NewStrongPass456!",
    })
    assert res.status_code == 200

    # Try logging in with old password
    res_old = client.post("/api/v1/auth/login", json={
        "identifier": "testuser",
        "password": "ValidPassword123!",
    })
    assert res_old.status_code == 401

    # Try logging in with new password
    res_new = client.post("/api/v1/auth/login", json={
        "identifier": "testuser",
        "password": "NewStrongPass456!",
    })
    assert res_new.status_code == 200


def test_api_key_flow(client, user_headers):
    # Create key
    res = client.post("/api/v1/auth/api-keys", headers=user_headers, json={"name": "Dev Key"})
    assert res.status_code == 201
    key_data = res.get_json()["data"]
    raw_api_key = key_data["api_key"]
    key_id = key_data["id"]

    # Use API Key to access /api/v1/auth/me
    res_auth = client.get("/api/v1/auth/me", headers={"X-API-Key": raw_api_key})
    assert res_auth.status_code == 200
    assert res_auth.get_json()["data"]["user"]["username"] == "testuser"

    # Revoke key
    res_del = client.delete(f"/api/v1/auth/api-keys/{key_id}", headers=user_headers)
    assert res_del.status_code == 200

    # Access with revoked key fails
    res_revoked = client.get("/api/v1/auth/me", headers={"X-API-Key": raw_api_key})
    assert res_revoked.status_code == 401
