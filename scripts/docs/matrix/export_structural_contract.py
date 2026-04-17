#!/usr/bin/env python3
"""Export the canonical ChEMBL runtime structural contract for workbook sync."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.docs.matrix.structural_contract import (
    DEFAULT_CONTRACT_EXPORT,
    build_runtime_contract_rows,
    serialize_runtime_contract_rows,
    write_runtime_contract_export,
)


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export the current ChEMBL runtime structural contract used by "
            "workbook sync and documentation reconciliation."
        )
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_CONTRACT_EXPORT,
        type=Path,
        help="Output JSON export path.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with status 1 if the exported contract would change.",
    )
    return parser


def main() -> int:
    args = _arg_parser().parse_args()
    output_path = args.output.resolve()
    if args.check:
        rows = build_runtime_contract_rows()
        payload = {
            "version": 1,
            "rows": serialize_runtime_contract_rows(rows),
        }
        expected = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        actual = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        result = {"output": str(output_path), "rows": len(rows)}
        print(result)
        return 0 if actual == expected else 1
    rows = write_runtime_contract_export(output_path)
    print({"output": str(output_path), "rows": len(rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
