#!/usr/bin/env python3
"""Backfill deterministic VCR cassette metadata sidecars."""

from __future__ import annotations

import argparse
import hashlib
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_VCR_ROOT = Path("tests/fixtures/vcr")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill deterministic *_meta.yaml sidecars for VCR cassettes."
    )
    parser.add_argument(
        "--vcr-root",
        default=str(DEFAULT_VCR_ROOT),
        help="Root VCR cassette directory.",
    )
    parser.add_argument(
        "--provider",
        default="",
        help="Optional provider to limit the backfill scope.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max cassette count to backfill.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if any selected cassette is missing a sidecar.",
    )
    parser.add_argument(
        "--recorded-at",
        default=datetime.now(UTC).date().isoformat(),
        help="ISO date to stamp into sidecars (default: today in UTC).",
    )
    parser.add_argument(
        "--rewrite-existing",
        action="store_true",
        help="Rewrite existing sidecars to the canonical managed-inventory payload.",
    )
    return parser.parse_args()


def _metadata_path_for(cassette_path: Path) -> Path:
    return cassette_path.with_name(f"{cassette_path.stem}_meta.yaml")


def _selected_cassettes(vcr_root: Path, provider: str) -> list[Path]:
    search_root = vcr_root / provider if provider else vcr_root
    if not search_root.exists():
        return []
    return sorted(
        path
        for path in search_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".yaml", ".yml"}
        and not path.name.endswith(("_meta.yaml", "_meta.yml"))
    )


def _is_binary_file(path: Path) -> bool:
    """Best-effort binary-file detection for cassette candidates."""
    chunk = path.read_bytes()[:1024]
    return b"\x00" in chunk


def _build_sidecar_payload(
    vcr_root: Path, cassette_path: Path, *, recorded_at: str
) -> dict[str, object]:
    cassette_path = cassette_path.resolve()
    vcr_root = vcr_root.resolve()
    provider = cassette_path.relative_to(vcr_root).parts[0]
    cassette_bytes = cassette_path.read_bytes()
    cassette_rel_path = cassette_path.relative_to(ROOT).as_posix()
    return {
        "schema_version": 1,
        "provider": provider,
        "cassette_rel_path": cassette_rel_path,
        "metadata_status": "managed_inventory",
        "source": "backfill_vcr_metadata_sidecars.py",
        "cassette_sha256": hashlib.sha256(cassette_bytes).hexdigest(),
        "recorded_at": recorded_at,
        "staleness_ready": True,
    }


def main() -> int:
    args = _parse_args()
    vcr_root = Path(args.vcr_root).resolve()
    cassettes = _selected_cassettes(vcr_root, args.provider)
    if args.limit > 0:
        cassettes = cassettes[: args.limit]

    if args.check:
        missing = [
            path.as_posix()
            for path in cassettes
            if not _metadata_path_for(path).exists()
        ]
        if missing:
            print(
                "[backfill-vcr-metadata] FAIL: missing sidecars\n"
                + "\n".join(f"- {item}" for item in missing)
            )
            return 1
        print("[backfill-vcr-metadata] PASS: all selected cassettes have sidecars")
        return 0

    written = 0
    for cassette_path in cassettes:
        if _is_binary_file(cassette_path):
            continue
        metadata_path = _metadata_path_for(cassette_path)
        if metadata_path.exists() and not args.rewrite_existing:
            continue
        payload = _build_sidecar_payload(
            vcr_root, cassette_path, recorded_at=args.recorded_at
        )
        metadata_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
        written += 1

    print(f"[backfill-vcr-metadata] wrote {written} sidecar(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
