from backend.app.services.cache_service import CacheService
from backend.app.services.url_service import URLService
from backend.app.extensions import get_redis


def test_cache_set_and_get():
    redis_conn = get_redis()
    if not redis_conn:
        return  # Gracefully skip if redis not connected in this test environment

    code = "cachetest123"
    data = {"id": "1", "original_url": "https://example.com/cached"}
    ok = CacheService.set_url(code, data, ttl=60)
    assert ok is True

    cached = CacheService.get_url(code)
    assert cached is not None
    assert cached["original_url"] == "https://example.com/cached"

    # Invalidate
    CacheService.invalidate(code)
    assert CacheService.get_url(code) is None


def test_cache_invalidation_on_url_lifecycle(client, user_headers):
    # 1. Create URL
    res = client.post("/api/v1/urls", headers=user_headers, json={
        "original_url": "https://example.com/cache-lifecycle",
    })
    code = res.get_json()["data"]["short_code"]

    # 2. Redirect populates/verifies cache
    client.get(f"/{code}")
    cached = CacheService.get_url(code)
    if get_redis():
        assert cached is not None

    # 3. Update URL (disable it)
    client.patch(f"/api/v1/urls/{code}", headers=user_headers, json={"is_active": False})

    # Cache should be invalidated or updated
    cached_after = CacheService.get_url(code)
    assert cached_after is None

    # 4. Subsequent redirect must reject
    res_redirect = client.get(f"/{code}")
    assert res_redirect.status_code == 403


def test_cache_graceful_fallback_when_redis_none():
    import backend.app.extensions as ext
    original_client = ext.redis_client
    try:
        # Simulate Redis outage
        ext.redis_client = None

        # Cache operations should return None/False without raising an exception
        assert CacheService.get_url("anycode") is None
        assert CacheService.set_url("anycode", {"url": "test"}, 60) is False
        assert CacheService.invalidate("anycode") is False

        # URL service get_url_by_code should still work by querying PostgreSQL directly!
        payload, model = URLService.get_url_by_code("nonexistent")
        assert payload is None and model is None
    finally:
        ext.redis_client = original_client

