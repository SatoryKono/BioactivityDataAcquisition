#!/usr/bin/env python3
"""Validate sunset dates for oneoff migration scripts.

This script checks all oneoff migration scripts for:
- Missing SUNSET_DATE headers
- Expired SUNSET_DATE values
- Invalid SUNSET_DATE formats

Usage:
    python scripts/ops/migrations/validate_sunset_dates.py
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import TypedDict

# Directory containing oneoff migration scripts
ONEOFF_DIR = Path(__file__).parent / "oneoff"

# Sunset date pattern
SUNSET_PATTERN = re.compile(r"SUNSET_DATE:\s*(\d{4}-\d{2}-\d{2})")

# Default sunset months from creation
DEFAULT_SUNSET_MONTHS = 6


class SunsetCheckResult(TypedDict):
    """Structured result for one migration script."""

    script: str
    issues: list[str]
    sunset_date: str | None


def parse_sunset_date(content: str) -> date | None:
    """Parse SUNSET_DATE from script content."""
    match = SUNSET_PATTERN.search(content)
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def check_script(script_path: Path) -> SunsetCheckResult:
    """Check a single migration script for sunset date compliance."""
    issues = []

    content = script_path.read_text()
    sunset_date = parse_sunset_date(content)

    if sunset_date is None:
        issues.append("Missing SUNSET_DATE header")
        return {"script": str(script_path), "issues": issues, "sunset_date": None}

    # Check if sunset date is expired
    today = date.today()
    if sunset_date < today:
        days_expired = (today - sunset_date).days
        issues.append(f"Expired SUNSET_DATE (expired {days_expired} days ago)")

    return {
        "script": str(script_path),
        "issues": issues,
        "sunset_date": sunset_date.isoformat(),
    }


def _report_script_result(
    script: Path,
    result: SunsetCheckResult,
) -> tuple[bool, bool]:
    if result["issues"]:
        print(f"❌ {script.name}:")
        for issue in result["issues"]:
            print(f"   - {issue}")
        if result["sunset_date"]:
            print(f"   SUNSET_DATE: {result['sunset_date']}")
        return True, False

    print(f"✅ {script.name}: SUNSET_DATE {result['sunset_date']}")
    if not result["sunset_date"]:
        return False, False
    sunset_date = datetime.strptime(result["sunset_date"], "%Y-%m-%d").date()
    days_until_sunset = (sunset_date - date.today()).days
    if days_until_sunset > 30:
        return False, False
    print(f"   ⚠️  Expiring in {days_until_sunset} days")
    return False, True


def _report_summary(
    all_issues: list[SunsetCheckResult],
    expiring_scripts: list[str],
) -> int:
    print()
    print("=" * 60)
    if all_issues:
        print(f"❌ Found {len(all_issues)} scripts with issues")
        print()
        print("Action required:")
        print("- Add SUNSET_DATE headers to missing scripts")
        print("- Remove or archive expired scripts")
        print("- Update scripts inventory")
        return 1

    print("✅ All scripts have valid SUNSET_DATE headers")
    if expiring_scripts:
        print()
        print("⚠️  Scripts expiring soon:")
        for script_name in expiring_scripts:
            print(f"   - {script_name}")
    return 0


def main() -> int:
    """Validate all oneoff migration scripts."""
    if not ONEOFF_DIR.exists():
        print(f"ERROR: Oneoff directory not found: {ONEOFF_DIR}")
        return 1

    scripts = list(ONEOFF_DIR.glob("*.py"))
    if not scripts:
        print(f"No migration scripts found in {ONEOFF_DIR}")
        return 0

    print(f"Validating {len(scripts)} oneoff migration scripts...")
    print()

    all_issues: list[SunsetCheckResult] = []
    expired_scripts: list[str] = []

    for script in scripts:
        result = check_script(script)
        has_issues, expires_soon = _report_script_result(script, result)
        if has_issues:
            all_issues.append(result)
        if expires_soon:
            expired_scripts.append(script.name)

    return _report_summary(all_issues, expired_scripts)


if __name__ == "__main__":
    sys.exit(main())
