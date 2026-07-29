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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for lightweight composition config catalog helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.composition.config_catalog import list_configured_pipeline_names

pytestmark = pytest.mark.unit


def test_list_configured_pipeline_names_reads_entity_config_tree(
    tmp_path: Path,
) -> None:
    configs_root = tmp_path / "configs"
    (configs_root / "entities" / "chembl").mkdir(parents=True)
    (configs_root / "entities" / "composite").mkdir(parents=True)
    (configs_root / "entities" / "pubchem").mkdir(parents=True)
    (configs_root / "entities" / "chembl" / "activity.yaml").write_text(
        "provider: chembl\nentity_type: activity\n",
        encoding="utf-8",
    )
    (configs_root / "entities" / "pubchem" / "compound.yaml").write_text(
        "provider: pubchem\nentity_type: compound\n",
        encoding="utf-8",
    )
    (configs_root / "entities" / "composite" / "activity.yaml").write_text(
        "provider: composite\nentity_type: activity\n",
        encoding="utf-8",
    )

    assert list_configured_pipeline_names(configs_root=configs_root) == [
        "chembl_activity",
        "pubchem_compound",
    ]


def test_list_configured_pipeline_names_missing_root_is_empty(
    tmp_path: Path,
) -> None:
    assert list_configured_pipeline_names(configs_root=tmp_path / "configs") == []
