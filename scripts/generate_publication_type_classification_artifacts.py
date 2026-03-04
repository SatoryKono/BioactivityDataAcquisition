#!/usr/bin/env python3
"""Generate publication-type classification artifacts from versioned CSV.

Artifacts:
- Versioned JSON asset (source of truth for giant table payload):
  configs/enums/publication_type_classification.asset.<version>.json
- Generated compact Python lookup module:
  src/bioetl/domain/mapping/generated/publication_type_classification_data.py
- Hash manifest:
  configs/enums/publication_type_classification.meta.yaml

Usage:
    python scripts/generate_publication_type_classification_artifacts.py
    python scripts/generate_publication_type_classification_artifacts.py --check
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import subprocess
import sys
import zlib
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
ASSET_FILE_STEM = "publication_type_classification.asset"

Row = tuple[str, str, str, str, str, str, str]
_DASH = "—"
_TABLE_ENCODE_WRAP = 88


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


def _build_provider_row_index(rows: list[Row], *, column: int) -> dict[str, int]:
    """Build provider lookup key -> 1-based row index mapping."""
    mapping: dict[str, int] = {}
    for row_idx, row in enumerate(rows, start=1):
        raw_key = row[column]
        if raw_key == _DASH:
            continue
        key = raw_key.rstrip("*").lower()
        if key not in mapping:
            mapping[key] = row_idx
    return mapping


def _encode_rows_blob(rows: list[Row]) -> str:
    """Encode full classification rows to compact deterministic blob."""
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    compressed = zlib.compress(payload, level=9)
    encoded = base64.b85encode(compressed).decode("ascii")
    return encoded


def _chunk_text(text: str, chunk_size: int) -> list[str]:
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _emit_row_index_dict(lines: list[str], name: str, mapping: dict[str, int]) -> None:
    lines.append(f"{name}: Final[dict[str, int]] = {{")
    for key, row_idx in mapping.items():
        lines.append(f"    {_python_repr(key)}: {row_idx},")
    lines.append("}")
    lines.append("")


def _build_generated_module(rows: list[Row], *, asset_json_rel_path: str) -> str:
    lines: list[str] = []
    lines.append('"""Auto-generated publication type classification data asset.')
    lines.append("")
    lines.append("DO NOT EDIT MANUALLY.")
    lines.append(
        "Run: python scripts/generate_publication_type_classification_artifacts.py"
    )
    lines.append(f"Asset source: {asset_json_rel_path}")
    lines.append('"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("import base64")
    lines.append("import json")
    lines.append("import zlib")
    lines.append("from typing import Final, cast")
    lines.append("")
    lines.append("_ClassificationRow = tuple[str, str, str, str, str, str, str]")
    lines.append("")
    lines.append("_EntryCore = tuple[str, str, str]")
    lines.append("")
    lines.append("_ENTRY_CORE: Final[tuple[_EntryCore, ...]] = (")
    for unified_type, subclass, class_code, *_rest in rows:
        lines.append(
            "    ("
            f"{_python_repr(unified_type)}, "
            f"{_python_repr(subclass)}, "
            f"{_python_repr(class_code)}"
            "),"
        )
    lines.append(")")
    lines.append("")
    _emit_row_index_dict(
        lines,
        "_OPENALEX_ROW_INDEX",
        _build_provider_row_index(rows, column=3),
    )
    _emit_row_index_dict(
        lines,
        "_CROSSREF_ROW_INDEX",
        _build_provider_row_index(rows, column=4),
    )
    _emit_row_index_dict(
        lines,
        "_PUBMED_ROW_INDEX",
        _build_provider_row_index(rows, column=5),
    )
    _emit_row_index_dict(
        lines,
        "_S2_ROW_INDEX",
        _build_provider_row_index(rows, column=6),
    )

    lines.append("_TABLE_B85: Final[str] = (")
    for chunk in _chunk_text(_encode_rows_blob(rows), _TABLE_ENCODE_WRAP):
        lines.append(f"    {_python_repr(chunk)}")
    lines.append(")")
    lines.append("")
    lines.append(
        "def _decode_classification_table() -> tuple[_ClassificationRow, ...]:"
    )
    lines.append(
        "    payload = zlib.decompress(base64.b85decode(_TABLE_B85.encode('ascii')))"
    )
    lines.append("    raw_rows = json.loads(payload.decode('utf-8'))")
    lines.append("    return tuple(")
    lines.append("        cast(_ClassificationRow, tuple(row))")
    lines.append("        for row in raw_rows")
    lines.append("    )")
    lines.append("")
    lines.append(
        "_CLASSIFICATION_TABLE: Final[tuple[_ClassificationRow, ...]] = "
        "_decode_classification_table()"
    )
    lines.append("CLASSIFICATION_TABLE_SIZE: Final[int] = len(_ENTRY_CORE)")
    lines.append("")
    lines.append("__all__ = [")
    lines.append('    "CLASSIFICATION_TABLE_SIZE",')
    lines.append('    "_CLASSIFICATION_TABLE",')
    lines.append('    "_CROSSREF_ROW_INDEX",')
    lines.append('    "_ENTRY_CORE",')
    lines.append('    "_OPENALEX_ROW_INDEX",')
    lines.append('    "_PUBMED_ROW_INDEX",')
    lines.append('    "_S2_ROW_INDEX",')
    lines.append("]")
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
    generated_hash: str,
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
    asset_version = _load_asset_version()
    asset_json_path = _resolve_asset_json_path(asset_version)
    asset_json_content = _build_json_asset(rows=rows, asset_version=asset_version)

    generated_content = _ruff_format(
        _build_generated_module(
            rows,
            asset_json_rel_path=asset_json_path.relative_to(PROJECT_ROOT).as_posix(),
        )
    )

    source_hash = _sha256_bytes(CSV_PATH.read_bytes())
    artifact_hash = _sha256_bytes(asset_json_content.encode("utf-8"))
    generated_hash = _sha256_bytes(generated_content.encode("utf-8"))
    manifest_content = _build_manifest(
        source_hash=source_hash,
        artifact_hash=artifact_hash,
        artifact_path=asset_json_path,
        generated_hash=generated_hash,
        row_count=len(rows),
    )

    stale_asset = _write_if_changed(asset_json_path, asset_json_content, args.check)
    stale_generated = _write_if_changed(OUTPUT_PATH, generated_content, args.check)
    stale_manifest = _write_if_changed(MANIFEST_PATH, manifest_content, args.check)

    if args.check and (stale_asset or stale_generated or stale_manifest):
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
