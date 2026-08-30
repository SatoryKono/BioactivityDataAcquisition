#!/usr/bin/env python3
"""Fast preflight for replay-heavy VCR lanes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any

from tests.helpers.vcr_config import (
    build_base_vcr_config,
    is_git_lfs_pointer,
    is_strict_lfs_pointer_blocked_cassette,
)

DEFAULT_ROOT = Path.cwd()
DEFAULT_VCR_ROOT = Path("tests/fixtures/vcr")
DEFAULT_CATALOG = Path("reports/quality/vcr-metadata-catalog.json")
PUBLIC_BLOCKER_IDS = {
    "missing_vcr_metadata_catalog",
    "unresolved_replay_critical_lfs_pointers",
    "unresolved_vcr_lfs_pointers",
    "vcr_metadata_catalog_totals_drift",
    "vcr_metadata_catalog_unowned_cassettes",
    "vcr_secret_filter_sanity_failed",
}


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


def _sanitizer_status() -> dict[str, Any]:
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
    sanitizer_status = _sanitizer_status()

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
    if (
        not sanitizer_status["replay_only"]
        or not sanitizer_status["has_request_sanitizer"]
    ):
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
        "sanitizer_status": sanitizer_status,
        "remediation": "Run `git lfs pull` before replaying unresolved VCR cassettes.",
        "blockers": blockers,
    }


def _public_repo_path(value: object) -> str | None:
    """Return a repository-relative POSIX path safe for CLI output."""
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        return None
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    return candidate.as_posix()


def _public_count(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _public_pointer_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = report.get("unresolved_lfs_pointers")
    if not isinstance(rows, list):
        return []
    public_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = _public_repo_path(row.get("path"))
        if path is not None:
            public_rows.append(
                {
                    "path": path,
                    "strict_replay_blocked": row.get("strict_replay_blocked") is True,
                }
            )
    return public_rows


def _public_blocker_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = report.get("blockers")
    if not isinstance(blockers, list):
        return []
    public_rows: list[dict[str, Any]] = []
    for blocker in blockers:
        if not isinstance(blocker, dict):
            continue
        blocker_id = blocker.get("id")
        if not isinstance(blocker_id, str) or blocker_id not in PUBLIC_BLOCKER_IDS:
            continue
        public_blocker: dict[str, Any] = {"id": blocker_id}
        raw_paths = blocker.get("paths")
        if isinstance(raw_paths, list):
            paths = [
                path
                for raw_path in raw_paths
                if (path := _public_repo_path(raw_path)) is not None
            ]
            if paths:
                public_blocker["paths"] = paths
        public_rows.append(public_blocker)
    return public_rows


def _public_vcr_replay_preflight(report: dict[str, Any]) -> dict[str, Any]:
    """Build the explicit CLI DTO without internal paths or diagnostic messages."""
    catalog = report.get("catalog")
    if not isinstance(catalog, dict):
        catalog = {}
    sanitizer = report.get("sanitizer_status")
    if not isinstance(sanitizer, dict):
        sanitizer = {}

    return {
        "schema_version": "vcr-replay-preflight-public-v2",
        "vcr_root": _public_repo_path(report.get("vcr_root")),
        "cassette_count": _public_count(report.get("cassette_count")),
        "metadata_sidecar_count": _public_count(report.get("metadata_sidecar_count")),
        "unresolved_lfs_pointers": _public_pointer_rows(report),
        "strict_unresolved_lfs_pointer_count": _public_count(
            report.get("strict_unresolved_lfs_pointer_count")
        ),
        "catalog": {
            "path": _public_repo_path(catalog.get("path")),
            "exists": catalog.get("exists") is True,
            "totals_match": catalog.get("totals_match") is True,
            "unowned_cassette_count": _public_count(
                catalog.get("unowned_cassette_count")
            ),
            "duplicate_scenario_stem_count": _public_count(
                catalog.get("duplicate_scenario_stem_count")
            ),
        },
        "sanitizer_status": {
            "record_mode": "none"
            if sanitizer.get("record_mode") == "none"
            else "unknown",
            "replay_only": sanitizer.get("replay_only") is True,
            "has_request_sanitizer": sanitizer.get("has_request_sanitizer") is True,
            "has_response_filter": sanitizer.get("has_response_filter") is True,
        },
        "remediation": "Run `git lfs pull` before replaying unresolved VCR cassettes.",
        "blockers": _public_blocker_rows(report),
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
    print(json.dumps(_public_vcr_replay_preflight(report), indent=2, sort_keys=True))
    if args.strict and report["blockers"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
