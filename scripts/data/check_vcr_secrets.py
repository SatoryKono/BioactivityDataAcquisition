#!/usr/bin/env python3
"""Detect potential secret leaks in VCR cassette files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr"

TOKEN_RE = re.compile(
    r"(?i)\b(api[_-]?key|apikey|token|access[_-]?token|refresh[_-]?token|secret|password)\b"
)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BEARER_RE = re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/=-]{8,})")
REDACTED_MARKERS = ("REDACTED", "<redacted>", "***", "example", "noreply", "test@")


def _looks_redacted(value: str) -> bool:
    lowered = value.lower()
    return any(marker.lower() in lowered for marker in REDACTED_MARKERS)


def _scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    for idx, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        if TOKEN_RE.search(line) and not _looks_redacted(line):
            findings.append(f"{path.relative_to(ROOT)}:{idx}: suspicious token field")
            continue

        if BEARER_RE.search(line) and not _looks_redacted(line):
            findings.append(f"{path.relative_to(ROOT)}:{idx}: possible bearer token")
            continue

        match = EMAIL_RE.search(line)
        if match and not _looks_redacted(match.group(0)):
            findings.append(f"{path.relative_to(ROOT)}:{idx}: possible real email")

    return findings


def main() -> int:
    if not VCR_ROOT.exists():
        sys.stdout.write("No VCR directory found, skipping.\n")
        return 0

    findings: list[str] = []
    for cassette in sorted(VCR_ROOT.rglob("*.yaml")):
        findings.extend(_scan_file(cassette))

    if findings:
        sys.stderr.write(
            "ERROR: potential secret leaks found in VCR cassettes. "
            "Replace sensitive values with REDACTED placeholders.\n"
        )
        for finding in findings:
            sys.stderr.write(f" - {finding}\n")
        return 1

    sys.stdout.write("OK: no obvious secrets found in VCR cassettes.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
