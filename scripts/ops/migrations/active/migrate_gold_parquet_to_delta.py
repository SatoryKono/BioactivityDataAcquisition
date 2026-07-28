#!/usr/bin/env python3
"""Migrate one local legacy Gold Parquet dataset to Delta without data loss.

The command is dry-run by default and never mutates the source.  ``--apply``
writes an isolated staging table, validates row parity, and atomically promotes
the staging directory to the requested target path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

MIGRATION_MANIFEST = "_gold_contract_v1_1_migration.json"
TIMESTAMP_FIELDS = frozenset(
    {
        "captured_at",
        "completed_at_utc",
        "lineage_created_at",
        "reset_at",
        "started_at_utc",
        "timestamp",
        "write_completed_at",
        "write_started_at",
    }
)


@dataclass(frozen=True, slots=True)
class SourceInventory:
    """Immutable source evidence used for planning and idempotence."""

    file_count: int
    total_bytes: int
    row_count: int
    schema: str
    sha256: str


@dataclass(frozen=True, slots=True)
class MigrationResult:
    """Machine-readable result for one migration invocation."""

    status: str
    source: str
    target: str
    inventory: SourceInventory
    metadata_file_count: int


def _local_path(raw_path: str | Path) -> Path:
    path = Path(raw_path).expanduser()
    if "://" in str(raw_path):
        raise ValueError("Gold migration supports local filesystem paths only")
    return path.resolve()


def _discover_parquet_files(source: Path) -> tuple[Path, ...]:
    if source.is_file() and source.suffix.lower() == ".parquet":
        return (source,)
    if not source.is_dir():
        raise ValueError(f"Gold source does not exist: {source}")
    files = tuple(sorted(path for path in source.rglob("*.parquet") if path.is_file()))
    if not files:
        raise ValueError(f"Gold source contains no Parquet files: {source}")
    return files


def _discover_metadata_files(source: Path) -> tuple[Path, ...]:
    search_root = source if source.is_dir() else source.parent
    return tuple(
        sorted(path for path in search_root.rglob("*metadata.y*ml") if path.is_file())
    )


def _source_dataset(source: Path, parquet_files: tuple[Path, ...]):
    import pyarrow.dataset as pyarrow_dataset

    partition_root = source if source.is_dir() else source.parent
    return pyarrow_dataset.dataset(
        [str(path) for path in parquet_files],
        format="parquet",
        partitioning="hive",
        partition_base_dir=str(partition_root),
    )


def _content_fingerprint(source: Path, parquet_files: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    base_path = source if source.is_dir() else source.parent
    for path in parquet_files:
        digest.update(path.relative_to(base_path).as_posix().encode("utf-8"))
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def build_source_inventory(source: Path) -> SourceInventory:
    """Build deterministic row/schema/content evidence for a Parquet source."""
    parquet_files = _discover_parquet_files(source)
    dataset = _source_dataset(source, parquet_files)
    return SourceInventory(
        file_count=len(parquet_files),
        total_bytes=sum(path.stat().st_size for path in parquet_files),
        row_count=dataset.count_rows(),
        schema=str(dataset.schema),
        sha256=_content_fingerprint(source, parquet_files),
    )


_UTC_OFFSET_SUFFIX = "+00:00"


def _normalize_timestamp(value: object, *, assume_naive_utc: bool) -> object:
    if value is None:
        return None
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", _UTC_OFFSET_SUFFIX))
        except ValueError as exc:
            raise ValueError(f"Invalid metadata timestamp: {value!r}") from exc
    else:
        raise ValueError(f"Metadata timestamp must be ISO-8601: {value!r}")
    if timestamp.tzinfo is None:
        if not assume_naive_utc:
            raise ValueError(
                "Naive legacy metadata timestamp requires --assume-naive-utc"
            )
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(UTC).isoformat().replace(_UTC_OFFSET_SUFFIX, "Z")


def _normalize_metadata_value(
    value: object,
    *,
    assume_naive_utc: bool,
    field_name: str = "",
) -> object:
    if field_name in TIMESTAMP_FIELDS:
        return _normalize_timestamp(value, assume_naive_utc=assume_naive_utc)
    if isinstance(value, dict):
        return {
            str(key): _normalize_metadata_value(
                item,
                assume_naive_utc=assume_naive_utc,
                field_name=str(key),
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _normalize_metadata_value(
                item,
                assume_naive_utc=assume_naive_utc,
                field_name=field_name,
            )
            for item in value
        ]
    return value


def normalize_metadata_contract(
    value: object,
    *,
    assume_naive_utc: bool,
    field_name: str = "",
) -> object:
    """Normalize timestamps recursively and apply the v1.1 contract at the root."""
    normalized = _normalize_metadata_value(
        value,
        assume_naive_utc=assume_naive_utc,
        field_name=field_name,
    )
    if field_name or not isinstance(normalized, dict):
        return normalized
    normalized["version"] = "1.1"
    output_ext = normalized.get("output_ext")
    if not isinstance(output_ext, dict):
        output_ext = {}
        normalized["output_ext"] = output_ext
    output_ext["format"] = "delta"
    return normalized


def _copy_normalized_metadata(
    source: Path,
    target: Path,
    metadata_files: tuple[Path, ...],
    *,
    assume_naive_utc: bool,
) -> None:
    source_root = source if source.is_dir() else source.parent
    for metadata_path in metadata_files:
        payload = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
        normalized = normalize_metadata_contract(
            payload,
            assume_naive_utc=assume_naive_utc,
        )
        relative_path = metadata_path.relative_to(source_root)
        destination = target / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            yaml.safe_dump(normalized, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def _manifest_payload(
    source: Path,
    target: Path,
    inventory: SourceInventory,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "contract_version": "1.1",
        "source": str(source),
        "target": str(target),
        "source_inventory": asdict(inventory),
        "completed_at_utc": datetime.now(UTC).isoformat().replace(_UTC_OFFSET_SUFFIX, "Z"),
    }


def _validate_existing_target(target: Path, inventory: SourceInventory) -> bool:
    from deltalake import DeltaTable

    manifest_path = target / MIGRATION_MANIFEST
    if not (target / "_delta_log").is_dir() or not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_inventory = manifest.get("source_inventory", {})
    if not isinstance(source_inventory, dict):
        return False
    row_count = DeltaTable(str(target)).to_pyarrow_dataset().count_rows()
    return (
        source_inventory.get("sha256") == inventory.sha256
        and source_inventory.get("row_count") == inventory.row_count
        and row_count == inventory.row_count
    )


def migrate_gold_table(
    source_path: str | Path,
    target_path: str | Path,
    *,
    apply: bool = False,
    assume_naive_utc: bool = False,
    partition_by: tuple[str, ...] = (),
) -> MigrationResult:
    """Plan or apply a lossless, source-preserving Gold migration."""
    source = _local_path(source_path)
    target = _local_path(target_path)
    if source == target:
        raise ValueError("Source and target must be different paths")
    parquet_files = _discover_parquet_files(source)
    metadata_files = _discover_metadata_files(source)
    inventory = build_source_inventory(source)
    result_kwargs = {
        "source": str(source),
        "target": str(target),
        "inventory": inventory,
        "metadata_file_count": len(metadata_files),
    }
    if not apply:
        return MigrationResult(status="planned", **result_kwargs)
    if target.exists():
        if _validate_existing_target(target, inventory):
            return MigrationResult(status="already_applied", **result_kwargs)
        raise ValueError(f"Target already exists and is not this migration: {target}")

    staging = target.with_name(f".{target.name}.gold-v1-1-staging")
    if staging.exists():
        raise ValueError(f"Staging path already exists: {staging}")
    target.parent.mkdir(parents=True, exist_ok=True)

    from deltalake import DeltaTable, write_deltalake

    table = _source_dataset(source, parquet_files).to_table()
    write_deltalake(
        str(staging),
        table,
        mode="error",
        partition_by=list(partition_by) or None,
    )
    migrated_rows = DeltaTable(str(staging)).to_pyarrow_dataset().count_rows()
    if migrated_rows != inventory.row_count:
        raise RuntimeError(
            f"Gold migration row mismatch: {inventory.row_count} != {migrated_rows}"
        )
    _copy_normalized_metadata(
        source,
        staging,
        metadata_files,
        assume_naive_utc=assume_naive_utc,
    )
    (staging / MIGRATION_MANIFEST).write_text(
        json.dumps(
            _manifest_payload(source, target, inventory),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    staging.replace(target)
    return MigrationResult(status="applied", **result_kwargs)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Legacy Gold Parquet path.")
    parser.add_argument("--target", required=True, help="New empty Delta table path.")
    parser.add_argument("--apply", action="store_true", help="Apply the migration.")
    parser.add_argument(
        "--assume-naive-utc",
        action="store_true",
        help="Treat legacy naive metadata timestamps as UTC during migration.",
    )
    parser.add_argument(
        "--partition-by",
        action="append",
        default=[],
        help="Delta partition column; repeat for multiple columns.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = migrate_gold_table(
        args.source,
        args.target,
        apply=args.apply,
        assume_naive_utc=args.assume_naive_utc,
        partition_by=tuple(args.partition_by),
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
