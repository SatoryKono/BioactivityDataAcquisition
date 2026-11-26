"""Windows Bronze reference binding for the attested run data root."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path, PureWindowsPath


def _native_absolute_artifact(reference: str) -> Path | None:
    """Return the recorded path when it is absolute on this machine.

    A Windows report replayed on its originating host keeps verifying the
    recorded Bronze file itself instead of shadowing it with the bound copy.
    """
    raw = Path(reference)
    if not raw.is_absolute():
        return None
    return raw


def _probe_with_bronze_binding(
    item: object,
    context: object | None,
    root: Path,
    index: int,
    probe: Callable[[object, Path], Mapping[str, object]],
) -> Mapping[str, object]:
    """Verify the recorded file or its copy under the attested Bronze root."""
    if not isinstance(item, dict) or item.get("kind") != "bronze_batch":
        return probe(item, root)
    reference = item.get("path") or item.get("relative_path") or item.get("ref")
    data_root = getattr(context, "data_root", None)
    alias = getattr(context, "trusted_alias_base", None)
    if (
        not isinstance(reference, str)
        or not isinstance(data_root, Path)
        or not isinstance(alias, Path)
    ):
        return probe(item, root)
    windows_path = PureWindowsPath(reference)
    if not windows_path.is_absolute():
        return probe(item, root)
    if ".." in windows_path.parts:
        return _rejected_bronze_probe(item, index)

    native = _native_absolute_artifact(reference)
    try:
        if native is not None and native.is_file():
            return probe({**item, "path": str(native)}, root)
    except OSError:
        # Retry only an unavailable file. A digest mismatch is evidence.
        pass

    bound = _bound_bronze_path(windows_path, data_root, alias)
    if bound is None:
        return _rejected_bronze_probe(item, index)
    bronze_root, relative_path = bound
    try:
        return probe({**item, "path": str(relative_path)}, bronze_root)
    except OSError:
        return _rejected_bronze_probe(item, index, reason="artifact_unreadable")


def _bound_bronze_path(
    windows_path: PureWindowsPath, data_root: Path, alias: Path
) -> tuple[Path, Path] | None:
    """Bind the recorded suffix to the resolved and contained Bronze directory."""
    try:
        trusted_base = alias.resolve()
        bound_root = data_root.resolve()
        relative_root = bound_root.relative_to(trusted_base)
        prefix = (trusted_base.name, *relative_root.parts, "output", "bronze")
        directory = windows_path.parts[:-4]
        if PureWindowsPath(*directory[-len(prefix) :]) != PureWindowsPath(*prefix):
            return None
        bronze_root = (bound_root / "output" / "bronze").resolve()
        candidate = bronze_root.joinpath(*windows_path.parts[-4:]).resolve()
    except (OSError, ValueError):
        return None
    if not bronze_root.is_relative_to(bound_root) or not candidate.is_relative_to(
        bronze_root
    ):
        return None
    return bronze_root, candidate.relative_to(bronze_root)


def _rejected_bronze_probe(
    item: Mapping[str, object], index: int, *, reason: str = "artifact_path_escape"
) -> Mapping[str, object]:
    """Report a rejected or unreadable Windows Bronze reference."""
    ref = f"#/artifacts/{index}"
    name = item.get("name") or item.get("id") or item.get("kind") or f"artifact_{index}"
    return {
        "code": str(name),
        "result": "fail",
        "reason": reason,
        "evidence_ref": ref,
    }
