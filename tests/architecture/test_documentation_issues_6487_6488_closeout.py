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
"""Closeout guards for documentation drift issues #6487 and #6488."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
    SinkLayerConfig,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
WORKFLOW_INVENTORY = ROOT / "docs" / "04-reference" / "github-actions-workflows.md"
PIPELINE_CATALOG = ROOT / "docs" / "04-reference" / "pipeline-catalog.md"
PIPELINE_COVERAGE = ROOT / "docs" / "04-reference" / "pipelines" / "INDEX.md"


def test_issue_6487_inventory_count_and_docs_workflow_are_source_derived() -> None:
    """The published count and docs workflow must match tracked workflow YAML."""
    live_workflows = sorted(WORKFLOW_DIR.glob("*.yml"))
    inventory = WORKFLOW_INVENTORY.read_text(encoding="utf-8")

    count_match = re.search(
        r"inventory of the \*\*(\d+)\*\* live GitHub Actions", inventory
    )
    assert count_match is not None
    assert live_workflows
    assert int(count_match.group(1)) == len(live_workflows)
    assert WORKFLOW_DIR.joinpath("docs.yml") in live_workflows
    assert "| `docs.yml` | `Docs & Diagrams` |" in inventory


def test_issue_6488_gold_runtime_is_not_inferred_from_input_filter_flags() -> None:
    """An unrelated disabled input filter must not disable the Gold sink."""
    molecule_config = yaml.safe_load(
        (ROOT / "configs" / "entities" / "chembl" / "molecule.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert molecule_config["filters"]["input_filter"]["enabled"] is False
    assert "enabled" not in molecule_config["pipeline"]["sink"]["gold"]
    assert (
        SinkLayerConfig.model_validate(
            molecule_config["pipeline"]["sink"]["gold"]
        ).enabled
        is True
    )

    catalog = PIPELINE_CATALOG.read_text(encoding="utf-8")
    coverage = PIPELINE_COVERAGE.read_text(encoding="utf-8")
    molecule_catalog_row = next(
        line for line in catalog.splitlines() if line.startswith("| `chembl_molecule`")
    )
    molecule_coverage_row = next(
        line for line in coverage.splitlines() if line.startswith("| `chembl_molecule`")
    )

    assert molecule_catalog_row.endswith("| enabled (default) |")
    assert "| Direct | Enabled |" in molecule_coverage_row
    assert "`filters.input_filter.enabled: false`" in coverage
