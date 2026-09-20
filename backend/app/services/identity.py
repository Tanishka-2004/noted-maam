import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.jwks import jwks_manager
from app.core.metrics import metrics_collector
from app.core.security import (
    check_password_breached,
    check_password_strength,
    hash_password,
    verify_password,
)
from app.models.auth import (
    AuditLog,
    Device,
    Invitation,
    Membership,
    PasswordHistory,
    User,
    Workspace,
)
from app.models.auth import (
    Session as DbSession,
)

logger = logging.getLogger("app.identity")


def parse_user_agent(ua_string: str | None) -> tuple[str, str]:
    """Resolves browser and operating system from user agent string."""
    if not ua_string:
        return "Unknown Browser", "Unknown OS"

    os_name = "Unknown OS"
    if "Windows" in ua_string:
        os_name = "Windows"
    elif "Macintosh" in ua_string or "Mac OS X" in ua_string:
        os_name = "macOS"
    elif "iPhone" in ua_string:
        os_name = "iOS (iPhone)"
    elif "iPad" in ua_string:
        os_name = "iOS (iPad)"
    elif "Android" in ua_string:
        os_name = "Android"
    elif "Linux" in ua_string:
        os_name = "Linux"

    browser_name = "Unknown Browser"
    if "Firefox" in ua_string:
        browser_name = "Firefox"
    elif "Chrome" in ua_string and "Safari" in ua_string:
        browser_name = "Chrome"
    elif "Safari" in ua_string and "Chrome" not in ua_string:
        browser_name = "Safari"
    elif "Edge" in ua_string or "Edg" in ua_string:
        browser_name = "Edge"

    return browser_name, os_name


