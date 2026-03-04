#!/usr/bin/env python3
"""Generate publication-type classification data asset from versioned CSV.

Artifacts:
- Generated Python table:
  src/bioetl/domain/mapping/generated/publication_type_classification_data.py
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
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "configs" / "enums" / "publication_type_classification.csv"
OUTPUT_PATH = (
    PROJECT_ROOT
    / "src"
    / "bioetl"
    / "domain"
    / "mapping"
    / "generated"
    / "publication_type_classification_data.py"
)
MANIFEST_PATH = (
    PROJECT_ROOT / "configs" / "enums" / "publication_type_classification.meta.yaml"
)
DEFAULT_ASSET_VERSION = "v1"

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


def _python_repr(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _build_generated_module(rows: list[Row]) -> str:
    lines: list[str] = []
    lines.append('"""Auto-generated publication type classification data asset.')
    lines.append("")
    lines.append("DO NOT EDIT MANUALLY.")
    lines.append(
        "Run: python scripts/generate_publication_type_classification_artifacts.py"
    )
    lines.append('"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("from typing import Final")
    lines.append("")
    lines.append("_ClassificationRow = tuple[str, str, str, str, str, str, str]")
    lines.append("")
    lines.append("_CLASSIFICATION_TABLE: Final[tuple[_ClassificationRow, ...]] = (")
    for idx, row in enumerate(rows, start=1):
        lines.append(f"    # {idx}")
        lines.append("    (")
        for value in row:
            lines.append(f"        {_python_repr(value)},")
        lines.append("    ),")
    lines.append(")")
    lines.append("")
    lines.append("CLASSIFICATION_TABLE_SIZE: Final[int] = len(_CLASSIFICATION_TABLE)")
    lines.append("")
    lines.append('__all__ = ["_CLASSIFICATION_TABLE", "CLASSIFICATION_TABLE_SIZE"]')
    lines.append("")
    return "\n".join(lines)


def _ruff_format(content: str) -> str:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--stdin-filename",
            "publication_type_classification_data.py",
            "-",
        ],
        input=content,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout
    return content


def _load_asset_version() -> str:
    if not MANIFEST_PATH.exists():
        return DEFAULT_ASSET_VERSION
    payload = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    version = payload.get("asset_version")
    if isinstance(version, str) and version.strip():
        return version.strip()
    return DEFAULT_ASSET_VERSION


def _build_manifest(*, source_hash: str, generated_hash: str, row_count: int) -> str:
    payload = {
        "schema_version": 1,
        "asset": "publication_type_classification",
        "asset_version": _load_asset_version(),
        "source": {
            "path": CSV_PATH.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": source_hash,
            "row_count": row_count,
        },
        "generated": {
            "path": OUTPUT_PATH.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": generated_hash,
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
    generated_content = _ruff_format(_build_generated_module(rows))

    source_hash = _sha256_bytes(CSV_PATH.read_bytes())
    generated_hash = _sha256_bytes(generated_content.encode("utf-8"))
    manifest_content = _build_manifest(
        source_hash=source_hash,
        generated_hash=generated_hash,
        row_count=len(rows),
    )

    stale_generated = _write_if_changed(OUTPUT_PATH, generated_content, args.check)
    stale_manifest = _write_if_changed(MANIFEST_PATH, manifest_content, args.check)

    if args.check and (stale_generated or stale_manifest):
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
