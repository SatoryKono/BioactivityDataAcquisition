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
"""Tests for CLI bootstrap config helpers."""

from __future__ import annotations

import pytest

from bioetl.composition.bootstrap.cli.config_helpers import get_pipeline_yaml_for_dq

pytestmark = pytest.mark.unit


class _ModelDumpConfig:
    def model_dump(self) -> dict[str, object]:
        return {"provider": "chembl", "entity": "activity"}


def test_get_pipeline_yaml_for_dq_uses_model_dump_when_available() -> None:
    payload = get_pipeline_yaml_for_dq(
        "chembl_activity",
        pipeline_config_loader=lambda _: _ModelDumpConfig(),
    )

    assert payload == {"provider": "chembl", "entity": "activity"}


def test_get_pipeline_yaml_for_dq_copies_mapping_payload() -> None:
    source = {"provider": "pubmed", "entity": "publication"}

    payload = get_pipeline_yaml_for_dq(
        "pubmed_publication",
        pipeline_config_loader=lambda _: source,
    )

    assert payload == source
    assert payload is not source


def test_get_pipeline_yaml_for_dq_rejects_unsupported_config_types() -> None:
    with pytest.raises(
        TypeError,
        match="Pipeline YAML config must provide model_dump\\(\\) or be a mapping",
    ):
        get_pipeline_yaml_for_dq(
            "invalid",
            pipeline_config_loader=lambda _: object(),
        )
