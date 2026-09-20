import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.iam import current_workspace_id, get_user_permissions
from app.core.identity_providers import google_oauth_provider
from app.core.jwks import jwks_manager
from app.main import app
from app.models import Meeting, Membership, User, Workspace

# Setup isolated testing SQLite DB
TEST_DATABASE_URL = "sqlite:///./test_iam.db"
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
# 1. EXTERNAL OAUTH IDENTITY PROVIDER TESTS
# ==========================================


def test_oauth_google_redirect(client):
    """Verifies that Google OAuth endpoint sets secure state cookies and redirects."""
    response = client.get("/api/v1/auth/oauth/google", follow_redirects=False)
    assert response.status_code == 307  # Temporary Redirect
    assert "accounts.google.com" in response.headers["location"]
    assert "oauth_state" in response.cookies


@pytest.mark.asyncio
async def test_oauth_google_callback_invalid_state(client):
    """Verifies callback rejects invalid or missing oauth state cookies."""
    response = client.get("/api/v1/auth/oauth/google/callback?code=abc&state=wrong")
    assert response.status_code == 400
    assert "state parameter mismatch" in response.json()["detail"]


@pytest.mark.asyncio
async def test_oauth_google_callback_new_user_provisioning(db_session, client):
    """Verifies dynamic OAuth provisioning and default workspace setup."""
    profile_mock = {
        "oauth_id": "google_sub_12345",
        "email": "new_oauth_user@example.com",
        "picture": "https://example.com/pic.jpg",
        "name": "OAuth User",
    }

    # Mock external identity profile exchange
    with patch.object(
        google_oauth_provider,
        "exchange_code_for_profile",
        new_callable=AsyncMock,
        return_value=profile_mock,
    ) as mock_exchange:
        # Set matching state cookie to pass CSRF validation
        state = "state_nonce_123"
        client.cookies.set("oauth_state", state)

        response = client.get(
            f"/api/v1/auth/oauth/google/callback?code=mock_code&state={state}",
            follow_redirects=False
        )

        assert response.status_code == 307
        assert response.headers["location"] == "http://localhost:3000/oauth/callback"
        mock_exchange.assert_called_once_with("mock_code")

        # Verify refresh token cookie was set on redirect
        assert "refresh_token" in response.cookies

        # Verify database record exists
        user = (
            db_session.query(User)
            .filter(User.email == "new_oauth_user@example.com")
            .first()
        )
        assert user is not None
        assert user.oauth_provider == "google"
        assert user.oauth_id == "google_sub_12345"
        assert user.is_active is True

        # Verify default workspace and owner membership was created
        assert len(user.memberships) == 1
        assert user.memberships[0].role == "Owner"


@pytest.mark.asyncio
async def test_oauth_google_callback_account_linking(db_session, client):
    """Verifies account linking when an active password account logs in via OAuth."""
    # Seed active password user
    user = User(email="link_me@example.com", password_hash="hash", is_active=True)
    db_session.add(user)
    db_session.commit()

    profile_mock = {
        "oauth_id": "google_sub_linked",
        "email": "link_me@example.com",
        "picture": "https://example.com/pic.jpg",
        "name": "Linked User",
    }

    with patch.object(
        google_oauth_provider,
        "exchange_code_for_profile",
        new_callable=AsyncMock,
        return_value=profile_mock,
    ):
        state = "state_nonce_link"
        client.cookies.set("oauth_state", state)

        response = client.get(
            f"/api/v1/auth/oauth/google/callback?code=mock_code&state={state}",
            follow_redirects=False
        )

        assert response.status_code == 307
        assert response.headers["location"] == "http://localhost:3000/oauth/callback"
        assert "refresh_token" in response.cookies

        # Verify user is linked in database
        db_session.refresh(user)
        assert user.oauth_provider == "google"
        assert user.oauth_id == "google_sub_linked"


# ==========================================
# 2. ROLE-BASED ACCESS CONTROL (RBAC) TESTS
# ==========================================


def test_rbac_user_permissions(db_session):
    """Verifies scope resolutions mapped to Owner, Admin, and Member roles."""
    user = User(email="rbac@example.com", is_active=True)
    workspace = Workspace(name="RBAC Workspace")
    db_session.add_all([user, workspace])
    db_session.flush()

    # 1. Test Owner permissions
    owner_membership = Membership(
        user_id=user.id, workspace_id=workspace.id, role="Owner"
    )
    db_session.add(owner_membership)
    db_session.commit()

    owner_perms = get_user_permissions(db_session, user.id, workspace.id)
    assert "workspace.delete" in owner_perms
    assert "meeting.write" in owner_perms
    assert "meeting.delete" in owner_perms

    # 2. Test Member permissions (restricted workspace delete)
    owner_membership.role = "Member"
    db_session.commit()

    # Invalidate Redis permissions cache to refresh database lookup
    from app.core.iam import invalidate_user_permissions

    invalidate_user_permissions(user.id, workspace.id)

    member_perms = get_user_permissions(db_session, user.id, workspace.id)
    assert "workspace.delete" not in member_perms
    assert "meeting.write" in member_perms
    assert "meeting.read" in member_perms


# ==========================================
# 3. ROW-LEVEL SECURITY (RLS) POLICY TESTS
# ==========================================


