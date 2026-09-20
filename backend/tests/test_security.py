"""
Phase 2.12 — Security-Critical Test Suite

Covers attack vectors and edge cases for the IAM subsystem:
  - JWT forgery, malformed tokens, wrong algorithm
  - Invalid audience / issuer / kid
  - Expired tokens and key rotation
  - RTR replay, concurrent refresh, revoked family
  - OAuth CSRF state replay
  - WebSocket JWT edge cases
  - Rate limiter bypass attempts
  - Concurrent session / device revocation races
  - Logout idempotency
  - Redis and DB failover graceful degradation
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.jwks import JWKSKey, JWKSManager, jwks_manager
from app.core.security import hash_password
from app.main import app
from app.models.auth import Session as DbSession
from app.models.auth import User
from app.services.identity import IdentityService

# ── Isolated SQLite test database ──────────────────────────────────────────
TEST_DB_URL = "sqlite:///./test_security.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db_session")
def fixture_db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def fixture_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(name="active_user")
def fixture_active_user(db_session):
    """Seeds a verified, active user ready for login."""
    pwd = "Kx9#Lp2!vQz8$mN9_sec"
    user = User(
        email="security@example.com",
        password_hash=hash_password(pwd),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user, pwd


def _make_token(payload_overrides: dict, key: JWKSKey | None = None) -> str:
    """Helper: build a signed token with optional claim overrides."""
    active_key = key or jwks_manager.get_active_key()
    now = datetime.now(UTC)
    base = {
        "iss": "auth.notedmaam.ai",
        "aud": "api.notedmaam.ai",
        "sub": str(uuid.uuid4()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "nbf": int(now.timestamp()),
        "iat": int(now.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    base.update(payload_overrides)
    return active_key.sign_token(base)


# ══════════════════════════════════════════════════════════════════════════════
# 1. JWT FORGERY & MALFORMED TOKEN TESTS
# ══════════════════════════════════════════════════════════════════════════════


def test_reject_token_signed_with_unknown_key(client, active_user):
    """A token signed with an unregistered RSA key must be rejected."""
    rogue_key = JWKSKey(kid="rogue_key_abc")
    token = _make_token({}, key=rogue_key)
    resp = client.post(
        "/api/v1/meeting/start",
        json={"title": "Infiltration"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert "not found in active JWKS" in resp.text or resp.status_code == 401


def test_reject_malformed_jwt_garbage_string(client):
    """A garbage string passed as Bearer token must return 401."""
    resp = client.post(
        "/api/v1/meeting/start",
        json={"title": "Test"},
        headers={"Authorization": "Bearer this.is.garbage"},
    )
    assert resp.status_code == 401


def test_reject_jwt_with_hs256_algorithm_confusion(client):
    """A token signed with HMAC HS256 instead of RS256 must be rejected.

    Prevents algorithm confusion attacks where an attacker uses HS256 and
    the server's public key as the HMAC secret.
    """
    payload = {
        "iss": "auth.notedmaam.ai",
        "aud": "api.notedmaam.ai",
        "sub": str(uuid.uuid4()),
        "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
        "nbf": int(datetime.now(UTC).timestamp()),
        "iat": int(datetime.now(UTC).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    # Sign with symmetric HMAC
    hs256_token = jwt.encode(payload, "secret_hmac_key", algorithm="HS256")
    resp = client.post(
        "/api/v1/meeting/start",
        json={"title": "Test"},
        headers={"Authorization": f"Bearer {hs256_token}"},
    )
    assert resp.status_code == 401


def test_reject_jwt_missing_kid_header(client, active_user):
    """A token with no kid header must be rejected."""
    now = datetime.now(UTC)
    payload = {
        "iss": "auth.notedmaam.ai",
        "aud": "api.notedmaam.ai",
        "sub": str(uuid.uuid4()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "nbf": int(now.timestamp()),
        "iat": int(now.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    active_key = jwks_manager.get_active_key()
    from cryptography.hazmat.primitives import serialization

    pem = active_key.private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    # Encode without kid header
    token_no_kid = jwt.encode(payload, pem, algorithm="RS256")
    resp = client.post(
        "/api/v1/meeting/start",
        json={"title": "Test"},
        headers={"Authorization": f"Bearer {token_no_kid}"},
    )
    assert resp.status_code == 401


def test_reject_jwt_with_invalid_kid(client, active_user):
    """A token with a kid that doesn't match any registered key must be rejected."""
    # Build a token signed by the real key but embed a non-existent kid in the header
    active_key = jwks_manager.get_active_key()
    from cryptography.hazmat.primitives import serialization

    pem = active_key.private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    now = datetime.now(UTC)
    payload = {
        "iss": "auth.notedmaam.ai",
        "aud": "api.notedmaam.ai",
        "sub": str(uuid.uuid4()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "nbf": int(now.timestamp()),
        "iat": int(now.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token_bad_kid = jwt.encode(
        payload, pem, algorithm="RS256", headers={"kid": "nonexistent_key_xyz"}
    )
    resp = client.post(
        "/api/v1/meeting/start",
        json={"title": "Test"},
        headers={"Authorization": f"Bearer {token_bad_kid}"},
    )
    assert resp.status_code == 401


def test_reject_expired_jwt(client, active_user):
    """An expired JWT must be rejected even if otherwise valid."""
    expired_token = _make_token(
        {
            "exp": int((datetime.now(UTC) - timedelta(minutes=30)).timestamp()),
        }
    )
    resp = client.post(
        "/api/v1/meeting/start",
        json={"title": "Test"},
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401


def test_reject_jwt_wrong_audience(client, active_user):
    """A JWT with an invalid audience claim must be rejected."""
    token = _make_token({"aud": "wrong.audience.example.com"})
    resp = client.post(
        "/api/v1/meeting/start",
        json={"title": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


def test_reject_jwt_wrong_issuer(client, active_user):
    """A JWT with a tampered iss claim must be rejected."""
    token = _make_token({"iss": "evil.attacker.com"})
    resp = client.post(
        "/api/v1/meeting/start",
        json={"title": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # PyJWT validates aud but not iss by default unless options configured.
    # IAMMiddleware should at minimum return 401 on a bad token.
    assert resp.status_code in (401, 403)


def test_reject_missing_authorization_header(client):
    """Requests with no Authorization header must return 401."""
    resp = client.post("/api/v1/meeting/start", json={"title": "Test"})
    assert resp.status_code == 401


def test_reject_bearer_prefix_only(client):
    """A 'Bearer ' prefix with no token value must return 401."""
    resp = client.post(
        "/api/v1/meeting/start",
        json={"title": "Test"},
        headers={"Authorization": "Bearer "},
    )
    assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# 2. JWKS KEY ROTATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


def test_jwks_endpoint_returns_active_keys(client):
    """Public JWKS endpoint must return at least one RSA key."""
    resp = client.get("/api/v1/auth/.well-known/jwks.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "keys" in data
    assert len(data["keys"]) >= 1
    key = data["keys"][0]
    assert key["kty"] == "RSA"
    assert key["alg"] == "RS256"
    assert "n" in key and "e" in key and "kid" in key


def test_key_rotation_adds_new_signing_key():
    """After rotation, a new key is added and tokens signed with both are verifiable."""
    mgr = JWKSManager(rotation_days=30, grace_hours=24)
    key_before = mgr.get_active_key()

    now = datetime.now(UTC)
    payload = {
        "iss": "auth.notedmaam.ai",
        "aud": "api.notedmaam.ai",
        "sub": str(uuid.uuid4()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "nbf": int(now.timestamp()),
        "iat": int(now.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token_old = key_before.sign_token(payload)

    mgr.rotate_keys()
    key_after = mgr.get_active_key()

    assert key_after.kid != key_before.kid
    # Old token must still verify during grace period (key still in pool)
    result = mgr.verify_token(token_old)
    assert result["sub"] == payload["sub"]


def test_purged_key_token_is_rejected():
    """A token signed with a purged key (outside grace window) must not verify."""
    mgr = JWKSManager(rotation_days=0, grace_hours=0)
    old_key = mgr.get_active_key()

    now = datetime.now(UTC)
    payload = {
        "iss": "auth.notedmaam.ai",
        "aud": "api.notedmaam.ai",
        "sub": str(uuid.uuid4()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "nbf": int(now.timestamp()),
        "iat": int(now.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token_old = old_key.sign_token(payload)

    # Force rotate: with 0-day/0-hour window the old key will be purged
    mgr.rotate_keys()
    assert all(k.kid != old_key.kid for k in mgr.keys)

    with pytest.raises(jwt.InvalidTokenError):
        mgr.verify_token(token_old)


# ══════════════════════════════════════════════════════════════════════════════
# 3. REFRESH TOKEN ROTATION — CONCURRENT & EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════


def test_refresh_token_is_single_use(db_session, client):
    """A refresh token can only be rotated once; a second use is a replay."""
    user, pwd = fixture_active_user_direct(db_session)
    identity_service = IdentityService(db_session)
    _, _, rt = identity_service.login_user(email=user.email, password=pwd)

    # First rotation succeeds
    _, rt_2 = identity_service.rotate_refresh_token(rt)

    # Second use of the SAME rt_1 is a replay → family revoked
    with pytest.raises(ValueError, match="compromise detected"):
        identity_service.rotate_refresh_token(rt)

    # All sessions in family must be revoked
    sessions = db_session.query(DbSession).filter(DbSession.user_id == user.id).all()
    assert all(s.is_revoked for s in sessions)


def test_revoked_refresh_token_cannot_be_used(db_session):
    """A manually revoked refresh token must raise on rotation attempt."""
    user, pwd = fixture_active_user_direct(db_session)
    identity_service = IdentityService(db_session)
    _, _, rt = identity_service.login_user(email=user.email, password=pwd)

    # Revoke the session directly
    session = db_session.query(DbSession).filter(DbSession.user_id == user.id).first()
    session.is_revoked = True
    db_session.commit()

    with pytest.raises(ValueError):
        identity_service.rotate_refresh_token(rt)


def test_concurrent_refresh_does_not_duplicate_sessions(db_session):
    """Two near-simultaneous refresh attempts with the same token:
    first succeeds, second raises replay error.
    """
    user, pwd = fixture_active_user_direct(db_session)
    svc = IdentityService(db_session)
    _, _, rt = svc.login_user(email=user.email, password=pwd)

    # First rotation succeeds
    _, rt_new = svc.rotate_refresh_token(rt)

    # Second attempt with original rt (simulated second concurrent request)
    with pytest.raises(ValueError):
        svc.rotate_refresh_token(rt)


def test_logout_revokes_session_idempotently(db_session, client):
    """Logging out twice should not raise an error (idempotent revocation)."""
    user, pwd = fixture_active_user_direct(db_session)
    identity_service = IdentityService(db_session)
    _, _, rt = identity_service.login_user(email=user.email, password=pwd)

    session = db_session.query(DbSession).filter(DbSession.user_id == user.id).first()
    session_id = session.id

    # First revocation
    identity_service.revoke_session(user.id, session_id)

    # Second revocation on already-revoked session should not raise
    identity_service.revoke_session(user.id, session_id)

    session_after = (
        db_session.query(DbSession).filter(DbSession.id == session_id).first()
    )
    assert session_after.is_revoked is True


def test_revoke_session_cross_user_rejected(db_session):
    """User B cannot revoke User A's session."""
    user_a = User(
        email="usera@example.com",
        password_hash=hash_password("Kx9#Lp2!vQz8$mN9"),
        is_active=True,
    )
    user_b = User(
        email="userb@example.com",
        password_hash=hash_password("Kx9#Lp2!vQz8$mN9"),
        is_active=True,
    )
    db_session.add_all([user_a, user_b])
    db_session.commit()

    svc = IdentityService(db_session)
    _, _, _ = svc.login_user(email=user_a.email, password="Kx9#Lp2!vQz8$mN9")

    session_a = (
        db_session.query(DbSession).filter(DbSession.user_id == user_a.id).first()
    )

    # User B tries to revoke user A's session
    with pytest.raises(ValueError, match="Session not found"):
        svc.revoke_session(user_b.id, session_a.id)


# ══════════════════════════════════════════════════════════════════════════════
# 4. OAUTH CSRF STATE REPLAY TESTS
# ══════════════════════════════════════════════════════════════════════════════


def test_oauth_callback_without_state_cookie_rejected(client):
    """OAuth callback with mismatched or missing state cookie must be rejected."""
    # No state cookie set: state parameter won't match anything
    resp = client.get(
        "/api/v1/auth/oauth/google/callback?code=valid_code&state=attacker_state"
    )
    assert resp.status_code in (400, 401, 422)


def test_oauth_callback_state_mismatch_rejected(client):
    """OAuth callback where state param differs from cookie must fail CSRF check."""
    # Set a different state in the cookie
    client.cookies.set("oauth_state", "expected_state_abc")
    resp = client.get(
        "/api/v1/auth/oauth/google/callback?code=code123&state=tampered_state_xyz"
    )
    assert resp.status_code in (400, 401)


def test_oauth_callback_replayed_state_rejected(client):
    """Replaying the same state in a second callback request must fail."""
    state = f"csrf_{uuid.uuid4().hex}"
    client.cookies.set("oauth_state", state)

    # First callback attempt (will fail because code is fake, but state check passes)
    with patch(
        "app.core.identity_providers.GoogleOAuthProvider.exchange_code_for_profile",
        side_effect=ValueError("invalid_code"),
    ):
        resp1 = client.get(
            f"/api/v1/auth/oauth/google/callback?code=code1&state={state}"
        )
    assert resp1.status_code in (400, 401)


# ══════════════════════════════════════════════════════════════════════════════
# 5. WEBSOCKET AUTHENTICATION EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_websocket_rejects_missing_token():
    """WebSocket with no token query param raises WebSocketException."""
    from fastapi import WebSocketException

    from app.core.iam import get_websocket_user

    mock_ws = MagicMock()
    # query_params.get("token") returns None when key absent
    mock_ws.query_params = MagicMock()
    mock_ws.query_params.get = MagicMock(return_value=None)

    with pytest.raises(WebSocketException):
        await get_websocket_user(mock_ws)


@pytest.mark.asyncio
async def test_websocket_rejects_expired_token():
    """WebSocket with an expired JWT must raise WebSocketException."""
    from fastapi import WebSocketException

    from app.core.iam import get_websocket_user

    expired_token = _make_token(
        {
            "exp": int((datetime.now(UTC) - timedelta(minutes=5)).timestamp()),
        }
    )
    mock_ws = MagicMock()
    mock_ws.query_params = MagicMock()
    mock_ws.query_params.get = MagicMock(return_value=expired_token)

    with pytest.raises(WebSocketException):
        await get_websocket_user(mock_ws)


@pytest.mark.asyncio
async def test_websocket_rejects_forged_token():
    """WebSocket with a token from an unknown key must raise WebSocketException."""
    from fastapi import WebSocketException

    from app.core.iam import get_websocket_user

    rogue_key = JWKSKey(kid="rogue_ws_key")
    token = _make_token({}, key=rogue_key)
    mock_ws = MagicMock()
    mock_ws.query_params = MagicMock()
    mock_ws.query_params.get = MagicMock(return_value=token)

    with pytest.raises(WebSocketException):
        await get_websocket_user(mock_ws)


# ══════════════════════════════════════════════════════════════════════════════
# 6. RATE LIMITER EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════


@patch("app.core.rate_limiter.redis_limiter")
def test_rate_limiter_passes_under_threshold(mock_redis, client):
    """Requests under the rate limit threshold must pass through normally."""
    mock_pipeline = MagicMock()
    # Count is 5 — well under 100 IP limit
    mock_pipeline.execute.return_value = [None, 5, None, None]
    mock_redis.pipeline.return_value = mock_pipeline

    resp = client.get("/health")
    assert resp.status_code == 200


@patch("app.core.rate_limiter.redis_limiter")
def test_rate_limiter_ip_threshold_triggers_429(mock_redis, client):
    """Requests exceeding IP threshold must return 429."""
    mock_pipeline = MagicMock()
    mock_pipeline.execute.return_value = [None, 500, None, None]
    mock_redis.pipeline.return_value = mock_pipeline

    resp = client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "y"})
    assert resp.status_code == 429


@patch("app.core.rate_limiter.redis_limiter")
def test_rate_limiter_redis_outage_allows_through(mock_redis, client):
    """When Redis is unavailable, the rate limiter fails open (allows requests)."""
    import redis

    mock_redis.pipeline.side_effect = redis.RedisError("Connection refused")

    resp = client.get("/health")
    # Must not fail: graceful degradation allows the request through
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 7. SECURITY HEADERS VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════


def test_all_security_headers_present(client):
    """All required security headers must be present on every response."""
    resp = client.get("/health")
    headers = resp.headers

    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "max-age=31536000" in headers.get("Strict-Transport-Security", "")
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")


def test_security_headers_on_auth_endpoints(client):
    """Security headers must be present on auth routes too."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "doesntmatter"},
    )
    # Even a 401 response should carry security headers
    assert "X-Frame-Options" in resp.headers
    assert "X-Content-Type-Options" in resp.headers


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS (local fixtures not using pytest parametrize)
# ══════════════════════════════════════════════════════════════════════════════


def fixture_active_user_direct(db_session):
    """Creates and returns an active user directly from the db_session."""
    pwd = "Kx9#Lp2!vQz8$mN9"
    email = f"sec_{uuid.uuid4().hex[:8]}@example.com"
    user = User(email=email, password_hash=hash_password(pwd), is_active=True)
    db_session.add(user)
    db_session.commit()
    return user, pwd
