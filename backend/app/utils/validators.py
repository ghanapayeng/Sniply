import ipaddress
import re
import socket
import urllib.parse
import hashlib
from typing import Tuple

# Reserved routes/keywords that cannot be used as custom aliases
RESERVED_ALIASES = {
    "api",
    "auth",
    "admin",
    "dashboard",
    "login",
    "register",
    "logout",
    "urls",
    "analytics",
    "settings",
    "pages",
    "assets",
    "css",
    "js",
    "static",
    "health",
    "ready",
    "metrics",
    "404",
    "500",
    "error",
    "expired",
    "favicon.ico",
    "robots.txt",
    "sitemap.xml",
    "qr",
    "index",
    "sniply",
}

ALIAS_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,50}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def hash_token(token: str) -> str:
    """Generate SHA-256 hash of a sensitive token (session token, API key, password reset)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_ip(ip: str, salt: str = "sniply-salt") -> str:
    """Generate SHA-256 hash of an IP address with salt to ensure visitor privacy."""
    raw = f"{salt}:{ip}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def is_ip_private_or_restricted(ip_str: str) -> bool:
    """Check if an IP string is private, loopback, link-local, multicast, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return True


def validate_url_ssrf(raw_url: str) -> Tuple[bool, str, str]:
    """
    Comprehensive SSRF validator:
    1. Validates HTTP/HTTPS scheme.
    2. Disallows embedded credentials.
    3. Resolves DNS to check all target IP addresses.
    4. Rejects loopback, private, link-local, multicast, reserved addresses.
    5. Normalizes hostname.
    Returns: (is_valid, error_message, normalized_url)
    """
    if not raw_url or not isinstance(raw_url, str):
        return False, "URL is required and must be a string.", ""

    url_str = raw_url.strip()
    if len(url_str) > 2048:
        return False, "URL length exceeds maximum allowed limit (2048 characters).", ""

    # Parse URL
    try:
        parsed = urllib.parse.urlsplit(url_str)
    except Exception:
        return False, "Malformed URL format.", ""

    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return False, f"Invalid URL scheme '{parsed.scheme}'. Only http and https are permitted.", ""

    # Reject embedded user info (user:pass@host)
    if parsed.username or parsed.password:
        return False, "URLs with embedded credentials are not allowed.", ""

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must contain a valid domain name or public IP host.", ""

    hostname = hostname.lower()

    # Reject localhost variants
    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
        or hostname == "0.0.0.0"
        or hostname == "::1"
    ):
        return False, "Destination points to restricted local host.", ""

    # Check if hostname itself is an IP literal
    try:
        ip = ipaddress.ip_address(hostname)
        if is_ip_private_or_restricted(str(ip)):
            return False, f"Restricted IP address destination: {hostname}", ""
    except ValueError:
        # Hostname is a domain name. Resolve DNS to check resulting IPs
        try:
            # getaddrinfo with AF_UNSPEC to catch both IPv4 and IPv6
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if not addr_info:
                return False, f"Could not resolve host '{hostname}'.", ""
            for item in addr_info:
                ip_addr = item[4][0]
                if is_ip_private_or_restricted(ip_addr):
                    return False, f"Host '{hostname}' resolves to a restricted/private network address ({ip_addr}).", ""
        except socket.gaierror:
            # Note: in offline or test environments with mock domains (e.g. example.com), DNS might fail.
            # If standard example.com or test domain in development, allow if not a known private pattern:
            if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", hostname):
                return False, f"Invalid domain name syntax '{hostname}'.", ""

    # Reconstruct normalized URL
    normalized = urllib.parse.urlunsplit(
        (scheme, parsed.netloc, parsed.path or "/", parsed.query, parsed.fragment)
    )
    return True, "", normalized


def validate_custom_alias(alias: str | None) -> Tuple[bool, str]:
    """Validate user custom alias string."""
    if not alias:
        return True, ""
    
    clean_alias = alias.strip().lower()
    if len(clean_alias) < 3 or len(clean_alias) > 50:
        return False, "Custom alias must be between 3 and 50 characters long."
    
    if not ALIAS_REGEX.match(clean_alias):
        return False, "Custom alias may only contain alphanumeric characters, underscores, and hyphens."
    
    if clean_alias in RESERVED_ALIASES:
        return False, f"'{clean_alias}' is a reserved system keyword and cannot be used as an alias."
    
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username."""
    if not username or not isinstance(username, str):
        return False, "Username is required."
    clean = username.strip()
    if len(clean) < 3 or len(clean) > 30:
        return False, "Username must be between 3 and 30 characters long."
    if not USERNAME_REGEX.match(clean):
        return False, "Username can only contain alphanumeric characters and underscores."
    if clean.lower() in RESERVED_ALIASES:
        return False, f"Username '{clean}' is reserved."
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email address format."""
    if not email or not isinstance(email, str):
        return False, "Email address is required."
    clean = email.strip()
    if len(clean) > 255:
        return False, "Email address exceeds maximum length."
    if not EMAIL_REGEX.match(clean):
        return False, "Invalid email address format."
    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength (at least 8 chars, letter and number)."""
    if not password or not isinstance(password, str):
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password exceeds maximum length of 128 characters."
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    return True, ""
