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
"""Same-path owner tests for PubChem pipeline transformer module."""

from __future__ import annotations

import pytest

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.pipelines.pubchem.transformer import (
    PubChemCompoundTransformer,
    __all__,
)


pytestmark = pytest.mark.unit


def test_pubchem_transformer_is_canonical_base_transformer_subclass() -> None:
    assert issubclass(PubChemCompoundTransformer, BaseTransformer)


def test_pubchem_transformer_module_exports_single_transformer_entrypoint() -> None:
    assert __all__ == ["PubChemCompoundTransformer"]
