"""Password hashing and session tokens. Standard library only: hashlib.scrypt, secrets, hmac."""

import base64
import hashlib
import hmac
import secrets

# OWASP's scrypt option N=2^14, r=8, p=5 (16 MiB per hash, ~175 ms here). The parameters are
# stored in each hash, so raising them later still verifies older hashes.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 5
SALT_BYTES = 16
KEY_BYTES = 32
TOKEN_BYTES = 32
_MAXMEM = 64 * 1024 * 1024


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=_MAXMEM,
                          dklen=KEY_BYTES)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def hash_password(password: str) -> str:
    """'scrypt$n$r$p$salt$key', with a fresh random salt for every hash."""
    salt = secrets.token_bytes(SALT_BYTES)
    key = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(key)}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time comparison. A malformed stored hash verifies nothing; it never raises."""
    try:
        scheme, n, r, p, salt, key = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(key, validate=True)
        actual = _scrypt(password, base64.b64decode(salt, validate=True), int(n), int(r), int(p))
    except (ValueError, TypeError, MemoryError):
        return False
    return hmac.compare_digest(actual, expected)


# Verified against when no account matches, so an unknown email costs the same time as a
# wrong password.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def new_session_token() -> str:
    """The raw token: only ever sent to the browser in the HttpOnly cookie."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def token_hash(token: str) -> str:
    """What the database stores instead of the token (hex SHA-256)."""
    return hashlib.sha256(token.encode()).hexdigest()
