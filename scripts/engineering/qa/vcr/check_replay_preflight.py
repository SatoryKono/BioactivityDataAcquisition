#!/usr/bin/env python3
"""Fast preflight for replay-heavy VCR lanes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tests.helpers.vcr_config import (
    build_base_vcr_config,
    is_git_lfs_pointer,
    is_strict_lfs_pointer_blocked_cassette,
)

DEFAULT_ROOT = Path.cwd()
DEFAULT_VCR_ROOT = Path("tests/fixtures/vcr")
DEFAULT_CATALOG = Path("reports/quality/vcr-metadata-catalog.json")


def _repo_path(path: Path, *, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _cassette_files(vcr_root: Path) -> list[Path]:
    if not vcr_root.exists():
        return []
    return sorted(
        path
        for path in vcr_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".yaml", ".yml"}
        and not path.name.endswith(("_meta.yaml", "_meta.yml"))
    )


def _metadata_files(vcr_root: Path) -> list[Path]:
    if not vcr_root.exists():
        return []
    return sorted(
        path
        for path in vcr_root.rglob("*")
        if path.is_file() and path.name.endswith(("_meta.yaml", "_meta.yml"))
    )


def _pointer_rows(paths: list[Path], *, root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not is_git_lfs_pointer(path):
            continue
        rows.append(
            {
                "path": _repo_path(path, root=root),
                "strict_replay_blocked": is_strict_lfs_pointer_blocked_cassette(
                    path,
                    repo_root=root,
                ),
            }
        )
    return rows


def _catalog_status(
    *,
    root: Path,
    catalog_path: Path,
    cassette_count: int,
    metadata_sidecar_count: int,
) -> dict[str, Any]:
    resolved = root / catalog_path
    if not resolved.exists():
        return {
            "path": catalog_path.as_posix(),
            "exists": False,
            "totals_match": False,
            "unowned_cassette_count": None,
            "duplicate_scenario_stem_count": None,
        }

    payload = json.loads(resolved.read_text(encoding="utf-8"))
    totals = payload.get("totals", {})
    if not isinstance(totals, dict):
        totals = {}
    return {
        "path": catalog_path.as_posix(),
        "exists": True,
        "totals_match": totals.get("cassette_count") == cassette_count
        and totals.get("metadata_sidecar_count") == metadata_sidecar_count,
        "cassette_count": totals.get("cassette_count"),
        "metadata_sidecar_count": totals.get("metadata_sidecar_count"),
        "unowned_cassette_count": totals.get("unowned_cassette_count"),
        "duplicate_scenario_stem_count": totals.get("duplicate_scenario_stem_count"),
    }


def _secret_filter_status() -> dict[str, Any]:
    config = build_base_vcr_config(
        filter_headers=("authorization", "x-api-key"),
        filter_query_parameters=("api_key", "key"),
    )
    return {
        "record_mode": config.get("record_mode"),
        "replay_only": config.get("record_mode") == "none",
        "has_request_sanitizer": callable(config.get("before_record_request")),
        "has_response_filter": callable(config.get("before_record_response")),
    }


def collect_vcr_replay_preflight(
    root: Path = DEFAULT_ROOT,
    *,
    vcr_root: Path = DEFAULT_VCR_ROOT,
    catalog_path: Path = DEFAULT_CATALOG,
) -> dict[str, Any]:
    """Collect fast replay-lane blockers before pytest opens cassettes."""
    root = root.resolve()
    resolved_vcr_root = root / vcr_root
    cassettes = _cassette_files(resolved_vcr_root)
    metadata = _metadata_files(resolved_vcr_root)
    pointer_rows = _pointer_rows(cassettes, root=root)
    strict_pointer_rows = [row for row in pointer_rows if row["strict_replay_blocked"]]
    catalog = _catalog_status(
        root=root,
        catalog_path=catalog_path,
        cassette_count=len(cassettes),
        metadata_sidecar_count=len(metadata),
    )
    secret_filter = _secret_filter_status()

    blockers: list[dict[str, Any]] = []
    if pointer_rows:
        blockers.append(
            {
                "id": "unresolved_vcr_lfs_pointers",
                "message": (
                    f"Found {len(pointer_rows)} unresolved VCR Git LFS pointer "
                    "cassette(s); run git lfs pull before replaying."
                ),
                "paths": [row["path"] for row in pointer_rows],
            }
        )
    if strict_pointer_rows:
        blockers.append(
            {
                "id": "unresolved_replay_critical_lfs_pointers",
                "message": (
                    f"Found {len(strict_pointer_rows)} replay-critical unresolved "
                    "Git LFS pointer cassette(s); run git lfs pull before replaying."
                ),
                "paths": [row["path"] for row in strict_pointer_rows],
            }
        )
    if not catalog["exists"]:
        blockers.append(
            {
                "id": "missing_vcr_metadata_catalog",
                "message": f"Missing {catalog_path.as_posix()}.",
            }
        )
    elif not catalog["totals_match"]:
        blockers.append(
            {
                "id": "vcr_metadata_catalog_totals_drift",
                "message": (
                    "VCR metadata catalog totals do not match current cassette tree."
                ),
            }
        )
    if catalog.get("unowned_cassette_count") not in (0, None):
        blockers.append(
            {
                "id": "vcr_metadata_catalog_unowned_cassettes",
                "message": "VCR metadata catalog reports unowned cassettes.",
            }
        )
    if not secret_filter["replay_only"] or not secret_filter["has_request_sanitizer"]:
        blockers.append(
            {
                "id": "vcr_secret_filter_sanity_failed",
                "message": "Base VCR config is not replay-only with request sanitizers.",
            }
        )

    return {
        "schema_version": "vcr-replay-preflight-v1",
        "root": root.as_posix(),
        "vcr_root": vcr_root.as_posix(),
        "cassette_count": len(cassettes),
        "metadata_sidecar_count": len(metadata),
        "unresolved_lfs_pointers": pointer_rows,
        "strict_unresolved_lfs_pointer_count": len(strict_pointer_rows),
        "catalog": catalog,
        "secret_filter": secret_filter,
        "remediation": "Run `git lfs pull` before replaying unresolved VCR cassettes.",
        "blockers": blockers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fast VCR replay preflight for unresolved LFS pointers and catalog drift.",
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--vcr-root", type=Path, default=DEFAULT_VCR_ROOT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when replay blockers are present.",
    )
    args = parser.parse_args(argv)

    report = collect_vcr_replay_preflight(
        args.root,
        vcr_root=args.vcr_root,
        catalog_path=args.catalog,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and report["blockers"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
