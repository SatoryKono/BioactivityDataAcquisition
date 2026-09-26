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
"""Ownership tests for ChEMBL transformer/profile normalization boundaries."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.unit


def test_pure_bao_and_organism_normalization_is_not_transformer_owned() -> None:
    transformer_dir = Path("src/bioetl/application/pipelines/chembl")
    transformer_sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in transformer_dir.glob("*_transformer.py")
    }

    for filename, source in transformer_sources.items():
        assert "normalize_bao_identifier" not in source, filename
        assert "normalize_chembl_organism_name" not in source, filename

    assay_profile_source = Path(
        "src/bioetl/domain/normalization/profiles/chembl_assay.py"
    ).read_text(encoding="utf-8")
    assert "normalize_bao_label" in assay_profile_source
