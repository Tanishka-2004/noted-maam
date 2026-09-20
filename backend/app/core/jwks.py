import base64
import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def int_to_base64url(val: int) -> str:
    """Helper converting an integer to a base64url-encoded string without padding."""
    byte_len = (val.bit_length() + 7) // 8
    val_bytes = val.to_bytes(byte_len, byteorder="big")
    return base64.urlsafe_b64encode(val_bytes).decode("utf-8").rstrip("=")


class JWKSKey:
    def __init__(self, kid: str | None = None):
        self.kid: str = kid or f"key_{uuid.uuid4().hex[:8]}"
        self.created_at: datetime = datetime.utcnow()
        # Generate 2048-bit RSA key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def get_public_jwk(self) -> dict[str, Any]:
        """Compiles the public key parameters into a standard JWK format."""
        numbers = self.public_key.public_numbers()
        return {
            "kty": "RSA",
            "alg": "RS256",
            "use": "sig",
            "kid": self.kid,
            "n": int_to_base64url(numbers.n),
            "e": int_to_base64url(numbers.e),
        }

    def sign_token(self, payload: dict[str, Any]) -> str:
        """Signs JWT payload using RS256 algorithm with private key."""
        headers = {"kid": self.kid}
        # Convert private key to PEM for pyjwt signing
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return jwt.encode(payload, pem, algorithm="RS256", headers=headers)


class JWKSManager:
    def __init__(self, rotation_days: int = 30, grace_hours: int = 24):
        self.rotation_days: int = rotation_days
        self.grace_hours: int = grace_hours
        self.keys: list[JWKSKey] = []
        # Bootstraps with an initial key
        self.rotate_keys()

    def rotate_keys(self) -> None:
        """Generates a new key pair and appends to validation list,
        purging old grace keys.
        """
        new_key = JWKSKey()
        self.keys.insert(0, new_key)

        # Purge keys older than rotation window + grace period
        cutoff = datetime.utcnow() - timedelta(
            days=self.rotation_days, hours=self.grace_hours
        )
        self.keys = [k for k in self.keys if k.created_at > cutoff or k == new_key]

    def get_active_key(self) -> JWKSKey:
        """Retrieves the newest key used for signing."""
        if not self.keys:
            self.rotate_keys()
        return self.keys[0]

    def get_jwks(self) -> dict[str, list[dict[str, Any]]]:
        """Compiles active public keys into standard JWKS format."""
        return {"keys": [key.get_public_jwk() for key in self.keys]}

    def verify_token(self, token: str) -> dict[str, Any]:
        """Decodes and validates a JWT signature against the current key pool."""
        # Unverified header check to extract kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise jwt.InvalidTokenError("Token lacks kid header identifier.")

        # Find matching key in active pools
        target_key = next((k for k in self.keys if k.kid == kid), None)
        if not target_key:
            raise jwt.InvalidTokenError("Signing key (kid) not found in active JWKS.")

        # Get public key PEM format
        public_pem = target_key.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        # Decode and verify
        return jwt.decode(
            token, public_pem, algorithms=["RS256"], audience="api.notedmaam.ai"
        )


# Global JWKS Manager Instance
jwks_manager = JWKSManager()
