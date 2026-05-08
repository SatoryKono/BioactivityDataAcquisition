from __future__ import annotations

from pathlib import Path


def test_design_system_documents_query_duplication_policy() -> None:
    """Dashboard design docs must define duplicate-query governance."""
    text = Path("docs/03-guides/dashboards/design-system.md").read_text(
        encoding="utf-8"
    )
    required_tokens = {
        "PromQL duplication policy",
        "report-dashboard-query-duplicates",
        "Exact duplicate PromQL across more than one panel",
        "Current audited exact-duplicate reuse",
        "Justified exact duplicates MUST remain audited",
    }
    missing = sorted(token for token in required_tokens if token not in text)
    assert not missing, (
        "dashboard design-system must document duplicate-query governance; "
        f"missing={missing}"
    )
