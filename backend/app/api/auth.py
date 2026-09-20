import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.identity_providers import google_oauth_provider
from app.core.jwks import jwks_manager
from app.schemas.auth import (
    SessionResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.identity import IdentityService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/.well-known/jwks.json", status_code=200)
def get_jwks() -> dict[str, list[dict[str, Any]]]:
    """Exposes active public keys in standard JWKS format for signature validation."""
    return jwks_manager.get_jwks()


@router.post(
    "/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse
)
async def register(
    data: UserRegister, request: Request, db: Session = Depends(get_db)
) -> Any:
    """Registers a user credentials account.
    Enforces idempotency and complexity checks.
    """
    ip = request.client.host if request.client else "Unknown IP"
    ua = request.headers.get("user-agent", "Unknown User-Agent")

    identity_service = IdentityService(db)
    try:
        user, token = await identity_service.register_user(
            email=data.email, password=data.password, ip_address=ip, user_agent=ua
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/verify", status_code=status.HTTP_200_OK, response_model=UserResponse)
def verify_email(token: str, request: Request, db: Session = Depends(get_db)) -> Any:
    """Validates verification tokens, provisions workspace memberships,
    and activates accounts.
    """
    ip = request.client.host if request.client else "Unknown IP"
    ua = request.headers.get("user-agent", "Unknown User-Agent")

    identity_service = IdentityService(db)
    try:
        user = identity_service.verify_email(token=token, ip_address=ip, user_agent=ua)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e


@router.post("/login", status_code=status.HTTP_200_OK, response_model=TokenResponse)
def login(
    data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)
) -> TokenResponse:
    """Authenticates email and password. Returns access token and sets
    secure refresh token cookie.
    """
    ip = request.client.host if request.client else "Unknown IP"
    ua = request.headers.get("user-agent", "Unknown User-Agent")

    identity_service = IdentityService(db)
    try:
        user, access_token, refresh_token = identity_service.login_user(
            email=data.email, password=data.password, ip_address=ip, user_agent=ua
        )

        # Set opaque refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/api/v1/auth/refresh",
            max_age=604800,  # 7 days
        )

        return TokenResponse(access_token=access_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e


@router.post("/refresh", status_code=status.HTTP_200_OK, response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Rotates refresh and access tokens. Detects session family replays
    and invalidates hijacked chains.
    """
    ip = request.client.host if request.client else "Unknown IP"
    ua = request.headers.get("user-agent", "Unknown User-Agent")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing.",
        )

    identity_service = IdentityService(db)
    try:
        access_token, new_refresh_token = identity_service.rotate_refresh_token(
            old_refresh_token=refresh_token, ip_address=ip, user_agent=ua
        )

        # Set new rotated refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/api/v1/auth/refresh",
            max_age=604800,  # 7 days
        )

        return TokenResponse(access_token=access_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Revokes the active refresh token and logs out the client session."""
    ip = request.client.host if request.client else "Unknown IP"
    ua = request.headers.get("user-agent", "Unknown User-Agent")

    if refresh_token:
        identity_service = IdentityService(db)
        identity_service.logout_user(
            refresh_token=refresh_token, ip_address=ip, user_agent=ua
        )

    # Delete refresh token cookie
    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")
    return {"detail": "Successfully logged out."}


@router.get("/oauth/google")
def oauth_google(response: Response) -> RedirectResponse:
    """Redirects client to Google Identity Provider login page with state nonce."""
    state = uuid.uuid4().hex
    auth_url = google_oauth_provider.get_authorization_url(state)

    # Store state nonce in secure cookie for CSRF callback verify checks
    response_redirect = RedirectResponse(auth_url)
    response_redirect.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=300,
    )
    return response_redirect


@router.get("/oauth/google/callback")
async def oauth_google_callback(
    code: str,
    state: str,
    request: Request,
    oauth_state: str | None = Cookie(None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Google OAuth callback receiver.
    Performs state verification and account onboarding/linking,
    then redirects to the frontend with an HttpOnly session cookie.
    """
    if not oauth_state or state != oauth_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth security state parameter mismatch or token expired.",
        )

    ip = request.client.host if request.client else "Unknown IP"
    ua = request.headers.get("user-agent", "Unknown User-Agent")

    try:
        # Exchange code for user profile properties
        profile = await google_oauth_provider.exchange_code_for_profile(code)

        # Link account or register user
        identity_service = IdentityService(db)
        user, access_token, refresh_token = await identity_service.onboard_oauth_user(
            provider="google",
            oauth_id=profile["oauth_id"],
            email=profile["email"],
            ip_address=ip,
            user_agent=ua,
        )

        # Secure redirect target for frontend callback landing page
        response_redirect = RedirectResponse(url="http://localhost:3000/oauth/callback")

        # Set refresh token cookie on redirect
        response_redirect.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            path="/api/v1/auth/refresh",
            max_age=604800,  # 7 days
        )

        # Delete oauth_state cookie
        response_redirect.delete_cookie(key="oauth_state")

        return response_redirect
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/sessions", response_model=list[SessionResponse])
def get_sessions(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Returns active sessions associated with the logged-in user."""
    user_id = request.state.user_id
    identity_service = IdentityService(db)
    return identity_service.get_active_sessions(user_id=user_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session_endpoint(
    session_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """Revokes a target active session for the logged-in user."""
    user_id = request.state.user_id
    ip = request.client.host if request.client else "Unknown IP"
    ua = request.headers.get("user-agent", "Unknown User-Agent")

    identity_service = IdentityService(db)
    try:
        identity_service.revoke_session(
            user_id=user_id,
            session_id=session_id,
            ip_address=ip,
            user_agent=ua,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