class IdentityService:
    def __init__(self, db: Session):
        self.db = db

    def write_audit_log(
        self,
        event_type: str,
        user_id: uuid.UUID | None = None,
        workspace_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        severity: str = "INFO",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Helper writing immutable audit logs to database."""
        log = AuditLog(
            user_id=user_id,
            workspace_id=workspace_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity,
            details=details,
        )
        self.db.add(log)
        self.db.commit()

    async def register_user(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str]:
        """Registers a user credentials account.
        Enforces idempotency, zxcvbn complexity, and HIBP checks.
        """
        metrics_collector.increment("registration_total")
        self.write_audit_log(
            "registration_started",
            details={"email": email},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # 1. Complexity constraints validation
        strong, msg = check_password_strength(password)
        if not strong:
            self.write_audit_log(
                "registration_failed",
                details={"email": email, "reason": "weak_password"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise ValueError(f"Password fails complexity criteria: {msg}")

        # 2. Breach verification
        breached = await check_password_breached(password)
        if breached:
            self.write_audit_log(
                "registration_failed",
                details={"email": email, "reason": "breached_password"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise ValueError(
                "Password identified as compromised in a public database breach."
            )

        # 3. Idempotency check on email
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            if existing_user.is_active:
                self.write_audit_log(
                    "registration_failed",
                    details={"email": email, "reason": "email_exists"},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                raise ValueError("Email already registered.")
            else:
                # Update credentials and re-trigger onboarding flow
                # for pending verification state
                existing_user.password_hash = hash_password(password)
                existing_user.created_at = datetime.utcnow()
                # Generate new token
                token = uuid.uuid4().hex
                token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

                # Update existing pending verification record
                pending_invite = (
                    self.db.query(Invitation)
                    .filter(
                        Invitation.email == email,
                        Invitation.is_accepted.is_(False),
                    )
                    .first()
                )
                if pending_invite:
                    pending_invite.token_hash = token_hash
                    pending_invite.expires_at = datetime.utcnow() + timedelta(hours=24)
                else:
                    new_invite = Invitation(
                        workspace_id=uuid.uuid4(),
                        email=email,
                        role="Member",
                        token_hash=token_hash,
                        is_accepted=False,
                        expires_at=datetime.utcnow() + timedelta(hours=24),
                    )
                    self.db.add(new_invite)

                self.db.commit()
                self.write_audit_log(
                    "registration_idempotent_retrigger",
                    user_id=existing_user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                return existing_user, token

        # 4. Standard User Creation
        pwd_hash = hash_password(password)
        user = User(email=email, password_hash=pwd_hash, is_active=False)
        self.db.add(user)
        self.db.flush()

        # Add initial password hash to user password history
        history = PasswordHistory(user_id=user.id, password_hash=pwd_hash)
        self.db.add(history)

        # 5. Generate verification token details
        token = uuid.uuid4().hex
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        # Write invitation token as verification trigger
        # (bound to system self-registration)
        # Here we create a mock invitation record
        invitation = Invitation(
            workspace_id=uuid.uuid4(),  # placeholder org root UUID
            email=email,
            role="Member",
            token_hash=token_hash,
            is_accepted=False,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        self.db.add(invitation)
        self.db.commit()

        self.write_audit_log(
            "registration_completed",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return user, token

    def verify_email(
        self,
        token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        """Validates verification tokens, provisions workspace memberships,
        and activates accounts.
        """
        metrics_collector.increment("verification_total")
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        invitation = (
            self.db.query(Invitation)
            .filter(
                Invitation.token_hash == token_hash,
                Invitation.is_accepted.is_(False),
            )
            .first()
        )

        if not invitation:
            self.write_audit_log(
                "verification_failed",
                details={"reason": "invalid_token"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise ValueError("Invalid or already consumed verification token.")

        if invitation.expires_at < datetime.utcnow():
            self.write_audit_log(
                "verification_failed",
                details={"reason": "expired_token"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise ValueError("Verification token expired.")

        user = self.db.query(User).filter(User.email == invitation.email).first()
        if not user:
            raise ValueError(
                "No user account mapping found for target invitation email."
            )

        # Activate user
        user.is_active = True
        invitation.is_accepted = True

        # Generate a default Workspace for the user on onboarding
        workspace = Workspace(name=f"{user.email.split('@')[0]}'s Workspace")
        self.db.add(workspace)
        self.db.flush()

        # Link invitation target workspace to actual default workspace
        invitation.workspace_id = workspace.id

        # Bind membership
        membership = Membership(
            user_id=user.id, workspace_id=workspace.id, role="Owner"
        )
        self.db.add(membership)
        self.db.commit()

        self.write_audit_log(
            "verification_success",
            user_id=user.id,
            workspace_id=workspace.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return user

    def login_user(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        """Authenticates user credentials. Resolves session limits (max 10),
        and tracks device details.
        """
        user = self.db.query(User).filter(User.email == email).first()

        if not user or not user.password_hash:
            metrics_collector.increment("login_failure_total")
            self.write_audit_log(
                "login_failed",
                details={"email": email, "reason": "invalid_credentials"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            metrics_collector.increment("login_failure_total")
            self.write_audit_log(
                "login_failed",
                user_id=user.id,
                details={"reason": "unverified_account"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise ValueError("Account pending email verification.")

        if not verify_password(password, user.password_hash):
            metrics_collector.increment("login_failure_total")
            self.write_audit_log(
                "login_failed",
                user_id=user.id,
                details={"reason": "wrong_password"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise ValueError("Invalid email or password.")

        # Limit check: enforce maximum 10 active devices per user
        active_sessions = (
            self.db.query(DbSession)
            .filter(DbSession.user_id == user.id, DbSession.is_revoked.is_(False))
            .order_by(DbSession.created_at)
            .all()
        )

        if len(active_sessions) >= 10:
            # Auto-revoke oldest session
            oldest = active_sessions[0]
            oldest.is_revoked = True
            self.write_audit_log(
                "session_limit_exceeded_revoke",
                user_id=user.id,
                details={"revoked_session_id": str(oldest.id)},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        # Resolve primary workspace context (first joined workspace)
        membership = (
            self.db.query(Membership).filter(Membership.user_id == user.id).first()
        )
        workspace_id = membership.workspace_id if membership else None

        # Generate tokens
        access_token_payload = {
            "iss": "auth.notedmaam.ai",
            "sub": str(user.id),
            "aud": "api.notedmaam.ai",
            "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
            "nbf": int(datetime.now(UTC).timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
            "jti": uuid.uuid4().hex,
            "workspace_id": str(workspace_id) if workspace_id else None,
        }

        # Access token signed using RS256
        active_key = jwks_manager.get_active_key()
        access_token = active_key.sign_token(access_token_payload)

        # Opaque refresh token
        refresh_token = f"rt_{uuid.uuid4().hex}{uuid.uuid4().hex}"
        refresh_token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        family_id = f"fam_{uuid.uuid4().hex[:8]}"

        # Write Session record
        session = DbSession(
            user_id=user.id,
            workspace_id=workspace_id,
            refresh_token_hash=refresh_token_hash,
            family_id=family_id,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        self.db.add(session)
        self.db.flush()

        # Write Device record
        browser, os_name = parse_user_agent(user_agent)
        device = Device(
            session_id=session.id,
            user_agent=user_agent,
            browser=browser,
            operating_system=os_name,
            ip_address=ip_address,
            geographic_location="Unknown Location",
            last_active_at=datetime.utcnow(),
        )
        self.db.add(device)
        self.db.commit()

        metrics_collector.increment("login_success_total")
        self.write_audit_log(
            "login_success",
            user_id=user.id,
            workspace_id=workspace_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return user, access_token, refresh_token

    def rotate_refresh_token(
        self,
        old_refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        """Implements Refresh Token Rotation (RTR). Identifies token replays
        and invalidates hijacked chains.
        """
        metrics_collector.increment("refresh_total")
        old_hash = hashlib.sha256(old_refresh_token.encode("utf-8")).hexdigest()

        # Find matching session
        session = (
            self.db.query(DbSession)
            .filter(DbSession.refresh_token_hash == old_hash)
            .first()
        )
        if not session:
            self.write_audit_log(
                "refresh_failed",
                details={"reason": "invalid_refresh_token"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise ValueError("Invalid refresh token.")

        if session.is_revoked or session.expires_at < datetime.utcnow():
            self.write_audit_log(
                "refresh_failed",
                user_id=session.user_id,
                details={"reason": "revoked_or_expired_token"},
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise ValueError("Refresh token revoked or expired.")

        # REPLAY ATTACK DETECTION
        if session.is_used:
            metrics_collector.increment("replay_attack_total")
            # Invalidate all family sessions immediately
            self.db.query(DbSession).filter(
                DbSession.family_id == session.family_id
            ).update({"is_revoked": True}, synchronize_session=False)
            self.db.commit()

            self.write_audit_log(
                "token_replay_detected",
                user_id=session.user_id,
                severity="CRITICAL",
                details={
                    "replayed_token_hash": old_hash,
                    "family_id": session.family_id,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise ValueError("Token family compromise detected. Session terminated.")

        # Consume old token
        session.is_used = True

        # Generate new tokens
        access_token_payload = {
            "iss": "auth.notedmaam.ai",
            "sub": str(session.user_id),
            "aud": "api.notedmaam.ai",
            "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
            "nbf": int(datetime.now(UTC).timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
            "jti": uuid.uuid4().hex,
            "workspace_id": str(session.workspace_id) if session.workspace_id else None,
        }
        active_key = jwks_manager.get_active_key()
        new_access_token = active_key.sign_token(access_token_payload)

        new_refresh_token = f"rt_{uuid.uuid4().hex}{uuid.uuid4().hex}"
        new_hash = hashlib.sha256(new_refresh_token.encode("utf-8")).hexdigest()

        # Write new session step maintaining the same family_id
        new_session = DbSession(
            user_id=session.user_id,
            workspace_id=session.workspace_id,
            refresh_token_hash=new_hash,
            family_id=session.family_id,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        self.db.add(new_session)
        self.db.flush()

        # Transfer/Update device attributes
        device = self.db.query(Device).filter(Device.session_id == session.id).first()
        browser, os_name = parse_user_agent(user_agent)
        new_device = Device(
            session_id=new_session.id,
            user_agent=user_agent,
            browser=browser,
            operating_system=os_name,
            ip_address=ip_address,
            geographic_location=(
                device.geographic_location if device else "Unknown Location"
            ),
            last_active_at=datetime.utcnow(),
        )
        self.db.add(new_device)
        self.db.commit()

        self.write_audit_log(
            "token_refresh_success",
            user_id=session.user_id,
            workspace_id=session.workspace_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return new_access_token, new_refresh_token

    def logout_user(
        self,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Revokes the target refresh token and session."""
        rt_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        session = (
            self.db.query(DbSession)
            .filter(DbSession.refresh_token_hash == rt_hash)
            .first()
        )
        if session:
            session.is_revoked = True
            self.db.commit()
            self.write_audit_log(
                "logout",
                user_id=session.user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )

    def revoke_all_sessions(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Revokes all active sessions for the specified user."""
        self.db.query(DbSession).filter(
            DbSession.user_id == user_id, DbSession.is_revoked.is_(False)
        ).update({"is_revoked": True}, synchronize_session=False)
        self.db.commit()
        self.write_audit_log(
            "revoke_all_sessions",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def onboard_oauth_user(
        self,
        provider: str,
        oauth_id: str,
        email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        """Onboards and authenticates a user logging in via Google OAuth.
        Handles account linking, workspace setup, and active session logins.
        """
        metrics_collector.increment("oauth_login_total")

        # 1. Lookup user by provider & oauth_id
        user = (
            self.db.query(User)
            .filter(User.oauth_provider == provider, User.oauth_id == oauth_id)
            .first()
        )

        if not user:
            # 2. Check if user already exists by email
            user = self.db.query(User).filter(User.email == email).first()
            if user:
                # Account Linking: bind OAuth credentials to active user profile
                user.oauth_provider = provider
                user.oauth_id = oauth_id
                user.is_active = True  # Verified by provider
                self.db.commit()
                self.write_audit_log(
                    "oauth_link",
                    user_id=user.id,
                    details={"provider": provider, "oauth_id": oauth_id},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            else:
                # 3. Provision new OAuth User profile
                user = User(
                    email=email,
                    oauth_provider=provider,
                    oauth_id=oauth_id,
                    is_active=True,
                )
                self.db.add(user)
                self.db.flush()

                # Generate a default Workspace for the OAuth user
                workspace = Workspace(name=f"{email.split('@')[0]}'s Workspace")
                self.db.add(workspace)
                self.db.flush()

                # Bind membership
                membership = Membership(
                    user_id=user.id, workspace_id=workspace.id, role="Owner"
                )
                self.db.add(membership)
                self.db.commit()

                self.write_audit_log(
                    "oauth_registration_completed",
                    user_id=user.id,
                    workspace_id=workspace.id,
                    details={"provider": provider},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

        # 4. Generate sessions & tokens
        active_sessions = (
            self.db.query(DbSession)
            .filter(DbSession.user_id == user.id, DbSession.is_revoked.is_(False))
            .order_by(DbSession.created_at)
            .all()
        )

        if len(active_sessions) >= 10:
            oldest = active_sessions[0]
            oldest.is_revoked = True

        user_membership = (
            self.db.query(Membership).filter(Membership.user_id == user.id).first()
        )
        workspace_id = user_membership.workspace_id if user_membership else None

        access_token_payload = {
            "iss": "auth.notedmaam.ai",
            "sub": str(user.id),
            "aud": "api.notedmaam.ai",
            "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
            "nbf": int(datetime.now(UTC).timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
            "jti": uuid.uuid4().hex,
            "workspace_id": str(workspace_id) if workspace_id else None,
        }

        active_key = jwks_manager.get_active_key()
        access_token = active_key.sign_token(access_token_payload)

        refresh_token = f"rt_{uuid.uuid4().hex}{uuid.uuid4().hex}"
        refresh_token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        family_id = f"fam_{uuid.uuid4().hex[:8]}"

        session = DbSession(
            user_id=user.id,
            workspace_id=workspace_id,
            refresh_token_hash=refresh_token_hash,
            family_id=family_id,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        self.db.add(session)
        self.db.flush()

        browser, os_name = parse_user_agent(user_agent)
        device = Device(
            session_id=session.id,
            user_agent=user_agent,
            browser=browser,
            operating_system=os_name,
            ip_address=ip_address,
            geographic_location="Unknown Location",
            last_active_at=datetime.utcnow(),
        )
        self.db.add(device)
        self.db.commit()

        self.write_audit_log(
            "oauth_login",
            user_id=user.id,
            workspace_id=workspace_id,
            details={"provider": provider},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return user, access_token, refresh_token

    def get_active_sessions(self, user_id: uuid.UUID) -> list[DbSession]:
        """Queries and returns all active session records for the target user."""
        from sqlalchemy.orm import joinedload

        return (
            self.db.query(DbSession)
            .options(joinedload(DbSession.device))
            .filter(DbSession.user_id == user_id, DbSession.is_revoked.is_(False))
            .order_by(DbSession.created_at.desc())
            .all()
        )

    def revoke_session(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Marks a target session as revoked, asserting ownership."""
        session = (
            self.db.query(DbSession)
            .filter(DbSession.id == session_id, DbSession.user_id == user_id)
            .first()
        )
        if not session:
            raise ValueError("Session not found or access denied.")

        if not session.is_revoked:
            session.is_revoked = True
            self.db.commit()
            self.write_audit_log(
                "session_revoked_manually",
                user_id=user_id,
                details={"revoked_session_id": str(session_id)},
                ip_address=ip_address,
                user_agent=user_agent,
            )
