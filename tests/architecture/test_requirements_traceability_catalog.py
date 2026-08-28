# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""REQ-DOC-001: docs/01-requirements and tests cite only catalog REQ-* IDs.

Row-level SSOT is requirements-traceability-crosswalk.csv. This guard stops
orphan markdown IDs (e.g. REQ-DASH-004 missing a CSV row) and invented test
aliases (REQ-ARCH family members past CSV 001-007, REQ-PERF-*, …).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

_ROOT = Path(__file__).resolve().parents[2]
_CSV = (
    _ROOT
    / "docs"
    / "01-requirements"
    / "traceability"
    / "requirements-traceability-crosswalk.csv"
)
_REQUIREMENTS = _ROOT / "docs" / "01-requirements" / "REQUIREMENTS.md"
_REQ_DOCS = _ROOT / "docs" / "01-requirements"
_TESTS = _ROOT / "tests"

# Catalog IDs are family + three-digit suffix (REQ-ARCH-001, REQ-DASH-004).
_REQ_ID_RE = re.compile(r"REQ-[A-Z]+(?:-[A-Z]+)*-\d{3}")
_ACTIVE_COUNT_RE = re.compile(r"\*\*(\d+) active requirements\*\*")
_MUST_COUNT_RE = re.compile(r"^-\s+(\d+)\s+`MUST`;", re.MULTILINE)


def _catalog_ids() -> list[str]:
    with _CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["requirement_id"] for row in rows]
    assert ids, f"empty catalog: {_CSV}"
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    assert not duplicates, f"duplicate CSV requirement_id values: {duplicates}"
    return ids


def _ids_in_tree(root: Path, pattern: str) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for path in sorted(root.rglob(pattern)):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(_ROOT).as_posix()
        for match in _REQ_ID_RE.finditer(text):
            hits.setdefault(match.group(0), []).append(rel)
    return hits


def test_requirements_index_counts_match_crosswalk_csv() -> None:
    """REQUIREMENTS.md headline counts must equal the CSV row inventory."""
    ids = _catalog_ids()
    with _CSV.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    must_count = sum(1 for row in rows if row["modality"] == "MUST")

    text = _REQUIREMENTS.read_text(encoding="utf-8")
    active = _ACTIVE_COUNT_RE.search(text)
    must_claimed = _MUST_COUNT_RE.search(text)
    assert active is not None, "REQUIREMENTS.md must state active requirement count"
    assert must_claimed is not None, "REQUIREMENTS.md must state MUST count"
    assert int(active.group(1)) == len(ids), (
        f"REQUIREMENTS.md claims {active.group(1)} active rows; CSV has {len(ids)}"
    )
    assert int(must_claimed.group(1)) == must_count, (
        f"REQUIREMENTS.md claims {must_claimed.group(1)} MUST; CSV has {must_count}"
    )


def test_requirement_ids_in_docs_are_in_crosswalk_csv() -> None:
    """Every REQ-*-NNN in docs/01-requirements must have a CSV row."""
    catalog = set(_catalog_ids())
    found = _ids_in_tree(_REQ_DOCS, "*.md")
    orphans = sorted(req_id for req_id in found if req_id not in catalog)
    assert not orphans, (
        "docs/01-requirements cites REQ IDs missing from the crosswalk CSV:\n"
        + "\n".join(f"  {req_id}: {sorted(set(found[req_id]))}" for req_id in orphans)
    )


def test_requirement_ids_in_tests_are_in_crosswalk_csv() -> None:
    """Every REQ-*-NNN in tests/ must be a catalog ID (no invented aliases)."""
    catalog = set(_catalog_ids())
    found = _ids_in_tree(_TESTS, "*.py")
    invented = sorted(req_id for req_id in found if req_id not in catalog)
    assert not invented, (
        "tests/ cites REQ IDs missing from the crosswalk CSV:\n"
        + "\n".join(f"  {req_id}: {sorted(set(found[req_id]))}" for req_id in invented)
    )


def test_requirement_ids_in_rules_adr_and_src_are_in_crosswalk_csv() -> None:
    """RULES, accepted ADR, and src/bioetl must not invent REQ-* IDs (#9803)."""
    catalog = set(_catalog_ids())
    rules = _ROOT / "docs" / "00-project" / "RULES.md"
    adr_root = _ROOT / "docs" / "02-architecture" / "decisions"
    src_root = _ROOT / "src" / "bioetl"
    found: dict[str, list[str]] = {}
    for path in [rules, *sorted(adr_root.glob("ADR-*.md")), *sorted(src_root.rglob("*.py"))]:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(_ROOT).as_posix()
        for match in _REQ_ID_RE.finditer(text):
            found.setdefault(match.group(0), []).append(rel)
    invented = sorted(req_id for req_id in found if req_id not in catalog)
    assert not invented, (
        "RULES/ADR/src cite REQ IDs missing from the crosswalk CSV:\n"
        + "\n".join(f"  {req_id}: {sorted(set(found[req_id]))}" for req_id in invented)
    )


def test_req_arch_040_041_protocol_headings_present_in_rules() -> None:
    """REQ-ARCH-040/041 protocol headings must remain in RULES.md."""
    text = (_ROOT / "docs" / "00-project" / "RULES.md").read_text(encoding="utf-8")
    assert "Обязательная Двойная Верификация (REQ-ARCH-040)" in text
    assert "Причины Ложных Утверждений (REQ-ARCH-041)" in text
