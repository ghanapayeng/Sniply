import os
import pytest
from backend.app import create_app
from backend.app.extensions import db as _db, get_redis
from backend.app.models.user import User
from backend.app.services.auth_service import AuthService


@pytest.fixture(scope="session")
def app():
    os.environ["FLASK_ENV"] = "testing"
    os.environ["TEST_DATABASE_URL"] = "postgresql://sniply:sniplypassword@127.0.0.1:5433/sniply_test"
    os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
    
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def db_session(app):
    with app.app_context():
        # Clear tables before each test function to guarantee isolation
        meta = _db.metadata
        for table in reversed(meta.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        
        # Flush redis test db if connected
        redis_conn = get_redis()
        if redis_conn:
            try:
                redis_conn.flushdb()
            except Exception:
                pass
                
        yield _db.session
        _db.session.rollback()


@pytest.fixture
def client(app, db_session):
    return app.test_client()


@pytest.fixture
def test_user(app, db_session):
    user, _ = AuthService.register_user(
        username="testuser",
        email="testuser@example.com",
        password="ValidPassword123!",
        role="user",
    )
    return user


@pytest.fixture
def admin_user(app, db_session):
    admin, _ = AuthService.register_user(
        username="adminuser",
        email="adminuser@example.com",
        password="AdminPassword123!",
        role="admin",
    )
    return admin


@pytest.fixture
def user_token(app, test_user):
    token, _ = AuthService.create_session(test_user)
    return token


@pytest.fixture
def admin_token(app, admin_user):
    token, _ = AuthService.create_session(admin_user)
    return token


@pytest.fixture
def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

