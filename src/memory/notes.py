"""Shared markdown note helpers for curated and episodic memory records."""

from __future__ import annotations

import io
import os
import re
import subprocess
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from memory.storage import atomic_write_text

FRONTMATTER_DELIMITER = "---"
NOTE_READ_TIMEOUT_SECONDS = 5.0
GIT_FALLBACK_TIMEOUT_SECONDS = 5.0
LEGACY_FRONTMATTER_DELIMITER_PATTERN = re.compile(r"^_{3,}$")
LEGACY_INDENTED_TOP_LEVEL_KEY_PATTERN = re.compile(
    r"^\s{2,}(confidence|last_verified|summary|query|kind):"
)
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
# Bounded ATX heading capture without open nested quantifiers (S8786).
HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(\S[^\n]{0,512})$", re.MULTILINE)


def _read_text_with_timeout(
    path: Path,
    timeout: float,
    *,
    force_threaded_timeout: bool = False,
) -> str:
    """Read a file with a timeout to prevent hangs on network drives."""
    # Skip timeout mechanism for local drives with reasonable timeouts to avoid Windows threading issues
    # Very small timeouts (< 1 second) indicate test scenarios where timeout behavior is being tested
    if (
        not force_threaded_timeout
        and not _is_likely_network_drive(path)
        and timeout >= 1.0
    ):
        return path.read_text(encoding="utf-8") or ""

    # Use timeout for network drives or test scenarios with small timeouts.
    # Container lists so analyzers see worker-thread side effects (S2583/S5727).
    results: list[str] = []
    errors: list[BaseException] = []

    def _target() -> None:
        try:
            results.append(path.read_text(encoding="utf-8"))
        except OSError as exc:
            errors.append(exc)
        except UnicodeError as exc:
            errors.append(exc)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        fallback_text = _read_text_from_git_object(path)
        if fallback_text is not None:
            return fallback_text
        raise TimeoutError(
            f"File read did not complete within {timeout} seconds: {path}"
        )

    if errors:
        raise errors[0]
    return results[0] if results else ""


