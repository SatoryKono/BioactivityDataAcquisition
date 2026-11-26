"""Windows Bronze reference binding for the attested run data root."""

from __future__ import annotations

from collections.abc import Mapping
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


def _bound_bronze_reference(item: object, context: object | None) -> object | None:
    """Resolve a Windows Bronze reference only inside the attested run data root.

    Returns the bound item, the original item when the reference stays on the
    legacy resolution path, or None when an absolute Windows ``bronze_batch``
    reference escapes the attested root and the probe must fail closed.
    """
    if not isinstance(item, dict) or item.get("kind") != "bronze_batch":
        return item
    reference = item.get("path") or item.get("relative_path") or item.get("ref")
    data_root = getattr(context, "data_root", None)
    alias = getattr(context, "trusted_alias_base", None)
    if (
        not isinstance(reference, str)
        or not isinstance(data_root, Path)
        or not isinstance(alias, Path)
    ):
        return item
    windows_path = PureWindowsPath(reference)
    if not windows_path.is_absolute() or ".." in windows_path.parts:
        return item
    native = _native_absolute_artifact(reference)
    try:
        native_available = native is not None and native.is_file()
    except OSError:
        native_available = False
    if native_available:
        return item
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
    return {**item, "path": str(candidate)}


def _rejected_bronze_probe(
    item: Mapping[str, object], index: int
) -> Mapping[str, object]:
    """Fail an absolute Windows Bronze reference that escapes the bound root."""
    ref = f"#/artifacts/{index}"
    name = item.get("name") or item.get("id") or item.get("kind") or f"artifact_{index}"
    return {
        "code": str(name),
        "result": "fail",
        "reason": "artifact_path_escape",
        "evidence_ref": ref,
    }
