#!/usr/bin/env python3
"""Detect potential secret leaks in VCR cassette files.

The checker is intentionally conservative and only inspects places where API
credentials should appear in recorded HTTP traffic:
- request headers (`Authorization`, `X-API-Key`, etc.)
- request URLs (`api_key`, `apikey`, `token`, `key` query parameters)
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

ROOT = Path(__file__).resolve().parents[4]
VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr"

QUERY_KEYS = {"api_key", "apikey", "token", "key", "access_token", "refresh_token"}
HEADER_KEYS = {
    "authorization",
    "x-api-key",
    "api-key",
    "x-auth-token",
    "proxy-authorization",
}
REDACTED_MARKERS = ("redacted", "<redacted>", "***", "example", "dummy", "test")


def _looks_redacted(value: str) -> bool:
    lowered = value.strip().strip("'\"").lower()
    if not lowered:
        return True
    return any(marker in lowered for marker in REDACTED_MARKERS)


def _scan_uri(path: Path, line_idx: int, uri_value: str) -> list[str]:
    findings: list[str] = []
    query_items = parse_qsl(urlparse(uri_value).query, keep_blank_values=True)
    for key, value in query_items:
        finding = _query_credential_finding(path, line_idx, key, value)
        if finding is not None:
            findings.append(finding)
    return findings


def _query_credential_finding(
    path: Path,
    line_idx: int,
    key: str,
    value: str,
) -> str | None:
    """Return finding for one query credential when it looks unredacted."""
    if key.lower() not in QUERY_KEYS or _looks_redacted(value):
        return None
    return f"{path.relative_to(ROOT)}:{line_idx}: unredacted query credential '{key}'"


def _header_value_finding(
    *,
    path: Path,
    idx: int,
    header_name: str,
    lines: list[str],
) -> str | None:
    """Return finding for a suspicious header value, if any."""
    next_line = lines[idx].strip() if idx < len(lines) else ""
    if not next_line.startswith("-"):
        return f"{path.relative_to(ROOT)}:{idx}: header '{header_name}' without value"
    header_value = next_line.lstrip("-").strip()
    if _looks_redacted(header_value):
        return None
    return f"{path.relative_to(ROOT)}:{idx + 1}: unredacted header '{header_name}'"


def _scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        if line.lower().startswith("uri: "):
            uri = line[5:].strip()
            findings.extend(_scan_uri(path, idx, uri))
            continue

        if not line.endswith(":"):
            continue
        header_name = line[:-1].strip().lower()
        if header_name not in HEADER_KEYS:
            continue
        finding = _header_value_finding(
            path=path,
            idx=idx,
            header_name=header_name,
            lines=lines,
        )
        if finding is not None:
            findings.append(finding)

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
