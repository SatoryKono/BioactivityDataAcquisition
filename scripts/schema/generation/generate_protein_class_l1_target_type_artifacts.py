#!/usr/bin/env python3
"""Generate ChEMBL protein-class L1 target-type mapping artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = PROJECT_ROOT / "configs" / "enums" / "protein_class_l1_target_type.csv"
MANIFEST_PATH = (
    PROJECT_ROOT / "configs" / "enums" / "protein_class_l1_target_type.meta.yaml"
)
DEFAULT_ASSET_VERSION = "v1"
ASSET_FILE_STEM = "protein_class_l1_target_type.asset"

Row = tuple[str, str, bool, str]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_rows(path: Path) -> list[Row]:
    rows: list[Row] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {
            "source_l1_raw",
            "canonical_l1",
            "counts_for_target_type",
            "notes",
        }
        if set(reader.fieldnames or ()) != expected:
            raise ValueError(f"{path} must have columns {sorted(expected)}")
        for line_no, row in enumerate(reader, start=2):
            raw = (row.get("source_l1_raw") or "").strip()
            canonical = (row.get("canonical_l1") or "").strip()
            counts_raw = (row.get("counts_for_target_type") or "").strip().lower()
            notes = (row.get("notes") or "").strip()
            if not raw or not canonical:
                raise ValueError(f"{path}:{line_no} raw and canonical are required")
            if counts_raw not in {"true", "false"}:
                raise ValueError(
                    f"{path}:{line_no} counts_for_target_type must be true/false"
                )
            rows.append((raw, canonical, counts_raw == "true", notes))
    return rows


def _load_asset_version() -> str:
    if not MANIFEST_PATH.exists():
        return DEFAULT_ASSET_VERSION
    payload = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    version = payload.get("asset_version")
    if isinstance(version, str) and version.strip():
        return version.strip()
    return DEFAULT_ASSET_VERSION


def _resolve_asset_json_path(asset_version: str) -> Path:
    return (
        PROJECT_ROOT / "configs" / "enums" / (f"{ASSET_FILE_STEM}.{asset_version}.json")
    )


def _build_json_asset(*, rows: list[Row], asset_version: str) -> str:
    payload = {
        "schema_version": 1,
        "asset": "protein_class_l1_target_type",
        "asset_version": asset_version,
        "mapping_version": "protein_class_l1_map_v1",
        "columns": [
            "source_l1_raw",
            "canonical_l1",
            "counts_for_target_type",
            "notes",
        ],
        "rows": rows,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=False, indent=2) + "\n"


def _build_manifest(
    *,
    source_hash: str,
    artifact_hash: str,
    artifact_path: Path,
    row_count: int,
) -> str:
    payload = {
        "schema_version": 2,
        "asset": "protein_class_l1_target_type",
        "asset_version": _load_asset_version(),
        "source": {
            "path": CSV_PATH.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": source_hash,
            "row_count": row_count,
        },
        "artifact": {
            "path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": artifact_hash,
            "row_count": row_count,
        },
    }
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)


def _write_if_changed(path: Path, content: str, check: bool) -> bool:
    desired = content.encode("utf-8")
    current = path.read_bytes() if path.exists() else None
    if current == desired:
        print(f"OK    {path.relative_to(PROJECT_ROOT)}")
        return False
    if check:
        print(f"STALE {path.relative_to(PROJECT_ROOT)}", file=sys.stderr)
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    print(f"WROTE {path.relative_to(PROJECT_ROOT)}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if generated protein-class mapping artifacts are stale",
    )
    args = parser.parse_args()

    rows = _load_rows(CSV_PATH)
    asset_version = _load_asset_version()
    asset_json_path = _resolve_asset_json_path(asset_version)
    asset_json = _build_json_asset(rows=rows, asset_version=asset_version)
    source_hash = _sha256_bytes(CSV_PATH.read_bytes())
    artifact_hash = _sha256_bytes(asset_json.encode("utf-8"))
    manifest = _build_manifest(
        source_hash=source_hash,
        artifact_hash=artifact_hash,
        artifact_path=asset_json_path,
        row_count=len(rows),
    )

    stale_asset = _write_if_changed(asset_json_path, asset_json, args.check)
    stale_manifest = _write_if_changed(MANIFEST_PATH, manifest, args.check)
    if args.check and (stale_asset or stale_manifest):
        print(
            "\nProtein class L1 target type artifacts are stale. "
            "Run: python scripts/schema/generation/generate_protein_class_l1_target_type_artifacts.py",
            file=sys.stderr,
        )
        return 1

    print("\nProtein class L1 target type artifacts are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
