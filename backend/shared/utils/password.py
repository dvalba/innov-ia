"""Password hashing with the standard library only (T-003, plan decision D10).

Hash format: `innov$<salt_hex>$<sha256(salt + password)>`.

NOTE (plan D10): `hashlib.sha256` with salt covers the MVP scope. Documented
as a hardening risk for production (e.g. bcrypt/argon2) should the dependency
policy change.
"""

import hashlib
import secrets

_SALT_BYTES = 16
_HASH_ALGORITHM = "sha256"
_PREFIX = "innov"


def hash_password(password: str) -> str:
    """Derives the hash (salt + sha256) of the password."""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.new(_HASH_ALGORITHM)
    digest.update(salt)
    digest.update(password.encode("utf-8"))
    return f"{_PREFIX}${salt.hex()}${digest.hexdigest()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verifies the password against the hash; `False` on invalid format."""
    parts = hashed.split("$")
    if len(parts) != 3 or parts[0] != _PREFIX:
        return False
    try:
        salt = bytes.fromhex(parts[1])
    except ValueError:
        return False
    digest = hashlib.new(_HASH_ALGORITHM)
    digest.update(salt)
    digest.update(password.encode("utf-8"))
    return secrets.compare_digest(digest.hexdigest(), parts[2])


def generate_temp_password(length: int = 14) -> str:
    """Generates a high-entropy temporary password (RF-17)."""
    alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    base = "".join(secrets.choice(alphabet) for _ in range(length))
    return base + secrets.choice("!@#_-")
