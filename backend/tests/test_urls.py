def test_anonymous_shorten_url(client):
    res = client.post("/api/v1/urls", json={
        "original_url": "https://example.com/very/long/article?ref=123",
    })
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["short_code"] is not None
    assert data["is_anonymous"] is True
    assert data["original_url"] == "https://example.com/very/long/article?ref=123"
    assert data["expires_at"] is not None  # Anonymous links must have default expiration


def test_anonymous_custom_alias_forbidden(client):
    res = client.post("/api/v1/urls", json={
        "original_url": "https://example.com",
        "custom_alias": "mycustomlink",
    })
    assert res.status_code == 403
    assert res.get_json()["code"] == "AUTH_REQUIRED_FOR_ALIAS"


def test_authenticated_shorten_with_alias(client, user_headers):
    res = client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/products/iphone",
        "custom_alias": "my-iphone",
        "title": "iPhone Product Link",
    })
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["custom_alias"] == "my-iphone"
    assert data["title"] == "iPhone Product Link"
    assert data["is_anonymous"] is False


def test_duplicate_custom_alias(client, user_headers):
    client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/link1",
        "custom_alias": "dup-alias",
    })
    res = client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/link2",
        "custom_alias": "dup-alias",
    })
    assert res.status_code == 400
    assert "already taken" in res.get_json()["message"]


def test_reserved_alias_rejected(client, user_headers):
    res = client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com",
        "custom_alias": "admin",
    })
    assert res.status_code == 400
    assert "reserved" in res.get_json()["message"]


def test_list_urls_filtering_pagination(client, user_headers):
    # Create 3 links
    for i in range(3):
        client.post("/api/v1/urls", headers=user_headers, json={
            "original_url": f"https://example.com/page{i}",
            "title": f"Page Title {i}",
        })

    res = client.get("/api/v1/urls?page=1&per_page=2", headers=user_headers)
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["total_pages"] == 2


def test_update_url(client, user_headers):
    create_res = client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/before",
        "title": "Original Title",
    })
    code = create_res.get_json()["data"]["short_code"]

    update_res = client.patch(f"/api/v1/urls/{code}", headers=user_headers, json={
        "title": "Updated Title",
        "is_active": False,
    })
    assert update_res.status_code == 200
    updated_data = update_res.get_json()["data"]
    assert updated_data["title"] == "Updated Title"
    assert updated_data["is_active"] is False


def test_delete_url(client, user_headers):
    create_res = client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/delete-me",
    })
    code = create_res.get_json()["data"]["short_code"]

    del_res = client.delete(f"/api/v1/urls/{code}", headers=user_headers)
    assert del_res.status_code == 200

    get_res = client.get(f"/api/v1/urls/{code}", headers=user_headers)
    assert get_res.status_code == 404


def test_qr_code_generation(client):
    create_res = client.post("/api/v1/urls", json={
        "original_url": "https://example.com/qr-test",
    })
    code = create_res.get_json()["data"]["short_code"]

    qr_res = client.get(f"/api/v1/urls/{code}/qr")
    assert qr_res.status_code == 200
    assert qr_res.content_type == "image/png"
    assert len(qr_res.data) > 0
