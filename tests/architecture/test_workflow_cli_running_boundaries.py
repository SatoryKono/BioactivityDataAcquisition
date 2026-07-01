"""Architecture tests for workflow inventory, CLI reference, and running-pipelines guide ownership boundaries."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def test_workflow_catalog_declares_inventory_boundary() -> None:
    """Workflow catalog must explicitly state it is inventory-only, not lifecycle/CLI guide."""
    workflow_catalog = Path("docs/04-reference/workflow-catalog.md").read_text(encoding="utf-8")

    assert "Boundary:" in workflow_catalog
    assert "inventory" in workflow_catalog.lower()
    assert "CLI Reference" in workflow_catalog
    assert "Running Pipelines" in workflow_catalog


def test_cli_reference_declares_command_boundary() -> None:
    """CLI reference must explicitly state it is command reference, not execution guide."""
    cli_ref = Path("docs/04-reference/cli.md").read_text(encoding="utf-8")

    assert "Boundary:" in cli_ref
    assert "CLI command reference" in cli_ref
    assert "Running Pipelines" in cli_ref
    assert "Workflow Catalog" in cli_ref


def test_running_pipelines_declares_execution_boundary() -> None:
    """Running pipelines guide must explicitly state it owns execution flow, not CLI/inventory."""
    running_pipelines = Path("docs/03-guides/running-pipelines.md").read_text(encoding="utf-8")

    assert "Boundary:" in running_pipelines
    assert "execution" in running_pipelines.lower()
    assert "CLI Reference" in running_pipelines
    assert "Workflow Catalog" in running_pipelines


def test_workflow_catalog_lacks_cli_examples() -> None:
    """Workflow catalog should not contain CLI command examples."""
    workflow_catalog = Path("docs/04-reference/workflow-catalog.md").read_text(encoding="utf-8")

    # Should not have CLI command blocks
    assert "```bash" not in workflow_catalog
    assert "bioetl run" not in workflow_catalog
    assert "bioetl workflow" not in workflow_catalog


def test_cli_reference_lacks_workflow_inventory() -> None:
    """CLI reference should not duplicate workflow inventory."""
    cli_ref = Path("docs/04-reference/cli.md").read_text(encoding="utf-8")

    # Should not duplicate workflow YAML contract
    assert "schema_version" not in cli_ref or "workflow:" not in cli_ref


def test_running_pipelines_lacks_workflow_inventory() -> None:
    """Running pipelines guide should not duplicate workflow inventory."""
    running_pipelines = Path("docs/03-guides/running-pipelines.md").read_text(encoding="utf-8")

    # Should not duplicate workflow YAML contract
    assert "schema_version" not in running_pipelines or "workflow:" not in running_pipelines


def test_quick_start_uses_correct_cli_description() -> None:
    """Quick start should not claim running-pipelines is comprehensive CLI reference."""
    quick_start = Path("docs/03-guides/quick-start.md").read_text(encoding="utf-8")

    # Should not say "Comprehensive CLI reference"
    assert "Comprehensive CLI reference" not in quick_start
