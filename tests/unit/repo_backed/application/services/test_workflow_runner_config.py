"""Repository-backed workflow configuration contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.workflow_config_api import load_workflow_config


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def test_chembl_baseline_declares_expected_pipeline_universe() -> None:
    """Keep the file-backed workflow contract outside the pure-unit lane."""
    config = load_workflow_config(
        "chembl_baseline",
        config_dir=Path("configs/workflows"),
    )

    assert config.name == "chembl_baseline"
    assert [
        (
            step.pipeline_name,
            config.defaults.merged_with(step.run_options).run_type,
        )
        for step in config.pipeline_steps
    ] == [
        ("chembl_assay", "backfill"),
        ("chembl_target", "backfill"),
        ("chembl_publication", "backfill"),
    ]
