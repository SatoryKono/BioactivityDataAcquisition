"""Shared VCR replay configuration helpers for test suites."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import suppress
from fnmatch import fnmatch
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlparse

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    import pytest

DEFAULT_VCR_MATCH_ON: tuple[str, ...] = (
    "method",
    "scheme",
    "host",
    "port",
    "path",
    "query",
)
QUERY_IGNORE_EMAIL_MATCH_ON: tuple[str, ...] = (
    "method",
    "scheme",
    "host",
    "port",
    "path",
    "query_ignore_email",
)

_GIT_LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"
_VCR_IGNORED_QUERY_KEYS = {"email", "api_key", "key"}
_TRANSIENT_HTML_CONTENT_TYPE = "text/html"
STRICT_LFS_POINTER_BLOCKER_PATTERNS: tuple[str, ...] = (
    "tests/fixtures/vcr/*/provider_contract_*.yaml",
    "tests/fixtures/vcr/*/test_*_full_cycle.yaml",
    "tests/fixtures/vcr/*/test_*_full_run.yaml",
)


_PROVIDER_VCR_DIR_HINTS: tuple[str, ...] = (
    "chembl",
    "crossref",
    "openalex",
    "pubchem",
    "pubmed",
    "semanticscholar",
    "uniprot",
)


def ensure_default_vcr_record_mode() -> None:
    """Set deterministic replay-only VCR mode unless the caller overrides it."""
    os.environ.setdefault("VCR_RECORD_MODE", "none")


def is_vcr_recording_mode(record_mode: str | None = None) -> bool:
    """Return whether the effective VCR mode is allowed to refresh cassette data."""
    effective_mode = (record_mode or os.environ.get("VCR_RECORD_MODE", "none")).lower()
    if effective_mode in {"all", "new_episodes", "once"}:
        return True
    argv_text = " ".join(sys.argv).lower()
    return any(
        token in argv_text
        for token in (
            "--vcr-record=all",
            "--vcr-record=new_episodes",
            "--vcr-record=once",
            "--vcr-record-mode=all",
            "--vcr-record-mode=new_episodes",
            "--vcr-record-mode=once",
        )
    )


def is_git_lfs_pointer(path: Path) -> bool:
    """Return whether one path points to a Git LFS placeholder file."""
    try:
        with path.open("rb") as handle:
            return handle.read(len(_GIT_LFS_POINTER_PREFIX)) == _GIT_LFS_POINTER_PREFIX
    except OSError:
        return False


def is_strict_lfs_pointer_blocked_cassette(
    path: Path,
    *,
    repo_root: Path | None = None,
) -> bool:
    """Return whether an unresolved pointer must fail rather than skip replay."""
    root = repo_root or Path.cwd()
    try:
        normalized = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        normalized = path.as_posix()
    return any(
        fnmatch(normalized, pattern) for pattern in STRICT_LFS_POINTER_BLOCKER_PATTERNS
    )


def resolve_requested_cassette_path(
    request: pytest.FixtureRequest,
) -> Path | None:
    """Resolve the cassette path without opening it through vcrpy."""
    try:
        vcr_config_value = request.getfixturevalue("vcr_config")
        cassette_dir = vcr_config_value.get("cassette_library_dir")
        if cassette_dir is None:
            cassette_dir = request.getfixturevalue("vcr_cassette_dir")
        cassette_name = str(request.getfixturevalue("vcr_cassette_name"))
    except Exception:  # pragma: no cover - fixture lookup behavior is pytest-owned
        return None

    if not cassette_name.endswith(".yaml"):
        cassette_name = f"{cassette_name}.yaml"

    cassette_path = Path(cassette_name)
    if cassette_path.is_absolute():
        return cassette_path
    return Path(str(cassette_dir)) / cassette_path


def build_base_vcr_config(
    *,
    cassette_library_dir: Path | str | None = None,
    match_on: Sequence[str] = DEFAULT_VCR_MATCH_ON,
    decode_compressed_response: bool = False,
    filter_headers: Sequence[str] | None = None,
    filter_query_parameters: Sequence[str] | None = None,
    ignore_localhost: bool = False,
    record_mode: str | None = None,
) -> dict[str, object]:
    """Build one shared VCR config payload with deterministic defaults."""
    config: dict[str, object] = {
        "record_mode": record_mode or os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": list(match_on),
    }
    if cassette_library_dir is not None:
        config["cassette_library_dir"] = str(cassette_library_dir)
    if decode_compressed_response:
        config["decode_compressed_response"] = True
    before_record_request = _build_before_record_request_sanitizer(
        filter_headers=filter_headers,
        filter_query_parameters=filter_query_parameters,
    )
    if before_record_request is not None:
        config["before_record_request"] = before_record_request
    config["before_record_response"] = _build_before_record_response_filter()
    if ignore_localhost:
        config["ignore_localhost"] = True
    return config


def _normalize_vcr_replacements(
    values: Sequence[str] | None,
) -> tuple[tuple[str, object | None], ...]:
    """Coerce one VCR replacement list into explicit (key, replacement) pairs."""
    if values is None:
        return ()
    return tuple((value, None) for value in values)


def _build_before_record_request_sanitizer(
    *,
    filter_headers: Sequence[str] | None,
    filter_query_parameters: Sequence[str] | None,
) -> Callable[[Any], Any] | None:
    """Build one defensive sanitizer for VCR request replay/record hooks.

    Some adapter transports expose request-like objects that do not fully satisfy
    vcrpy's built-in filter expectations. In those cases, vcrpy's synthesized
    before_record_request chain can raise TypeError during test setup. This
    helper preserves header/query secret filtering for standard VCR Request
    objects while degrading to a no-op for malformed or provider-specific
    request surfaces.
    """
    header_replacements = _normalize_vcr_replacements(filter_headers)
    query_replacements = _normalize_vcr_replacements(filter_query_parameters)
    if not header_replacements and not query_replacements:
        return None

    def before_record_request(request: Any) -> Any:
        if request is None:
            return None

        try:
            from vcr import filters
        except Exception:  # pragma: no cover - vcr import is environment-owned
            return request

        sanitized = request
        if header_replacements and hasattr(sanitized, "headers"):
            with suppress(AttributeError, KeyError, TypeError, ValueError):
                sanitized = filters.replace_headers(
                    sanitized,
                    replacements=header_replacements,
                )

        if query_replacements and hasattr(sanitized, "uri"):
            with suppress(AttributeError, KeyError, TypeError, ValueError):
                sanitized = filters.replace_query_parameters(
                    sanitized,
                    replacements=query_replacements,
                )
        return sanitized

    return before_record_request


def _build_before_record_response_filter() -> Callable[[Any], Any]:
    """Skip transient upstream HTML error pages during cassette recording."""

    def before_record_response(response: Any) -> Any:
        if _is_transient_html_server_error(response):
            return None
        return response

    return before_record_response


def _is_transient_html_server_error(response: Any) -> bool:
    """Return whether one VCR response looks like a transient upstream HTML 5xx."""
    if not isinstance(response, Mapping):
        return False

    status = response.get("status")
    if not isinstance(status, Mapping):
        return False

    try:
        raw_status_code = status.get("code")
        if not isinstance(raw_status_code, (int, str)):
            return False
        status_code = int(raw_status_code)
    except (TypeError, ValueError):
        return False

    if status_code < 500:
        return False

    headers = response.get("headers")
    if not isinstance(headers, Mapping):
        return False

    content_type = _get_header_value(headers, "content-type")
    return _TRANSIENT_HTML_CONTENT_TYPE in content_type.lower()


def _get_header_value(headers: Mapping[Any, Any], name: str) -> str:
    """Return one normalized VCR header value."""
    for key, value in headers.items():
        if str(key).lower() != name:
            continue
        if isinstance(value, (list, tuple)):
            return str(value[0]) if value else ""
        return str(value)
    return ""


def query_ignore_email(request_1: Any, request_2: Any) -> bool:
    """Custom VCR matcher that ignores email and api_key query parameters."""
    return _strip_credential_query(request_1.uri) == _strip_credential_query(
        request_2.uri
    )


def build_cassette_dir(*, fixtures_root: Path, provider_dir: str) -> Path:
    """Return one provider-specific cassette directory under the shared fixtures root."""
    cassette_dir = fixtures_root / provider_dir
    cassette_dir.mkdir(parents=True, exist_ok=True)
    return cassette_dir


def resolve_cassette_name(
    *,
    node_name: str | None,
    class_name: str | None = None,
    overrides: Mapping[str, str] | None = None,
) -> str:
    """Normalize the cassette file name, honoring class-qualified overrides first."""
    if node_name is None:
        msg = "pytest node name must be defined for VCR cassette resolution"
        raise RuntimeError(msg)
    resolved_overrides = overrides or {}
    qualified_name = f"{class_name}.{node_name}" if class_name else node_name
    qualified_override = resolved_overrides.get(qualified_name)
    if qualified_override is not None:
        return qualified_override
    return resolved_overrides.get(node_name, node_name)


def infer_provider_cassette_dir(
    *,
    node_name: str,
    module_path: str | None,
    overrides: Mapping[str, str],
    default: str = "chembl",
) -> str:
    """Resolve one provider cassette directory from explicit overrides or module stem."""
    explicit = overrides.get(node_name)
    if explicit is not None:
        return explicit
    if module_path is None:
        return default
    module_stem = Path(module_path).stem
    for hint in _PROVIDER_VCR_DIR_HINTS:
        if hint in module_stem:
            return hint
    return default


def _strip_credential_query(uri: str) -> list[tuple[str, str]]:
    """Return query params excluding credentials for VCR matching."""
    query_params = parse_qsl(urlparse(uri).query, keep_blank_values=True)
    return [
        (key, value)
        for key, value in query_params
        if key.lower() not in _VCR_IGNORED_QUERY_KEYS
    ]
