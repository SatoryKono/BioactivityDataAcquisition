#!/usr/bin/env python3
"""Fail closed when architecture JUnit is missing, empty, or contains skips."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail closed on empty architecture JUnit or nonzero skips.",
    )
    parser.add_argument(
        "--junit-dir",
        type=Path,
        required=True,
        help="Directory containing pytest JUnit XML files.",
    )
    return parser.parse_args()


def _suites(root: ET.Element) -> list[ET.Element]:
    if root.tag == "testsuite":
        return [root]
    if root.tag == "testsuites":
        return [elem for elem in root if elem.tag == "testsuite"]
    return []


def main() -> int:
    args = _parse_args()
    files = sorted(args.junit_dir.glob("*.xml"))
    if not files:
        print(
            f"::error::Missing architecture JUnit XML in {args.junit_dir}",
            file=sys.stderr,
        )
        return 1
    tests = 0
    skipped = 0
    for path in files:
        root = ET.parse(path).getroot()
        for suite in _suites(root):
            tests += int(suite.attrib.get("tests", "0"))
            skipped += int(suite.attrib.get("skipped", "0"))
    if tests == 0:
        print(
            f"::error::Architecture JUnit collection is empty in {args.junit_dir}",
            file=sys.stderr,
        )
        return 1
    if skipped > 0:
        print(
            "::error::Architecture skip budget is zero; "
            f"skipped={skipped} tests={tests} dir={args.junit_dir}",
            file=sys.stderr,
        )
        return 1
    print(f"architecture junit tests={tests} skipped={skipped} dir={args.junit_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
