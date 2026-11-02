from urllib.parse import urlparse


def _qudt_identifier_from_uri(value: str) -> str | None:
    parsed = urlparse(value.strip())
    hostname = parsed.hostname.casefold() if parsed.hostname is not None else None
    if hostname == "qudt.org" and parsed.path.startswith("/vocab/unit/"):
        return parsed.path.rsplit("/", maxsplit=1)[-1]
    return None


def _legacy_qudt_identifier_from_uri(value: str) -> str | None:
    parsed = urlparse(value.strip())
    hostname = parsed.hostname.casefold() if parsed.hostname is not None else None
    if hostname != "www.openphacts.org":
        return None
    if parsed.path.casefold() == "/units/nanomolar":
        return "NanoMOL-PER-L"
    return None

