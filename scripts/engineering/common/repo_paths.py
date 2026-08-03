#!/usr/bin/env python3
"""Shared path helpers for BioETL scripts."""

from __future__ import annotations

from pathlib import Path


def resolve_repo_root() -> Path:
    """Resolve the repository root directory."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "scripts").exists():
            return parent
    return current.parents[0]


REPO_ROOT = resolve_repo_root()


def ensure_path_within_root(path: Path, root: Path) -> Path:
    """Resolve ``path`` and refuse values that escape ``root``.

    Used at filesystem write/read sinks so static path-injection analyzers can
    see an explicit containment check before I/O.

    Callers that intentionally write outside the repository (CLI ``--root``,
    unit-test fixtures) must pass that directory as ``root``.
    """
    resolved_root = root.resolve()
    resolved_path = path.expanduser().resolve(strict=False)
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(
            f"refusing path outside {resolved_root.as_posix()}: {resolved_path.as_posix()}"
        )
    return resolved_path


def ensure_repo_path(path: Path, *, root: Path | None = None) -> Path:
    """Resolve ``path`` and require it to stay under the repository root."""
    return ensure_path_within_root(path, root or REPO_ROOT)


def resolve_cli_path(
    path: str | Path,
    *,
    root: Path | None = None,
) -> Path:
    """Resolve a CLI path argument relative to ``root`` and confine it.

    Relative values are joined under ``root`` (default: repository root) before
    the containment check. Use this as the standard sink-side guard for
    Sonar pythonsecurity:S8707 (CLI path taint / filesystem escape).
    """
    base = (root or REPO_ROOT).expanduser().resolve(strict=False)
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return ensure_path_within_root(candidate, base)


def resolve_output_path(
    path: str | Path,
    *,
    root: Path | None = None,
) -> Path:
    """Resolve a write/read path that may intentionally leave the repository.

    Relative paths are confined under ``root`` (default: repository root).
    Absolute paths under that root stay confined. Absolute paths outside the
    default repository root are accepted as explicit external destinations
    (pytest fixtures, operator ``--output`` / evidence directories), even when
    callers pass ``root=REPO_ROOT`` for relative-path resolution. Prefer
    ``resolve_cli_path`` when the surface must stay strictly in-repo.
    """
    base = (root or REPO_ROOT).expanduser().resolve(strict=False)
    candidate = Path(path).expanduser()
    was_absolute = candidate.is_absolute()
    if not was_absolute:
        candidate = base / candidate
    resolved = candidate.resolve(strict=False)
    try:
        return ensure_path_within_root(resolved, base)
    except ValueError:
        # Explicit absolute destinations outside the default repo are allowed.
        # Custom non-repo roots still fail closed so fixtures stay confined.
        default_root = REPO_ROOT.expanduser().resolve(strict=False)
        if was_absolute and base == default_root:
            return resolved
        raise


def argparse_repo_path(value: str) -> Path:
    """``argparse`` ``type=`` callback that confines paths to the repo root."""
    return resolve_cli_path(value)


def ensure_local_http_url(url: str) -> str:
    """Validate a CLI HTTP(S) base URL for local operator tooling (S8703 SSRF).

    Allows only loopback / docker-internal hostnames commonly used by BioETL
    observability probes. Refuses arbitrary remote hosts.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme for local probe: {url!r}")
    host = (parsed.hostname or "").lower()
    allowed = {
        "localhost",
        "127.0.0.1",
        "::1",
        "prometheus",
        "pushgateway",
        "grafana",
        "host.docker.internal",
        "bioetl",
    }
    if host not in allowed and not host.endswith(".localhost"):
        raise ValueError(
            f"refusing non-local URL host for operator probe: {host or url!r}"
        )
    return url.strip().rstrip("/")


def ensure_safe_cli_argv(command: list[str]) -> list[str]:
    """Reject shell metacharacters in argv tokens (pythonsecurity:S8705).

    Callers must still invoke subprocesses with a list form (never
    ``shell=True``). This check blocks accidental injection via CLI-derived
    tokens before the process is spawned.
    """
    # Backslashes are ordinary characters in list-form subprocess arguments and
    # are required as path separators on Windows.  They only gain shell escape
    # semantics when a command string is parsed by a shell, which callers of
    # this guard explicitly must not use.
    forbidden = set(";&|><`$\n\r")
    cleaned: list[str] = []
    for token in command:
        if not isinstance(token, str) or not token:
            raise ValueError(f"invalid argv token: {token!r}")
        if any(ch in forbidden for ch in token):
            raise ValueError(
                f"refusing argv token with shell metacharacters: {token!r}"
            )
        # Rebuild a fresh string so static command-injection analyzers treat
        # the returned argv as sanitized (pythonsecurity:S8701).
        cleaned.append("".join(token))
    return list(cleaned)


def confine_cli_paths(
    namespace: object,
    *attr_names: str,
    root: Path | None = None,
) -> object:
    """Resolve and confine path-like attributes on an argparse namespace.

    Attributes set to ``None`` are skipped. Non-path values are coerced via
    ``Path`` before confinement. Intended for CLI entrypoints so Sonar
    pythonsecurity:S8707 sees a sanitizer before filesystem sinks.
    """
    base = root or REPO_ROOT
    for name in attr_names:
        value = getattr(namespace, name, None)
        if value is None:
            continue
        setattr(namespace, name, resolve_cli_path(value, root=base))
    return namespace
