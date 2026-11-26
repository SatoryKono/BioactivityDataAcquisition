"""Build an immutable IUPHAR snapshot from pinned offline official export bytes."""

from __future__ import annotations

import argparse
from pathlib import Path

from bioetl.infrastructure.adapters.iuphar.snapshot_payload import build_snapshot_bundle
from iuphar_target_class.identifier_roles import (
    ANCHOR_PRIORITY_POLICIES,
    MATCHING_POLICY_VERSION,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--acquisition-sha256", required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--coverage-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--matching-policy-version",
        choices=(MATCHING_POLICY_VERSION, *sorted(ANCHOR_PRIORITY_POLICIES)),
        default=MATCHING_POLICY_VERSION,
    )
    args = parser.parse_args(argv)
    bundle = build_snapshot_bundle(
        acquisition=args.acquisition,
        acquisition_sha256=args.acquisition_sha256,
        coverage=args.coverage,
        coverage_sha256=args.coverage_sha256,
        output_dir=args.output_dir,
        matching_policy_version=args.matching_policy_version,
    )
    print(f"snapshot_sha256={bundle.snapshot_sha256}")
    print(f"profile_sha256={bundle.profile_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
