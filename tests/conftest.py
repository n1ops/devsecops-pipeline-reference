import os

# MUST set env vars BEFORE importing app modules to pass startup checks
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-not-production")
os.environ.setdefault("DEBUG", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.rate_limit import limiter

SQLALCHEMY_TEST_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

VALID_PASSWORD = "SecurePass123!"


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    limiter.enabled = False

    def _override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    limiter.enabled = True
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def auth_header(client):
    client.post(
        "/auth/register",
        json={"username": "testuser", "password": VALID_PASSWORD},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "testuser", "password": VALID_PASSWORD},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def auth_token(client):
    """Return just the raw token string (for logout tests etc.)."""
    client.post(
        "/auth/register",
        json={"username": "tokenuser", "password": VALID_PASSWORD},
    )
    resp = client.post(
        "/auth/login",
        json={"username": "tokenuser", "password": VALID_PASSWORD},
    )
    return resp.json()["access_token"]


@pytest.fixture()
def client_with_rate_limit():
    """Client fixture with rate limiting enabled."""
    Base.metadata.create_all(bind=engine)

    def _override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    limiter.enabled = True
    # Clear any existing rate limit state
    try:
        limiter._limiter.reset()
    except Exception:
        pass
    with TestClient(app) as c:
        yield c
    limiter.enabled = False
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
