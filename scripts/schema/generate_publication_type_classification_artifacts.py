#!/usr/bin/env python3
"""Generate publication-type classification artifacts from versioned CSV.

Artifacts:
- Versioned JSON asset (runtime data source):
  configs/enums/publication_type_classification.asset.<version>.json
- Hash manifest:
  configs/enums/publication_type_classification.meta.yaml

Usage:
    python scripts/generate_publication_type_classification_artifacts.py
    python scripts/generate_publication_type_classification_artifacts.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "configs" / "enums" / "publication_type_classification.csv"
MANIFEST_PATH = (
    PROJECT_ROOT / "configs" / "enums" / "publication_type_classification.meta.yaml"
)
DEFAULT_ASSET_VERSION = "v1"
ASSET_FILE_STEM = "publication_type_classification.asset"

Row = tuple[str, str, str, str, str, str, str]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_rows(path: Path) -> list[Row]:
    rows: list[Row] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)  # header
        for line_no, row in enumerate(reader, start=2):
            if len(row) < 8:
                raise ValueError(
                    f"{path}:{line_no} must have 8 columns, got {len(row)}"
                )
            rows.append(
                (
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                )
            )
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
    filename = f"{ASSET_FILE_STEM}.{asset_version}.json"
    return PROJECT_ROOT / "configs" / "enums" / filename


def _build_json_asset(*, rows: list[Row], asset_version: str) -> str:
    payload = {
        "schema_version": 1,
        "asset": "publication_type_classification",
        "asset_version": asset_version,
        "columns": [
            "unified_type",
            "subclass",
            "class_code",
            "openalex_type",
            "crossref_type",
            "pubmed_type",
            "semanticscholar_type",
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
        "asset": "publication_type_classification",
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
    desired_bytes = content.encode("utf-8")
    current_bytes = path.read_bytes() if path.exists() else None
    if current_bytes == desired_bytes:
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
        "--check", action="store_true", help="fail if artifacts are stale"
    )
    args = parser.parse_args()

    rows = _load_rows(CSV_PATH)
    asset_version = _load_asset_version()
    asset_json_path = _resolve_asset_json_path(asset_version)
    asset_json_content = _build_json_asset(rows=rows, asset_version=asset_version)

    source_hash = _sha256_bytes(CSV_PATH.read_bytes())
    artifact_hash = _sha256_bytes(asset_json_content.encode("utf-8"))
    manifest_content = _build_manifest(
        source_hash=source_hash,
        artifact_hash=artifact_hash,
        artifact_path=asset_json_path,
        row_count=len(rows),
    )

    stale_asset = _write_if_changed(asset_json_path, asset_json_content, args.check)
    stale_manifest = _write_if_changed(MANIFEST_PATH, manifest_content, args.check)

    if args.check and (stale_asset or stale_manifest):
        print(
            "\nPublication type artifacts are stale. "
            "Run: python scripts/generate_publication_type_classification_artifacts.py",
            file=sys.stderr,
        )
        return 1

    print("\nPublication type classification artifacts are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
