#!/usr/bin/env python3
"""Generate or check the canonical VCR metadata catalog artifact."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from functools import cache
from pathlib import Path
from typing import cast

import yaml

CATALOG_SCHEMA_VERSION = 1
DEFAULT_VCR_ROOT = Path("tests/fixtures/vcr")
DEFAULT_OUTPUT = Path("reports/quality/vcr-metadata-catalog.json")
REACHABILITY_SCAN_ROOTS = (Path("tests"),)
RF013_HEALTH_CASE_PATTERN = re.compile(
    r"^rf013_(?P<provider>[a-z0-9_]+)_health_case_\d+$"
)
RF013_HEALTH_CASE_OWNER = Path("tests/integration/adapters/vcr_rebalance_support.py")


@dataclass(frozen=True)
class CassetteCatalogRow:
    """Single cassette inventory row for the canonical metadata catalog."""

    provider: str
    scenario_stem: str
    cassette_rel_path: str
    cassette_extension: str
    has_metadata_sidecar: bool
    metadata_rel_path: str | None
    metadata_status: str
    reachability_status: str
    reachability_owner_paths: list[str]


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


def _load_existing_metadata_payload(path: Path) -> object | None:
    return cast(object | None, yaml.safe_load(path.read_text(encoding="utf-8")))


def _is_reachability_scan_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if "fixtures" in path.parts:
        return False
    return path.suffix.lower() == ".py"


def _iter_reachability_scan_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for root in REACHABILITY_SCAN_ROOTS:
        scan_root = repo_root / root
        if not scan_root.exists():
            continue
        files.extend(
            path
            for path in scan_root.rglob("*.py")
            if _is_reachability_scan_file(path)
        )
    return sorted(files, key=lambda path: path.as_posix().lower())


def _read_scan_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _build_reachability_scan_texts(
    repo_root: Path,
) -> list[tuple[str, str]]:
    return list(_build_reachability_scan_texts_cached(repo_root.as_posix()))


@cache
def _build_reachability_scan_texts_cached(repo_root: str) -> tuple[tuple[str, str], ...]:
    root = Path(repo_root)
    return [
        (path.relative_to(root).as_posix(), _read_scan_text(path))
        for path in _iter_reachability_scan_files(root)
    ]


def _direct_reference_owner_paths(
    *,
    cassette_path: Path,
    vcr_root: Path,
    scan_texts: list[tuple[str, str]],
) -> list[str]:
    rel_to_vcr = cassette_path.relative_to(vcr_root).as_posix()
    tokens = {
        cassette_path.name,
        cassette_path.stem,
        rel_to_vcr,
        f"tests/fixtures/vcr/{rel_to_vcr}",
    }
    owners: list[str] = []
    for relative_path, text in scan_texts:
        if any(token in text for token in tokens):
            owners.append(relative_path)
    return owners


def _generated_reference_owner_paths(
    *,
    cassette_path: Path,
    repo_root: Path,
) -> list[str]:
    if not RF013_HEALTH_CASE_PATTERN.match(cassette_path.stem):
        return []
    owner = repo_root / RF013_HEALTH_CASE_OWNER
    return [RF013_HEALTH_CASE_OWNER.as_posix()] if owner.exists() else []


def _reachability_status_and_owners(
    *,
    cassette_path: Path,
    metadata_path: Path,
    repo_root: Path,
    vcr_root: Path,
    scan_files: list[tuple[str, str]],
) -> tuple[str, list[str]]:
    direct_owners = _direct_reference_owner_paths(
        cassette_path=cassette_path,
        vcr_root=vcr_root,
        scan_texts=scan_files,
    )
    if direct_owners:
        return "direct_reference", direct_owners

    generated_owners = _generated_reference_owner_paths(
        cassette_path=cassette_path,
        repo_root=repo_root,
    )
    if generated_owners:
        return "generated_reference", generated_owners

    if metadata_path.exists():
        return "metadata_review_required", [metadata_path.as_posix()]
    return "unowned", []


def iter_catalog_rows(vcr_root: Path) -> list[CassetteCatalogRow]:
    """Build deterministic catalog rows for all tracked cassette files."""
    rows: list[CassetteCatalogRow] = []
    if not vcr_root.exists():
        return rows
    repo_root = vcr_root.resolve().parents[2]
    scan_files = _build_reachability_scan_texts(repo_root)

    cassette_paths = sorted(
        (path for path in vcr_root.rglob("*") if _is_cassette_file(path)),
        key=lambda path: (path.as_posix().lower(), path.as_posix()),
    )
    metadata_payloads = {
        path: _load_existing_metadata_payload(path)
        for path in vcr_root.rglob("*")
        if path.is_file() and path.name.endswith(("_meta.yaml", "_meta.yml"))
    }

    for cassette_path in cassette_paths:
        rel_path = cassette_path.as_posix()
        parts = cassette_path.relative_to(vcr_root).parts
        provider = parts[0] if parts else "unknown"
        metadata_path = _metadata_path_for(cassette_path)
        has_metadata_sidecar = metadata_path in metadata_payloads
        metadata_payload = metadata_payloads.get(metadata_path)
        reachability_status, reachability_owner_paths = _reachability_status_and_owners(
            cassette_path=cassette_path,
            metadata_path=metadata_path,
            repo_root=repo_root,
            vcr_root=vcr_root,
            scan_files=scan_files,
        )
        rows.append(
            CassetteCatalogRow(
                provider=provider,
                scenario_stem=cassette_path.stem,
                cassette_rel_path=rel_path,
                cassette_extension=cassette_path.suffix.lower(),
                has_metadata_sidecar=has_metadata_sidecar,
                metadata_rel_path=metadata_path.as_posix()
                if has_metadata_sidecar
                else None,
                metadata_status=_metadata_status(metadata_payload),
                reachability_status=reachability_status,
                reachability_owner_paths=reachability_owner_paths,
            )
        )

    return rows


def build_catalog(vcr_root: Path) -> dict[str, object]:
    """Build the canonical JSON catalog payload."""
    rows = iter_catalog_rows(vcr_root)
    provider_summary: dict[str, ProviderCatalogSummary] = {}
    paths_by_stem: dict[str, list[str]] = {}
    expected_metadata_paths = {
        row.metadata_rel_path for row in rows if row.metadata_rel_path is not None
    }
    actual_metadata_paths = {
        path.as_posix()
        for path in vcr_root.rglob("*")
        if path.is_file() and path.name.endswith(("_meta.yaml", "_meta.yml"))
    }

    for row in rows:
        summary = provider_summary.setdefault(row.provider, ProviderCatalogSummary())
        summary.cassette_count += 1
        if row.has_metadata_sidecar:
            summary.metadata_sidecar_count += 1
        else:
            summary.without_metadata_count += 1
        paths_by_stem.setdefault(row.scenario_stem, []).append(row.cassette_rel_path)

    for summary in provider_summary.values():
        cassette_count = summary.cassette_count
        metadata_sidecar_count = summary.metadata_sidecar_count
        coverage_percent = (
            round((metadata_sidecar_count / cassette_count) * 100.0, 2)
            if cassette_count
            else 0.0
        )
        summary.metadata_coverage_percent = coverage_percent
    duplicate_scenario_stems = {
        stem: sorted(paths)
        for stem, paths in sorted(paths_by_stem.items())
        if len(paths) > 1
    }

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
            "duplicate_scenario_stem_count": len(duplicate_scenario_stems),
            "direct_reachable_cassette_count": sum(
                1 for row in rows if row.reachability_status == "direct_reference"
            ),
            "generated_reachable_cassette_count": sum(
                1 for row in rows if row.reachability_status == "generated_reference"
            ),
            "metadata_review_required_cassette_count": sum(
                1
                for row in rows
                if row.reachability_status == "metadata_review_required"
            ),
            "unowned_cassette_count": sum(
                1 for row in rows if row.reachability_status == "unowned"
            ),
        },
        "pruning": {
            "duplicate_scenario_stems": duplicate_scenario_stems,
            "orphan_metadata_sidecar_count": len(
                actual_metadata_paths - expected_metadata_paths
            ),
            "metadata_review_required_cassettes": [
                row.cassette_rel_path
                for row in rows
                if row.reachability_status == "metadata_review_required"
            ],
            "unowned_cassettes": [
                row.cassette_rel_path
                for row in rows
                if row.reachability_status == "unowned"
            ],
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
