from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings


class OAuthProvider(ABC):
    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """Generates the authorization redirect URL with state nonce."""
        pass

    @abstractmethod
    async def exchange_code_for_profile(self, code: str) -> dict[str, Any]:
        """Exchanges callback authorization code for user profile properties."""
        pass


class GoogleOAuthProvider(OAuthProvider):
    def __init__(self) -> None:
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI

    def get_authorization_url(self, state: str) -> str:
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}?{query_string}"

    async def exchange_code_for_profile(self, code: str) -> dict[str, Any]:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Exchange authorization code for tokens
            response = await client.post(token_url, data=data)
            if response.status_code != 200:
                raise ValueError(
                    f"Failed exchanging Google OAuth token: {response.text}"
                )

            token_json = response.json()
            access_token = token_json.get("access_token")
            if not access_token:
                raise ValueError("Response lacks access_token claim.")

            # 2. Query user profile using token
            userinfo_url = "https://openidconnect.googleapis.com/v1/userinfo"
            headers = {"Authorization": f"Bearer {access_token}"}
            profile_response = await client.get(userinfo_url, headers=headers)
            if profile_response.status_code != 200:
                raise ValueError(
                    "Failed fetching user profile from Google info endpoint."
                )

            profile = profile_response.json()

            # 3. Claims validation
            if not profile.get("email_verified"):
                raise ValueError("Google account email must be verified to onboarding.")

            return {
                "oauth_id": profile.get("sub"),
                "email": profile.get("email"),
                "picture": profile.get("picture"),
                "name": profile.get("name"),
            }


# Singleton active google provider instance
google_oauth_provider = GoogleOAuthProvider()
