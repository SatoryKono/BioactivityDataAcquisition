#!/usr/bin/env python3
"""Census VCR cassettes vs test references (#6899).

Usage:
    python -m scripts.engineering.qa.report_vcr_cassette_census
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr"
TESTS_ROOT = ROOT / "tests"
OUT = ROOT / "reports" / "quality" / "vcr-cassette-census.json"


def main() -> None:
    cassettes = sorted(VCR_ROOT.rglob("*.yaml")) + sorted(VCR_ROOT.rglob("*.yml"))
    # Build a searchable blob of test sources (path + content names).
    test_files = list(TESTS_ROOT.rglob("test_*.py")) + list(
        TESTS_ROOT.rglob("conftest.py")
    )
    blob_parts: list[str] = []
    for path in test_files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        blob_parts.append(path.as_posix())
        blob_parts.append(text)
    blob = "\n".join(blob_parts)

    unused: list[str] = []
    used: list[str] = []
    for cassette in cassettes:
        rel = cassette.relative_to(ROOT).as_posix()
        name = cassette.name
        stem = cassette.stem
        # Match full relative path, filename, or stem token in tests.
        if rel in blob or name in blob or re.search(re.escape(stem), blob):
            used.append(rel)
        else:
            unused.append(rel)

    payload = {
        "schema_version": "vcr-cassette-census-v1",
        "linked_issue": "#6899",
        "parent_epic": "#6890",
        "snapshot_date": date.today().isoformat(),
        "generated_by": "scripts.engineering.qa.report_vcr_cassette_census",
        "summary": {
            "cassette_count": len(cassettes),
            "used_count": len(used),
            "unused_candidate_count": len(unused),
            "policy": "prune_only_after_owner_review",
        },
        "unused_candidates": unused,
        "used_sample": used[:25],
        "notes": [
            "Stem matching is intentionally conservative and may false-positive retain.",
            "Do not delete unused_candidates without owner review and importer double-check.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"[updated] {OUT} cassettes={len(cassettes)} "
        f"used~={len(used)} unused_candidates={len(unused)}"
    )


if __name__ == "__main__":
    main()
