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
"""ARCH-CR-02: legacy composite stub detection is path-based only."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.composition.factories.pipeline_support.registry_validation_helpers import (
    _is_legacy_composite_entity_stub,
)

pytestmark = pytest.mark.unit


def test_legacy_stub_detected_by_parent_directory_only(tmp_path: Path) -> None:
    composite_dir = tmp_path / "entities" / "composite"
    composite_dir.mkdir(parents=True)
    stub = composite_dir / "activity.yaml"
    # Provider field intentionally missing/misleading must not matter.
    stub.write_text("entity: activity\nprovider: chembl\n", encoding="utf-8")
    assert _is_legacy_composite_entity_stub(stub) is True


def test_non_legacy_provider_composite_yaml_is_not_stub(tmp_path: Path) -> None:
    chembl_dir = tmp_path / "entities" / "chembl"
    chembl_dir.mkdir(parents=True)
    impostor = chembl_dir / "activity.yaml"
    impostor.write_text("entity: activity\nprovider: composite\n", encoding="utf-8")
    assert _is_legacy_composite_entity_stub(impostor) is False
