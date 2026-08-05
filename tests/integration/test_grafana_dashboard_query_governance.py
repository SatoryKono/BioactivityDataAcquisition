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
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

# Active SSOT only — archived dashboard drafts (#7588) must not be treated as
# current normative surfaces for query-policy assertions.
_QUERY_POLICY_DOCS = (
    Path("docs/03-guides/dashboards/design-system.md"),
)


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


def test_query_policy_docs_track_resolved_dq_time_semantics() -> None:
    normalized_by_path = {
        path: " ".join(path.read_text(encoding="utf-8").split())
        for path in _QUERY_POLICY_DOCS
    }
    for path, normalized in normalized_by_path.items():
        lowered = normalized.lower()
        assert "share expression intentionally" not in lowered, path
        assert "share one weighted-score expression intentionally" not in lowered, path
        assert "distinct time semantics" in lowered, path

    combined = " ".join(normalized_by_path.values())
    for token in (
        "bioetl_dq_current_status",
        "bioetl_runtime_current_status_trusted",
        "[7d]",
        "selected-range",
        "UNKNOWN",
    ):
        assert token in combined


def test_grafana_readme_documents_current_dq_weighted_score_semantics() -> None:
    text = Path("grafana/README.md").read_text(encoding="utf-8")
    heading = "### 18.2 Data Quality Score (Volume-weighted)"
    section = text[text.index(heading) :].split("\n### ", maxsplit=1)[0]

    for token in (
        "last_over_time(bioetl_dq_validation_score",
        "last_over_time(bioetl_dq_validation_record_count",
        "[7d]",
        "selected-range",
        "UNKNOWN",
    ):
        assert token in section
    assert "or vector(0)" not in section
