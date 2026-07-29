# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
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
