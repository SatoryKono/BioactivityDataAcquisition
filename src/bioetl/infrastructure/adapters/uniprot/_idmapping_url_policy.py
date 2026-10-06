"""Trust policy for UniProt ID-mapping redirect and pagination URLs."""

from __future__ import annotations

from urllib.parse import unquote, urljoin, urlsplit


def _origin(url: str) -> tuple[str, str, int]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("invalid UniProt ID mapping base URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("userinfo is forbidden in UniProt ID mapping URLs")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid port in UniProt ID mapping URL") from exc
    effective_port = port or (443 if parsed.scheme == "https" else 80)
    return parsed.scheme, parsed.hostname.casefold(), effective_port


def trusted_idmapping_url(base_url: str, candidate: str) -> str:
    """Resolve and validate one same-origin, ID-mapping-scoped URL."""
    base = urlsplit(base_url)
    if base.query or base.fragment:
        raise ValueError("query and fragment are forbidden in ID mapping base URL")
    joined = urljoin(f"{base_url.rstrip('/')}/", candidate)
    parsed = urlsplit(joined)
    if parsed.fragment or _origin(joined) != _origin(base_url):
        raise ValueError("untrusted UniProt ID mapping URL")

    decoded_path = unquote(parsed.path)
    if "\\" in decoded_path or ".." in decoded_path.split("/"):
        raise ValueError("untrusted UniProt ID mapping path")
    allowed_prefix = f"{base.path.rstrip('/')}/idmapping/"
    if not decoded_path.startswith(allowed_prefix):
        raise ValueError("URL is outside the UniProt ID mapping API")
    return joined
