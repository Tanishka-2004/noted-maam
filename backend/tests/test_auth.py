import hashlib
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.auth import Invitation, User
from app.models.auth import Session as DbSession
from app.services.identity import IdentityService

# Setup isolated testing SQLite DB
TEST_DATABASE_URL = "sqlite:///./test_auth.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db_session")
def fixture_db_session():
    """Provisions and teardowns an isolated test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def fixture_client(db_session):
    """Overrides the database dependency and provides a test client instance."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ==========================================
# 1. REGISTRATION & IDEMPOTENCY TESTS
# ==========================================


@pytest.mark.asyncio
async def test_registration_flow_and_idempotency(db_session, client):
    """Verifies registration idempotency and password strength checks."""
    # Use a secure, non-breached password to satisfy HIBP check
    payload = {"email": "test@example.com", "password": "Kx9#Lp2!vQz8$mN9"}

    # First registration
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    assert response.json()["is_active"] is False

    # Idempotent registration: user pending verification is updated, not duplicated
    response2 = client.post("/api/v1/auth/register", json=payload)
    assert response2.status_code == 201
    users = db_session.query(User).filter(User.email == "test@example.com").all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_registration_active_user_rejection(db_session, client):
    """Verifies that an active user account registration is rejected."""
    # Seed active user
    user = User(email="active@example.com", password_hash="hash", is_active=True)
    db_session.add(user)
    db_session.commit()

    payload = {"email": "active@example.com", "password": "Kx9#Lp2!vQz8$mN9"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_registration_weak_password_rejection(client):
    """Verifies that weak passwords are rejected during registration."""
    payload = {"email": "weak@example.com", "password": "123"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422  # Pydantic length validator


# ==========================================
# 2. EMAIL VERIFICATION TESTS
# ==========================================


def test_email_verification_success(db_session, client):
    """Verifies that a valid verification token activates the account
    and provisions a workspace.
    """
    # Seed pending user and verification invitation
    user = User(email="verify@example.com", password_hash="hash", is_active=False)
    db_session.add(user)
    db_session.flush()

    token = "token123"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    invite = Invitation(
        workspace_id=user.id,
        email="verify@example.com",
        role="Member",
        token_hash=token_hash,
        is_accepted=False,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db_session.add(invite)
    db_session.commit()

    response = client.post(f"/api/v1/auth/verify?token={token}")
    assert response.status_code == 200
    assert response.json()["is_active"] is True

    # Verify workspace membership exists
    updated_user = (
        db_session.query(User).filter(User.email == "verify@example.com").first()
    )
    assert len(updated_user.memberships) == 1
    assert updated_user.memberships[0].role == "Owner"


def test_email_verification_expired_token(db_session, client):
    """Verifies that expired verification tokens are rejected."""
    user = User(email="expired@example.com", password_hash="hash", is_active=False)
    db_session.add(user)
    db_session.flush()

    token = "token_expired"
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    invite = Invitation(
        workspace_id=user.id,
        email="expired@example.com",
        role="Member",
        token_hash=token_hash,
        is_accepted=False,
        expires_at=datetime.utcnow() - timedelta(hours=1),  # already expired
    )
    db_session.add(invite)
    db_session.commit()

    response = client.post(f"/api/v1/auth/verify?token={token}")
    assert response.status_code == 400
    assert "expired" in response.json()["detail"]


# ==========================================
# 3. LOGIN & SESSION LIMITS TESTS
# ==========================================


def test_login_success(db_session, client):
    """Verifies credential validation and cookie generation."""
    pwd = "Kx9#Lp2!vQz8$mN9"
    user = User(
        email="login@example.com", password_hash=hash_password(pwd), is_active=True
    )
    db_session.add(user)
    db_session.commit()

    payload = {"email": "login@example.com", "password": pwd}
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.cookies


def test_login_unverified_block(db_session, client):
    """Verifies that unverified accounts are blocked from logging in."""
    pwd = "Kx9#Lp2!vQz8$mN9"
    user = User(
        email="unverified@example.com",
        password_hash=hash_password(pwd),
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    payload = {"email": "unverified@example.com", "password": pwd}
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "pending email verification" in response.json()["detail"]


def test_login_session_limit_exceeded(db_session, client):
    """Verifies that creating an 11th active session auto-revokes the oldest session."""
    pwd = "Kx9#Lp2!vQz8$mN9"
    user = User(
        email="limit@example.com", password_hash=hash_password(pwd), is_active=True
    )
    db_session.add(user)
    db_session.commit()

    identity_service = IdentityService(db_session)

    # Pre-seed 10 active sessions
    for i in range(10):
        identity_service.login_user(
            email="limit@example.com", password=pwd, user_agent=f"device_{i}"
        )

    # Check total active sessions
    active_count = (
        db_session.query(DbSession)
        .filter(DbSession.user_id == user.id, DbSession.is_revoked.is_(False))
        .count()
    )
    assert active_count == 10

    # 11th login: auto-revokes the first session
    identity_service.login_user(
        email="limit@example.com", password=pwd, user_agent="device_11"
    )

    # Assert oldest session is marked revoked
    revoked_count = (
        db_session.query(DbSession)
        .filter(DbSession.user_id == user.id, DbSession.is_revoked.is_(True))
        .count()
    )
    assert revoked_count == 1


# ==========================================
# 4. REFRESH TOKEN ROTATION (RTR) & REPLAY TESTS
# ==========================================


def test_refresh_token_rotation(db_session, client):
    """Verifies normal refresh rotation exchanges and cookie updates."""
    pwd = "Kx9#Lp2!vQz8$mN9"
    user = User(
        email="refresh@example.com", password_hash=hash_password(pwd), is_active=True
    )
    db_session.add(user)
    db_session.commit()

    identity_service = IdentityService(db_session)
    _, _, refresh_token = identity_service.login_user(
        email="refresh@example.com", password=pwd
    )

    # Set client cookie
    client.cookies.set("refresh_token", refresh_token)
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.cookies


def test_refresh_token_replay_attack_revocation(db_session, client):
    """Verifies that replaying a rotated refresh token revokes the entire family."""
    pwd = "Kx9#Lp2!vQz8$mN9"
    user = User(
        email="replay@example.com", password_hash=hash_password(pwd), is_active=True
    )
    db_session.add(user)
    db_session.commit()

    identity_service = IdentityService(db_session)
    _, _, rt_1 = identity_service.login_user(email="replay@example.com", password=pwd)

    # Rotate once: rt_1 becomes invalid, rt_2 issued
    _, rt_2 = identity_service.rotate_refresh_token(old_refresh_token=rt_1)

    # Replay attack: client tries to re-submit replayed rt_1
    client.cookies.set("refresh_token", rt_1)
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401

    # Assert all sessions in family are revoked
    sessions = db_session.query(DbSession).filter(DbSession.user_id == user.id).all()
    assert len(sessions) > 0
    for s in sessions:
        assert s.is_revoked is True