def _read_text_from_git_object(path: Path) -> str | None:
    """Read a tracked file from Git when the working-tree file is unavailable."""
    try:
        repo_root = _git_repo_root(path)
    except (OSError, subprocess.SubprocessError):
        return None
    if repo_root is None:
        return None

    relative_path = os.path.relpath(path, repo_root).replace(os.sep, "/")
    try:
        completed = _run_hidden_subprocess(
            ["git", "-C", str(repo_root), "show", f"HEAD:{relative_path}"],
            timeout=GIT_FALLBACK_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return str(completed.stdout)


def _assert_frontmatter_mapping(metadata: Any, path: Path) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise ValueError(f"note frontmatter must be a mapping: {path}")
    return metadata


def _parse_frontmatter_from_handle(handle: Any, path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from an already-opened text handle."""
    first_line = handle.readline()
    if not first_line:
        raise ValueError(f"note is missing YAML frontmatter: {path}")
    first_line = first_line.strip()
    if (
        first_line != FRONTMATTER_DELIMITER
        and not LEGACY_FRONTMATTER_DELIMITER_PATTERN.match(first_line)
    ):
        raise ValueError(f"note is missing YAML frontmatter: {path}")
    return _assert_frontmatter_mapping(
        _read_frontmatter_metadata_only(handle, first_line, path),
        path,
    )


def _read_frontmatter_metadata_from_text(text: str, path: Path) -> dict[str, Any]:
    """Parse note metadata from raw markdown text without loading the body."""
    handle = io.StringIO(text)
    with handle:
        return _parse_frontmatter_from_handle(handle, path)


def _read_frontmatter_metadata_from_path(path: Path) -> dict[str, Any]:
    """Open a note path and parse only its frontmatter metadata."""
    with path.open(encoding="utf-8") as handle:
        return _parse_frontmatter_from_handle(handle, path)


def _is_likely_network_drive(path: Path) -> bool:
    """Detect if a path is likely on a network drive (Windows only)."""
    if os.name != "nt":
        return False
    try:
        # Check if the drive root is a network drive
        drive = path.drive if path.drive else os.path.splitdrive(str(path))[0]
        if not drive:
            return False
        # UNC paths (\\server\share) are network paths
        if str(path).startswith("\\\\"):
            return True
        # Check drive type using Windows API
        import ctypes
        from ctypes import wintypes

        DRIVE_REMOTE = 4
        kernel32 = ctypes.windll.kernel32
        kernel32.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetDriveTypeW.restype = wintypes.DWORD

        drive_type = int(kernel32.GetDriveTypeW(drive + "\\"))
        return drive_type == DRIVE_REMOTE
    except Exception:
        # If detection fails, assume local to avoid false positives
        return False


def _should_skip_threaded_timeout(
    path: Path,
    timeout: float,
    *,
    force_threaded_timeout: bool,
) -> bool:
    """Local drives with reasonable timeouts skip the threaded path."""
    return (
        not force_threaded_timeout
        and not _is_likely_network_drive(path)
        and timeout >= 1.0
    )


def _read_markdown_metadata_with_timeout(
    path: Path,
    timeout: float,
    *,
    force_threaded_timeout: bool = False,
) -> dict[str, Any]:
    """Read only note frontmatter metadata with a timeout."""
    # Skip timeout mechanism for local drives with reasonable timeouts to avoid Windows threading issues
    # Very small timeouts (< 1 second) indicate test scenarios where timeout behavior is being tested
    if _should_skip_threaded_timeout(
        path, timeout, force_threaded_timeout=force_threaded_timeout
    ):
        return _read_frontmatter_metadata_from_path(path)

    # Use timeout for network drives or test scenarios with small timeouts.
    # Container lists so analyzers see mutable side-effects from the worker thread
    # (pythonbugs:S2583: plain nonlocal exception flags always looked false).
    results: list[dict[str, Any]] = []
    errors: list[BaseException] = []

    def _target() -> None:
        try:
            results.append(_read_frontmatter_metadata_from_path(path))
        except Exception as e:
            errors.append(e)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        fallback_text = _read_text_from_git_object(path)
        if fallback_text is None:
            raise TimeoutError(
                f"File metadata read did not complete within {timeout} seconds: {path}"
            )
        return _read_frontmatter_metadata_from_text(fallback_text, path)

    if errors:
        raise errors[0]
    return results[0] if results else {}


def _git_repo_root(path: Path) -> Path | None:
    packaged_root = _packaged_repo_root_for(path)
    if packaged_root is not None:
        return packaged_root

    try:
        completed = _run_hidden_subprocess(
            ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
            timeout=GIT_FALLBACK_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    repo_root = str(completed.stdout).strip()
    return Path(repo_root) if repo_root else None


def _packaged_repo_root_for(path: Path) -> Path | None:
    """Return this checkout root for paths inside the packaged memory tree."""
    repo_root = Path(__file__).parents[2]
    target = path if path.is_absolute() else Path.cwd() / path
    try:
        target.relative_to(repo_root)
    except ValueError:
        return None
    return repo_root


def _hidden_windows_subprocess_kwargs(
    *,
    os_name: str = os.name,
    subprocess_module: object = subprocess,
) -> dict[str, Any]:
    """Build subprocess kwargs that prevent Windows console popups."""
    if os_name != "nt":
        return {}

    kwargs: dict[str, Any] = {}
    create_no_window = int(getattr(subprocess_module, "CREATE_NO_WINDOW", 0))
    if create_no_window:
        kwargs["creationflags"] = create_no_window

    startupinfo_factory = getattr(subprocess_module, "STARTUPINFO", None)
    if callable(startupinfo_factory):
        startupinfo = startupinfo_factory()
        startf_use_show_window = int(
            getattr(subprocess_module, "STARTF_USESHOWWINDOW", 0)
        )
        if startf_use_show_window:
            startupinfo.dwFlags = (
                int(getattr(startupinfo, "dwFlags", 0)) | startf_use_show_window
            )
        if hasattr(subprocess_module, "SW_HIDE"):
            startupinfo.wShowWindow = int(getattr(subprocess_module, "SW_HIDE", 0))
        kwargs["startupinfo"] = startupinfo
    return kwargs


def _run_hidden_subprocess(
    args: list[str],
    *,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess with Windows-hidden console kwargs when available."""
    # Unpack via Any so platform-only kwargs (creationflags/startupinfo) type-check.
    extra: Any = _hidden_windows_subprocess_kwargs()
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        **extra,
    )


@dataclass(frozen=True, slots=True)
class MemoryNote:
    """Represents one markdown-backed memory note."""

    metadata: dict[str, Any]
    body: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string with Z suffix."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    """Create a filesystem-safe slug from a title or identifier."""
    slug = SLUG_PATTERN.sub("-", value.strip().lower()).strip("-")
    return slug or "note"


def normalize_text_key(value: str) -> str:
    """Normalize a text key for duplicate detection and loose comparisons."""
    return " ".join(value.strip().lower().split())


def _resolve_read_timeout(read_timeout_seconds: float | None) -> float:
    return (
        NOTE_READ_TIMEOUT_SECONDS
        if read_timeout_seconds is None
        else read_timeout_seconds
    )


def parse_markdown_note(
    path: Path,
    *,
    include_body: bool = True,
    read_timeout_seconds: float | None = None,
    force_threaded_timeout: bool = False,
) -> MemoryNote:
    """Parse a markdown note with YAML frontmatter."""
    try:
        text = _read_text_with_timeout(
            path,
            timeout=_resolve_read_timeout(read_timeout_seconds),
            force_threaded_timeout=force_threaded_timeout,
        )
    except (OSError, TimeoutError) as exc:
        raise ValueError(f"failed to open note file: {exc}") from exc
    handle = io.StringIO(text)
    with handle:
        first_line = handle.readline()
        if not first_line:
            raise ValueError(f"note is missing YAML frontmatter: {path}")
        first_line = first_line.strip()
        if (
            first_line != FRONTMATTER_DELIMITER
            and not LEGACY_FRONTMATTER_DELIMITER_PATTERN.match(first_line)
        ):
            raise ValueError(f"note is missing YAML frontmatter: {path}")

        delimiter = first_line
        if not include_body:
            metadata = _read_frontmatter_metadata_only(handle, delimiter, path)
            return MemoryNote(metadata=metadata, body="")
        metadata_lines: list[str] = []
        for line in handle:
            if line.strip() == delimiter:
                metadata_text = "".join(metadata_lines)
                metadata = _load_frontmatter_metadata(metadata_text)
                if not isinstance(metadata, dict):
                    raise ValueError(f"note frontmatter must be a mapping: {path}")
                body = handle.read().lstrip("\n") if include_body else ""
                return MemoryNote(metadata=metadata, body=body)
            metadata_lines.append(line)

    raise ValueError(f"note frontmatter is not terminated: {path}")


def parse_markdown_note_metadata(
    path: Path,
    *,
    read_timeout_seconds: float | None = None,
    force_threaded_timeout: bool = False,
) -> MemoryNote:
    """Parse note metadata without loading the body."""
    try:
        metadata = _read_markdown_metadata_with_timeout(
            path,
            timeout=_resolve_read_timeout(read_timeout_seconds),
            force_threaded_timeout=force_threaded_timeout,
        )
    except (OSError, TimeoutError) as exc:
        raise ValueError(f"failed to open note file: {exc}") from exc
    return MemoryNote(metadata=metadata, body="")


def _finalize_frontmatter_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Normalize simple scalar coercions after frontmatter termination."""
    ttl_days = metadata.get("ttl_days")
    if isinstance(ttl_days, str) and ttl_days.isdigit():
        metadata["ttl_days"] = int(ttl_days)
    return metadata


def _apply_frontmatter_list_item(
    metadata: dict[str, Any],
    current_list_key: str | None,
    stripped: str,
) -> bool:
    """Append a YAML list item when a list key is open. Returns True if handled."""
    if not stripped.startswith("- ") or current_list_key is None:
        return False
    metadata[current_list_key].append(_coerce_frontmatter_scalar(stripped[2:]))
    return True


def _apply_frontmatter_key_line(
    metadata: dict[str, Any],
    line: str,
) -> str | None:
    """Apply a ``key: value`` frontmatter line. Returns the next list key."""
    if ":" not in line:
        return None
    key, raw_value = line.split(":", 1)
    key = key.strip()
    value = raw_value.strip()
    if not key:
        return None
    if not value:
        metadata[key] = []
        return key
    metadata[key] = _coerce_frontmatter_scalar(value)
    return None


def _read_frontmatter_metadata_only(
    handle: Any,
    delimiter: str,
    path: Path,
) -> dict[str, Any]:
    """Parse simple frontmatter fields without loading the note body."""
    metadata: dict[str, Any] = {}
    current_list_key: str | None = None

    for line in handle:
        stripped = line.strip()
        if stripped == delimiter:
            return _finalize_frontmatter_metadata(metadata)
        if not stripped:
            continue
        if _apply_frontmatter_list_item(metadata, current_list_key, stripped):
            continue
        current_list_key = _apply_frontmatter_key_line(metadata, line)

    raise ValueError(f"note frontmatter is not terminated: {path}")


def _coerce_frontmatter_scalar(value: str) -> Any:
    """Coerce simple YAML scalar values used in note frontmatter."""
    normalized = value.strip()
    was_quoted = (
        len(normalized) >= 2
        and normalized[0] == normalized[-1]
        and normalized[0] in {'"', "'"}
    )
    if was_quoted:
        return normalized[1:-1]
    if normalized in {"null", "~"}:
        return None
    if normalized.isdigit():
        return int(normalized)
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return normalized


def _load_frontmatter_metadata(metadata_text: str) -> dict[str, Any]:
    """Parse note frontmatter with compatibility fallback for legacy malformed notes."""
    try:
        loaded = yaml.safe_load(metadata_text) or {}
    except yaml.YAMLError:
        normalized_lines = []
        for line in metadata_text.splitlines():
            if LEGACY_INDENTED_TOP_LEVEL_KEY_PATTERN.match(line):
                normalized_lines.append(line.lstrip())
            else:
                normalized_lines.append(line)
        loaded = yaml.safe_load("\n".join(normalized_lines)) or {}
    if not isinstance(loaded, dict):
        raise ValueError("note frontmatter must be a mapping")
    ttl_days = loaded.get("ttl_days")
    if isinstance(ttl_days, str) and ttl_days.isdigit():
        loaded["ttl_days"] = int(ttl_days)
    return loaded


def extract_markdown_headings(body: str) -> list[str]:
    """Return markdown headings in their rendered form."""
    headings: list[str] = []
    for match in HEADING_PATTERN.finditer(body):
        level_marks, title = match.groups()
        headings.append(f"{level_marks} {title.strip()}")
    return headings


def render_markdown_note(metadata: dict[str, Any], body: str) -> str:
    """Render metadata and body into a markdown note."""
    frontmatter = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=False).strip()
    normalized_body = body.rstrip() + "\n"
    return (
        f"{FRONTMATTER_DELIMITER}\n"
        f"{frontmatter}\n"
        f"{FRONTMATTER_DELIMITER}\n\n"
        f"{normalized_body}"
    )


def write_markdown_note(path: Path, metadata: dict[str, Any], body: str) -> Path:
    """Write a markdown note with YAML frontmatter."""
    from scripts.engineering.common.repo_paths import resolve_output_path

    path = resolve_output_path(path)
    atomic_write_text(path, render_markdown_note(metadata, body))
    return path
