"""Focused routing coverage for Gold DQ and removed evidence inputs."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit


def test_shadow_compare_routes_gold_dq_and_deleted_evidence() -> None:
    """Changed Gold DQ configs and removed evidence keep explicit routes."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            *(
                f"configs/quality/entities/composite/{entity}.yaml"
                for entity in (
                    "activity",
                    "assay",
                    "molecule",
                    "publication",
                    "target",
                )
            ),
            "configs/quality/domain_aggregate_classification.yaml",
            "reports/12592_report.md",
            "reports/12592_scoped_patch.diff",
        ],
        repo_root=repo_root,
    )

    assert (
        "tests/unit/composition/bootstrap/runtime/test_composite_config_loader.py"
        in report["selected"]
    )
    assert (
        "tests/unit/infrastructure/schemas/test_composite_gold_dq.py"
        in report["selected"]
    )
    assert (
        "tests/architecture/test_domain_aggregate_classification.py"
        in report["selected"]
    )
    assert (
        "tests/architecture/test_documentation_cleanup_inventory.py"
        in report["selected"]
    )
    assert "tests/architecture/test_check_doc_links_guardrails.py" in report["selected"]
