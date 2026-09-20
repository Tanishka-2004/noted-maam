import hashlib

import httpx
import zxcvbn
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Initialize Argon2id password hasher with specified enterprise criteria
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hashes a password using Argon2id algorithm."""
    return ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against an Argon2id hash."""
    try:
        return ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False


def check_password_strength(password: str) -> tuple[bool, str]:
    """Checks password complexity using zxcvbn library.

    Requires length >= 10 and zxcvbn strength score >= 3.
    """
    if len(password) < 10:
        return False, "Password must be at least 10 characters long."

    res = zxcvbn.zxcvbn(password)
    score = res.get("score", 0)
    feedback = res.get("feedback", {})
    warning = feedback.get("warning", "")
    suggestions = feedback.get("suggestions", [])

    if score < 3:
        msg = warning if warning else "Password is too weak or predictable."
        if suggestions:
            msg += f" Suggestions: {' '.join(suggestions)}"
        return False, msg

    return True, "Password meets criteria."


async def check_password_breached(password: str) -> bool:
    """Verifies if password is listed in HaveIBeenPwned API using
    k-Anonymity range check.
    """
    sha1_hex = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix = sha1_hex[:5]
    suffix = sha1_hex[5:]

    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    headers = {"User-Agent": "NotedMaam-Auth-Service"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                # Fallback to False to prevent blocking signups on HIBP outages
                return False

            lines = response.text.splitlines()
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    hash_suffix, count = parts[0], int(parts[1])
                    if hash_suffix == suffix:
                        return count > 0
    except Exception as e:
        # Fallback to False on timeout or network exceptions
        import logging

        logging.getLogger("app.security").warning(
            "HaveIBeenPwned API check failed: %s. Skipping check.", e
        )
        return False

    return False
