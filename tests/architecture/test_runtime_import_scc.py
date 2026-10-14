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
"""Architecture regression tests for ownership-projection import SCC drift."""

from __future__ import annotations

from datetime import date
from functools import cache
from pathlib import Path

import pytest

from scripts.engineering.qa.import_graph_inventory import (
    RESOLUTION_RESOLVED,
    SYNTAX_IMPORT,
    SYNTAX_IMPORT_FROM,
    ImportEdge,
    ImportGraphReport,
    collect_import_graph,
    find_import_sccs,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENFORCED_IMPORT_GRAPH_PROJECTION = "static_runtime_base_modules"
REVIEWED_RUNTIME_SCC_BUDGET_MAX = 1
REVIEWED_RUNTIME_SCC_MIN_REVIEW_DATE = date(2026, 7, 1)
ACCEPTED_RUNTIME_SCCS: dict[frozenset[str], dict[str, str]] = {
    frozenset(
        {
            "bioetl.interfaces.http.control_plane_identity.anchor_values",
            "bioetl.interfaces.http.control_plane_identity.checkpoint_extractors",
            "bioetl.interfaces.http.control_plane_identity.ledger_extractors",
            "bioetl.interfaces.http.control_plane_identity.manifest_extractors",
            "bioetl.interfaces.http.control_plane_identity.replay_extractors",
        }
    ): {
        "owner": "interfaces.http.control_plane_identity",
        "review_date": "2026-07-07",
        "linked_issue": "#6037",
        "rationale": (
            "Control plane identity extractors form a cohesive functional group "
            "that share common formatting utilities and domain model imports. "
            "The cycle enables shared extraction logic across manifest, ledger, "
            "checkpoint, and replay surfaces without code duplication. "
            "The #6037 refresh keeps this acceptance explicitly reviewed while "
            "the extractor family remains under the accepted SCC inventory budget."
        ),
    },
}
FORBIDDEN_RUNTIME_SCCS: tuple[frozenset[str], ...] = (
    frozenset(
        {
            "bioetl.domain.control_plane.run_ledger",
            "bioetl.domain.control_plane.run_ledger_replay",
        }
    ),
    frozenset(
        {
            "bioetl.application.core._record_normalization_runtime_support",
            "bioetl.application.core.record_normalization_processor",
        }
    ),
    frozenset(
        {
            "bioetl.domain.behavior._dq_rule_evaluators",
            "bioetl.domain.behavior._dq_rule_evaluators_cross",
        }
    ),
    frozenset(
        {
            "bioetl.domain.control_plane._reproducibility_profile_builders",
            "bioetl.domain.control_plane.reproducibility_profiles",
        }
    ),
    frozenset(
        {
            "bioetl.composition._services",
            "bioetl.composition.factories.services.workflow_services",
        }
    ),
    frozenset(
        {
            "bioetl.application.composite.checkpoint._state_support",
            "bioetl.application.composite.checkpoint.state",
        }
    ),
)


@cache
def _runtime_import_report() -> ImportGraphReport:
    """Collect the canonical first-party graph once for this test process."""
    return collect_import_graph(REPO_ROOT)


def _static_runtime_edges(report: ImportGraphReport) -> tuple[ImportEdge, ...]:
    """Project canonical ownership edges onto the historical static SCC view.

    The ratchet predates dynamic-import ownership and follows each ``Import``
    target plus the base module of ``ImportFrom`` statements. Reusing the shared
    collector keeps parsing, TYPE_CHECKING handling, and module resolution
    canonical without silently widening this shrink-only baseline.
    """
    grouped: dict[tuple[str, str, int, str], list[ImportEdge]] = {}
    for edge in report.projections.ownership:
        if edge.syntax not in {SYNTAX_IMPORT, SYNTAX_IMPORT_FROM}:
            continue
        key = (edge.source, edge.file, edge.line, edge.syntax)
        grouped.setdefault(key, []).append(edge)

    selected: list[ImportEdge] = []
    for key, edges in sorted(grouped.items()):
        syntax = key[3]
        if syntax == SYNTAX_IMPORT or any(edge.target == "bioetl" for edge in edges):
            selected.extend(edges)
            continue
        selected.append(
            min(edges, key=lambda edge: (edge.target.count("."), edge.target))
        )
    return tuple(selected)


def _runtime_import_sccs() -> tuple[frozenset[str], ...]:
    report = _runtime_import_report()
    return find_import_sccs(_static_runtime_edges(report))


@pytest.mark.architecture
def test_runtime_import_graph_has_no_forbidden_sccs() -> None:
    """Ownership-projection SCC scan must stay clear of confirmed cycles."""
    blocked = [
        sorted(component)
        for component in _runtime_import_sccs()
        if component in FORBIDDEN_RUNTIME_SCCS
    ]
    assert not blocked, (
        "Runtime import SCC scan found forbidden strongly connected components "
        f"(projection={ENFORCED_IMPORT_GRAPH_PROJECTION}; "
        "TYPE_CHECKING imports are ignored):\n"
        + "\n".join(f"- {', '.join(component)}" for component in blocked)
    )


@pytest.mark.architecture
def test_runtime_import_graph_has_no_unreviewed_sccs() -> None:
    """Ownership-projection SCCs must be explicitly owned and reviewed."""
    actual_sccs = _runtime_import_sccs()
    accepted_sccs = set(ACCEPTED_RUNTIME_SCCS)
    unreviewed = [
        sorted(component) for component in actual_sccs if component not in accepted_sccs
    ]
    stale_acceptances = [
        sorted(component) for component in accepted_sccs if component not in actual_sccs
    ]

    assert not unreviewed, (
        "Runtime import SCC scan found unreviewed strongly connected components "
        f"(projection={ENFORCED_IMPORT_GRAPH_PROJECTION}). Either remove the cycle "
        "or add an "
        "owner/rationale/review_date entry to ACCEPTED_RUNTIME_SCCS:\n"
        + "\n".join(f"- {', '.join(component)}" for component in unreviewed)
    )
    assert not stale_acceptances, (
        "Runtime import SCC acceptances are stale; remove the entries after "
        "breaking the cycles:\n"
        + "\n".join(f"- {', '.join(component)}" for component in stale_acceptances)
    )


@pytest.mark.architecture
def test_runtime_import_scc_uses_shared_canonical_collector() -> None:
    """The historical SCC projection is derived from the shared import inventory."""
    report = _runtime_import_report()
    assert not report.failures, "\n".join(
        f"{failure.file}: {failure.reason}: {failure.detail}"
        for failure in report.failures
    )
    selected = _static_runtime_edges(report)
    ownership_edges = set(report.projections.ownership)
    assert selected
    assert all(
        edge.resolution == RESOLUTION_RESOLVED
        and edge.syntax in {SYNTAX_IMPORT, SYNTAX_IMPORT_FROM}
        and edge in ownership_edges
        for edge in selected
    )


@pytest.mark.architecture
def test_runtime_import_scc_review_inventory_is_ratcheted_for_5427_and_6059() -> None:
    """#5427/#6059: reviewed runtime import SCC inventory must stay ratcheted."""
    assert len(ACCEPTED_RUNTIME_SCCS) == REVIEWED_RUNTIME_SCC_BUDGET_MAX

    for component, metadata in ACCEPTED_RUNTIME_SCCS.items():
        assert component
        assert len(component) > 1
        assert set(metadata) >= {
            "owner",
            "review_date",
            "linked_issue",
            "rationale",
        }
        assert metadata["owner"].strip()
        assert metadata["linked_issue"].startswith("#")
        review_date = date.fromisoformat(metadata["review_date"])
        assert review_date >= REVIEWED_RUNTIME_SCC_MIN_REVIEW_DATE
        assert metadata["rationale"].strip()