def test_rls_cross_workspace_write_protection(db_session):
    """Verifies that RLS hook blocks database writes with wrong tenant IDs."""
    ws_active = Workspace(name="Active Org")
    ws_victim = Workspace(name="Victim Org")
    db_session.add_all([ws_active, ws_victim])
    db_session.flush()

    # Set active request workspace context
    token = current_workspace_id.set(ws_active.id)
    try:
        # Attempt to insert a Meeting belonging to ws_victim workspace
        meeting = Meeting(
            workspace_id=ws_victim.id, title="Malicious Meeting Injection"
        )
        db_session.add(meeting)

        # Verify SQLAlchemy before_flush intercepts and raises PermissionError
        with pytest.raises(PermissionError) as exc_info:
            db_session.flush()
        assert "Cross-workspace query or modification denied" in str(exc_info.value)
    finally:
        current_workspace_id.reset(token)


# ==========================================
# 4. END-TO-END MIDDLEWARE INTEGRATION TESTS
# ==========================================


def test_middleware_meeting_creation_isolation(db_session, client):
    """Verifies full E2E path: resolves JWT, sets RLS context,
    and rejects cross-workspace reads.
    """
    user = User(email="tenant@example.com", is_active=True)
    ws_1 = Workspace(name="Tenant Workspace 1")
    ws_2 = Workspace(name="Tenant Workspace 2")
    db_session.add_all([user, ws_1, ws_2])
    db_session.flush()

    # Create membership in ws_1
    membership = Membership(user_id=user.id, workspace_id=ws_1.id, role="Member")
    db_session.add(membership)
    db_session.commit()

    # Generate a validated access token bound to ws_1 workspace context
    access_token_payload = {
        "iss": "auth.notedmaam.ai",
        "sub": str(user.id),
        "aud": "api.notedmaam.ai",
        "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
        "nbf": int(datetime.now(UTC).timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "jti": uuid.uuid4().hex,
        "workspace_id": str(ws_1.id),
    }
    active_key = jwks_manager.get_active_key()
    access_token = active_key.sign_token(access_token_payload)

    # 1. Authorize start_meeting POST request
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post(
        "/api/v1/meeting/start", json={"title": "Sync Scrum"}, headers=headers
    )
    assert response.status_code == 201
    assert "id" in response.json()

    # 2. Add a meeting inside ws_2 (not owned by tenant)
    meeting_2 = Meeting(workspace_id=ws_2.id, title="Secret Executive Board Sync")
    db_session.add(meeting_2)
    db_session.commit()

    # 3. Attempt to access meeting_2 using ws_1 access token
    response_block = client.get(f"/api/v1/meeting/{meeting_2.id}", headers=headers)
    assert response_block.status_code == 403
    assert "tenant isolation violation" in response_block.json()["detail"].lower()


# ==========================================
# 5. SECURITY HEADERS & RATE LIMITER TESTS
# ==========================================


def test_security_headers_present(client):
    """Verifies that appropriate HTTP Security Headers
    are injected by gateway middleware.
    """
    response = client.get("/health")
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert "default-src 'self'" in response.headers.get("Content-Security-Policy", "")


@patch("app.core.rate_limiter.redis_limiter")
def test_rate_limiter_middleware_triggers_429(mock_redis, client):
    """Verifies that Redis sliding window rate limits
    trigger HTTP 429 Too Many Requests.
    """
    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = [None, 500, None, None]
    mock_redis.pipeline.return_value = mock_pipeline

    response = client.post("/api/v1/meeting/start")
    assert response.status_code == 429
    assert "rate limit exceeded" in response.text.lower()


# ==========================================
# 6. SESSION MANAGEMENT API ROUTERS TESTS
# ==========================================


def test_session_management_api(db_session, client):
    """Verifies complete session lifecycle listing
    and manual device revocation via auth router.
    """
    email = "session_mgmt@example.com"
    # Strong password: HIBP check falls back gracefully in test environment
    password = "Kx9#Lp2!vQz8$mN9_sess"

    # 1. Register account
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg_resp.status_code == 201

    # 2. Manually verify email using the test db_session (avoids Docker DB connection)
    from app.models.auth import User as DbUser

    u = db_session.query(DbUser).filter(DbUser.email == email).first()
    assert u is not None
    u.is_email_verified = True
    u.is_active = True  # mirrors what verify_email service does
    db_session.commit()

    # 3. Login to get access token + session
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4. Fetch active sessions list
    sessions_resp = client.get("/api/v1/auth/sessions", headers=headers)
    assert sessions_resp.status_code == 200
    sessions_list = sessions_resp.json()
    assert len(sessions_list) > 0
    session_id = sessions_list[0]["id"]

    # 5. Revoke the session
    revoke_resp = client.delete(f"/api/v1/auth/sessions/{session_id}", headers=headers)
    assert revoke_resp.status_code == 204

    # 6. Verify no active sessions remain
    sessions_resp_2 = client.get("/api/v1/auth/sessions", headers=headers)
    assert len(sessions_resp_2.json()) == 0


# ==========================================
# 7. WEBSOCKET HANDSHAKE AUTH TESTS
# ==========================================


@pytest.mark.asyncio
async def test_websocket_user_auth_success():
    """Verifies that WebSocket handshake tokens verify correctly from query params."""
    from fastapi import WebSocket

    from app.core.iam import get_websocket_user

    mock_websocket = MagicMock(spec=WebSocket)
    user_id_val = uuid.uuid4()
    access_token_payload = {
        "iss": "auth.notedmaam.ai",
        "sub": str(user_id_val),
        "aud": "api.notedmaam.ai",
        "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
        "nbf": int(datetime.now(UTC).timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    active_key = jwks_manager.get_active_key()
    access_token = active_key.sign_token(access_token_payload)
    mock_websocket.query_params = {"token": access_token}

    res_user = await get_websocket_user(mock_websocket)
    assert res_user == user_id_val
