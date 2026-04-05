#!/usr/bin/env python3
"""Generate or check the canonical VCR metadata catalog artifact."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import yaml

CATALOG_SCHEMA_VERSION = 1
DEFAULT_VCR_ROOT = Path("tests/fixtures/vcr")
DEFAULT_OUTPUT = Path("reports/quality/vcr-metadata-catalog.json")


@dataclass(frozen=True)
class CassetteCatalogRow:
    """Single cassette inventory row for the canonical metadata catalog."""

    provider: str
    cassette_rel_path: str
    cassette_extension: str
    has_metadata_sidecar: bool
    metadata_rel_path: str | None
    metadata_status: str


@dataclass
class ProviderCatalogSummary:
    """Aggregated provider-level metadata coverage summary."""

    cassette_count: int = 0
    metadata_sidecar_count: int = 0
    without_metadata_count: int = 0
    metadata_coverage_percent: float = 0.0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or check the canonical VCR metadata catalog artifact."
    )
    parser.add_argument(
        "--vcr-root",
        default=str(DEFAULT_VCR_ROOT),
        help="Root VCR cassette directory.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the tracked artifact differs from generated output.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write the generated artifact to disk.",
    )
    return parser.parse_args()


def _metadata_path_for(cassette_path: Path) -> Path:
    return cassette_path.with_name(f"{cassette_path.stem}_meta.yaml")


def _is_cassette_file(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in {".yaml", ".yml"}
        and not (path.name.endswith("_meta.yaml") or path.name.endswith("_meta.yml"))
    )


def _metadata_status(metadata_payload: object) -> str:
    if not isinstance(metadata_payload, dict):
        return "missing"
    value = metadata_payload.get("metadata_status")
    if isinstance(value, str) and value:
        return value
    return "present"


def _load_metadata_payload(path: Path) -> object | None:
    if not path.exists():
        return None
    return cast(object | None, yaml.safe_load(path.read_text(encoding="utf-8")))


def iter_catalog_rows(vcr_root: Path) -> list[CassetteCatalogRow]:
    """Build deterministic catalog rows for all tracked cassette files."""
    rows: list[CassetteCatalogRow] = []
    if not vcr_root.exists():
        return rows

    cassette_paths = sorted(
        (path for path in vcr_root.rglob("*") if _is_cassette_file(path)),
        key=lambda path: (path.as_posix().lower(), path.as_posix()),
    )

    for cassette_path in cassette_paths:
        rel_path = cassette_path.as_posix()
        parts = cassette_path.relative_to(vcr_root).parts
        provider = parts[0] if parts else "unknown"
        metadata_path = _metadata_path_for(cassette_path)
        metadata_payload = _load_metadata_payload(metadata_path)
        rows.append(
            CassetteCatalogRow(
                provider=provider,
                cassette_rel_path=rel_path,
                cassette_extension=cassette_path.suffix.lower(),
                has_metadata_sidecar=metadata_path.exists(),
                metadata_rel_path=metadata_path.as_posix()
                if metadata_path.exists()
                else None,
                metadata_status=_metadata_status(metadata_payload),
            )
        )

    return rows


def build_catalog(vcr_root: Path) -> dict[str, object]:
    """Build the canonical JSON catalog payload."""
    rows = iter_catalog_rows(vcr_root)
    provider_summary: dict[str, ProviderCatalogSummary] = {}

    for row in rows:
        summary = provider_summary.setdefault(row.provider, ProviderCatalogSummary())
        summary.cassette_count += 1
        if row.has_metadata_sidecar:
            summary.metadata_sidecar_count += 1
        else:
            summary.without_metadata_count += 1

    for summary in provider_summary.values():
        cassette_count = summary.cassette_count
        metadata_sidecar_count = summary.metadata_sidecar_count
        coverage_percent = (
            round((metadata_sidecar_count / cassette_count) * 100.0, 2)
            if cassette_count
            else 0.0
        )
        summary.metadata_coverage_percent = coverage_percent

    return {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "catalog_kind": "vcr_metadata_catalog",
        "vcr_root": vcr_root.as_posix(),
        "totals": {
            "cassette_count": len(rows),
            "metadata_sidecar_count": sum(
                1 for row in rows if row.has_metadata_sidecar
            ),
            "provider_count": len(provider_summary),
        },
        "providers": {
            provider: asdict(summary)
            for provider, summary in sorted(provider_summary.items())
        },
        "cassettes": [asdict(row) for row in rows],
    }


def render_catalog_json(vcr_root: Path) -> str:
    """Render the canonical JSON artifact."""
    return json.dumps(build_catalog(vcr_root), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    args = _parse_args()
    vcr_root = Path(args.vcr_root)
    output_path = Path(args.output)
    rendered = render_catalog_json(vcr_root)

    if args.check:
        if not output_path.exists():
            print(f"[report-vcr-metadata-catalog] missing artifact: {output_path}")
            return 1
        actual = output_path.read_text(encoding="utf-8")
        if actual != rendered:
            print(
                "[report-vcr-metadata-catalog] FAIL: tracked artifact drifted from generated output"
            )
            return 1
        print("[report-vcr-metadata-catalog] PASS: artifact is up to date")
        return 0

    if args.update or not output_path.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"[report-vcr-metadata-catalog] wrote {output_path}")
        return 0

    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
