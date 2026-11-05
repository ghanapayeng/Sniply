import secrets
import string

BASE62_ALPHABET = string.digits + string.ascii_letters  # 62 characters: 0-9, a-z, A-Z


def generate_short_code(length: int = 7) -> str:
    """Generate a cryptographically random, collision-resistant Base62 string."""
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))


def generate_session_token() -> str:
    """Generate a high-entropy random URL-safe session token (32 bytes = 256 bits)."""
    return secrets.token_urlsafe(32)


def generate_api_key() -> str:
    """Generate an API key with standard prefix: snip_<random>"""
    return f"snip_{secrets.token_urlsafe(32)}"

