"""CLI for BioETL passport documentation projections."""

from __future__ import annotations

import argparse
from pathlib import Path

from .projector import build_all_outputs, check_outputs, write_outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("generate", "check"))
    parser.add_argument("--configs-root", type=Path, default=Path("configs"))
    parser.add_argument(
        "--output-root", type=Path, default=Path("docs/04-reference/passports")
    )
    parser.add_argument("--source-revision")
    parser.add_argument("--manual-root", type=Path)
    args = parser.parse_args(argv)
    outputs = build_all_outputs(
        configs_root=args.configs_root,
        output_root=args.output_root,
        source_revision=args.source_revision,
        manual_root=args.manual_root,
    )
    if args.action == "check":
        stale = check_outputs(outputs)
        if stale:
            for path in stale:
                print(f"stale: {path.as_posix()}")
            return 1
        print(f"Passport artifacts current: {len(outputs)} files")
        return 0
    write_outputs(outputs)
    print(f"Generated passport artifacts: {len(outputs)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
