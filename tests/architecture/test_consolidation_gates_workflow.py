"""Architecture contracts for the consolidation quality workflow."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


CONSOLIDATION_WORKFLOW = Path(".github/workflows/consolidation-gates.yml")
PYCHARM_MYPY_CONFIGURATION = Path("configs/ide/pycharm/runConfigurations/Mypy_Full.xml")
pytestmark = pytest.mark.architecture


def test_consolidation_workflow_is_evidence_only() -> None:
    """Consolidation must not duplicate blocking selectors owned elsewhere."""
    workflow = CONSOLIDATION_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "canonical-manifest-hashes:" in workflow
    assert "mypy" not in workflow
    assert "pytest" not in workflow


def test_pycharm_mypy_matches_canonical_product_scope() -> None:
    """The shared PyCharm runner must use the zero-error CI product scope."""
    root = ET.parse(PYCHARM_MYPY_CONFIGURATION).getroot()
    parameters = root.find(".//option[@name='PARAMETERS']")

    assert parameters is not None
    assert parameters.get("value") == (
        "--config-file pyproject.toml --strict --no-incremental src/bioetl"
    )


def test_consolidation_hash_lane_materializes_and_uploads_both_trees() -> None:
    """Evidence lane must publish deterministic hashes for tests and source."""
    workflow = CONSOLIDATION_WORKFLOW.read_text(encoding="utf-8")

    assert "find tests -type f | sort | xargs sha256sum" in workflow
    assert "find src -type f | sort | xargs sha256sum" in workflow
    assert "name: canonical-manifest-hashes" in workflow
    assert "path: reports/gates/artifacts" in workflow
    assert "if-no-files-found: error" in workflow
