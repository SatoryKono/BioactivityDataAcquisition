#!/usr/bin/env python3
"""Validate managed VCR metadata sidecars and enforce stale-age policy."""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[4]
VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate managed VCR metadata sidecars and enforce stale-age policy."
    )
    parser.add_argument(
        "--vcr-root",
        default=str(VCR_ROOT),
        help="Root VCR cassette directory.",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=90,
        help="Maximum allowed metadata age in days.",
    )
    return parser.parse_args()


def _iter_cassettes(vcr_root: Path) -> list[Path]:
    return sorted(
        path
        for path in vcr_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".yaml", ".yml"}
        and not path.name.endswith(("_meta.yaml", "_meta.yml"))
    )


def _metadata_path_for(cassette_path: Path) -> Path:
    return cassette_path.with_name(f"{cassette_path.stem}_meta.yaml")


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"metadata payload must be a mapping: {path.as_posix()}")
    return payload


def _parse_recorded_at(raw: object, *, metadata_path: Path) -> date:
    if not isinstance(raw, str) or not raw:
        raise AssertionError(
            f"metadata sidecar missing recorded_at ISO date: {metadata_path.as_posix()}"
        )
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError as exc:
        raise AssertionError(
            f"invalid recorded_at date in {metadata_path.as_posix()}: {raw!r}"
        ) from exc


def _validate_sidecar(
    cassette_path: Path,
    metadata_path: Path,
    *,
    vcr_root: Path,
    max_age_days: int,
    today: date,
) -> list[str]:
    failures: list[str] = []
    if not metadata_path.exists():
        return [f"missing metadata sidecar for {cassette_path.as_posix()}"]

    payload = _load_yaml(metadata_path)
    provider = cassette_path.relative_to(vcr_root).parts[0]
    expected_rel_path = cassette_path.relative_to(ROOT).as_posix()
    expected_sha = hashlib.sha256(cassette_path.read_bytes()).hexdigest()
    recorded_at = _parse_recorded_at(payload.get("recorded_at"), metadata_path=metadata_path)
    age_days = (today - recorded_at).days

    if payload.get("schema_version") != 1:
        failures.append(f"invalid schema_version in {metadata_path.as_posix()}")
    if payload.get("provider") != provider:
        failures.append(f"provider drift in {metadata_path.as_posix()}")
    if payload.get("cassette_rel_path") != expected_rel_path:
        failures.append(f"cassette_rel_path drift in {metadata_path.as_posix()}")
    if payload.get("metadata_status") != "managed_inventory":
        failures.append(f"metadata_status drift in {metadata_path.as_posix()}")
    if payload.get("source") != "backfill_vcr_metadata_sidecars.py":
        failures.append(f"unexpected source in {metadata_path.as_posix()}")
    if payload.get("cassette_sha256") != expected_sha:
        failures.append(f"cassette_sha256 drift in {metadata_path.as_posix()}")
    if payload.get("staleness_ready") is not True:
        failures.append(f"staleness_ready must be true in {metadata_path.as_posix()}")
    if age_days < 0:
        failures.append(f"recorded_at is in the future for {metadata_path.as_posix()}")
    if age_days > max_age_days:
        failures.append(
            f"metadata sidecar is stale ({age_days}d > {max_age_days}d): {metadata_path.as_posix()}"
        )
    return failures


def main() -> int:
    args = _parse_args()
    vcr_root = Path(args.vcr_root)
    today = datetime.now(UTC).date()
    failures: list[str] = []

    for cassette_path in _iter_cassettes(vcr_root):
        failures.extend(
            _validate_sidecar(
                cassette_path,
                _metadata_path_for(cassette_path),
                vcr_root=vcr_root,
                max_age_days=args.max_age_days,
                today=today,
            )
        )

    if failures:
        sys.stderr.write(
            "[check-vcr-metadata-age] FAIL: managed VCR metadata inventory drift\n"
        )
        for failure in failures:
            sys.stderr.write(f"- {failure}\n")
        return 1

    sys.stdout.write(
        "[check-vcr-metadata-age] PASS: managed VCR metadata inventory is complete and within stale-age budget.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
