from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash suitable for storing in users.password_hash."""
    if not password:
        raise ValueError("Password cannot be empty.")
    password_bytes = password.encode("utf-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a complete bcrypt hash string."""
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False
