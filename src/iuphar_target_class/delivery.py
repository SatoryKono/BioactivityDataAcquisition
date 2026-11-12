"""Write a batch result beside its source. A collision does not replace a file."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .policy import PLAN_VERSION
from .stage0.io import canonical_json_bytes

_FORBIDDEN = set('\\/:*?"<>|')
_TEMP_PREFIX = ".iuphar-"
_COLUMNS = (
    "input_row_id",
    "legacy_iuphar_class",
    "iuphar_class",
    "effective_class",
)


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """One attempt to write a result next to the source file."""

    source_name: str
    normalized_name: str
    directory: str
    written: bool
    diagnostic: str | None
    manifest_name: str | None


def sanitize(value: str) -> str:
    """Replace path separators, controls, and the reserved filename characters."""
    return "".join(
        "_" if ord(char) < 32 or char in _FORBIDDEN else char for char in value
    )


def result_names(
    source_name: str,
    *,
    snapshot_id: str,
    rules_version: str,
    run_id: str,
) -> tuple[str, str]:
    """Return the raw template name and the sanitized file name."""
    source = Path(source_name)
    suffix = source.suffix or ".csv"
    stem = source.name[: -len(source.suffix)] if source.suffix else source.name
    raw = f"{stem}__targetclass_{snapshot_id}_{rules_version}_{run_id}{suffix}"
    safe_suffix = "." + sanitize(suffix[1:])
    safe = (
        f"{sanitize(stem)}__targetclass_{sanitize(snapshot_id)}_"
        f"{sanitize(rules_version)}_{sanitize(run_id)}{safe_suffix}"
    )
    return raw, safe


def output_row(row: Mapping[str, str]) -> dict[str, str]:
    """Copy the old class aside. A local class never fills ``iuphar_class``."""
    legacy = row.get("legacy_iuphar_class") or row.get("old_iuphar_class") or ""
    return {
        "input_row_id": row.get("input_row_id") or "",
        "legacy_iuphar_class": legacy,
        "iuphar_class": row.get("iuphar_class") or "",
        "effective_class": row.get("effective_class") or "",
    }


def contract_document() -> dict[str, object]:
    """Published contract. The type mapping version stays unapproved."""
    return {
        "biological_accuracy_accepted": False,
        "columns": list(_COLUMNS),
        "mapping_status": "не утверждено",
        "mapping_version": None,
        "name_template": "<source>__targetclass_<snapshot_id>_<rules_version>_<run_id>.<ext>",
        "rules_version": PLAN_VERSION,
        "schema_version": None,
    }


def run_batch(
    source: Path,
    *,
    root: Path,
    snapshot_id: str,
    rules_version: str,
    run_id: str,
) -> DeliveryResult:
    """Read one CSV inside ``root`` and write the result beside that file."""
    source = _path_inside_root(source, root)
    _, safe_name = result_names(
        source.name,
        snapshot_id=snapshot_id,
        rules_version=rules_version,
        run_id=run_id,
    )
    directory = source.parent
    destination = directory / safe_name
    manifest_name = f"{safe_name}.manifest.json"
    if len(manifest_name.encode("utf-8")) > 255:
        # Keep the public CSV template; only its companion name needs bounding.
        digest = hashlib.sha256(safe_name.encode("utf-8")).hexdigest()
        manifest_name = f"targetclass-{digest}.manifest.json"
    manifest_path = directory / manifest_name
    if _directory_entry(destination) or _directory_entry(manifest_path):
        return DeliveryResult(
            source.name, safe_name, str(directory), False, "name_collision", None
        )
    rows = _read_rows(source, root=root)
    payload = _csv_bytes(tuple(output_row(row) for row in rows))
    manifest = canonical_json_bytes(
        {
            "directory": str(directory),
            "normalized_name": safe_name,
            "rules_version": rules_version,
            "run_id": run_id,
            "schema_version": None,
            "snapshot_id": snapshot_id,
            "source_name": source.name,
        }
    )
    published = _publish_name(destination, root)
    if not _create_new(destination, payload, root=root):
        return DeliveryResult(
            source.name, safe_name, str(directory), False, "name_collision", None
        )
    manifest_created = False
    try:
        manifest_created = _create_new(manifest_path, manifest, root=root)
    finally:
        if not manifest_created:
            published.unlink(missing_ok=True)
    if not manifest_created:
        return DeliveryResult(
            source.name, safe_name, str(directory), False, "name_collision", None
        )
    return DeliveryResult(
        source.name, safe_name, str(directory), True, None, manifest_name
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI wrapper. It uses the same writer as ``run_batch``."""
    parser = argparse.ArgumentParser(prog="iuphar-target-class")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--rules", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_batch(
        args.source,
        root=args.root,
        snapshot_id=args.snapshot,
        rules_version=args.rules,
        run_id=args.run_id,
    )
    if result.diagnostic:
        sys.stdout.write(result.diagnostic + "\n")
        return 2
    sys.stdout.write(result.normalized_name + "\n")
    return 0


def _read_rows(source: Path, *, root: Path) -> tuple[dict[str, str], ...]:
    """Read a CSV only after its resolved path stays inside ``root``.

    The opened path is rebuilt from the resolved root and the relative parts,
    so the file handle is not the original CLI path object.
    """
    resolved = _path_inside_root(source, root)
    base = root.resolve()
    relative = resolved.relative_to(base)
    opened = base.joinpath(*relative.parts)
    with opened.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "input_row_id" not in reader.fieldnames:
            raise ValueError("CSV requires an input_row_id header")
        return tuple(dict(row) for row in reader)


def _path_inside_root(path: Path, root: Path) -> Path:
    """Resolve ``path`` and reject it when it leaves ``root``.

    The check matches stage-0 publication: ``resolve`` then
    ``is_relative_to``, before any byte is read.
    """
    root_resolved = root.resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(root_resolved):
        message = "path escapes root"
        raise ValueError(message)
    return resolved


def _csv_bytes(rows: tuple[Mapping[str, str], ...]) -> bytes:
    """Serialize with the csv module so commas and quotes stay one field."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_COLUMNS)
    for row in rows:
        writer.writerow(tuple(row[column] for column in _COLUMNS))
    return buffer.getvalue().encode("utf-8")


def _directory_entry(path: Path) -> bool:
    """True for any directory entry, including a dangling symlink."""
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _publish_name(path: Path, root: Path) -> Path:
    """Return the final name inside ``root`` without following that name.

    The parent is resolved for the containment check. The last component stays
    as given, so publication cannot replace the target of a symlink.
    """
    root_resolved = root.resolve()
    parent = path.parent.resolve()
    if path.name in {"", ".", ".."} or not parent.is_relative_to(root_resolved):
        message = "path escapes root"
        raise ValueError(message)
    return parent / path.name


def _create_new(path: Path, payload: bytes, *, root: Path) -> bool:
    """Create ``path`` only when that name is absent. An existing entry is kept."""
    destination = _publish_name(path, root)
    if _directory_entry(destination):
        return False
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=_TEMP_PREFIX,
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        try:
            os.link(temporary, destination)
        except FileExistsError:
            return False
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


if __name__ == "__main__":
    raise SystemExit(main())
