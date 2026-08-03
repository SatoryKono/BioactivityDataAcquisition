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
"""Same-path owner tests for Semantic Scholar publication schema module."""

from __future__ import annotations

import pytest

from bioetl.domain.schemas.common.publication_base import PublicationBaseSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
    __all__,
)


pytestmark = pytest.mark.unit


def test_semanticscholar_publication_schema_extends_publication_base_schema() -> None:
    assert issubclass(SemanticScholarPublicationSchema, PublicationBaseSchema)


def test_semanticscholar_publication_schema_declares_provider_specific_columns() -> (
    None
):
    schema = SemanticScholarPublicationSchema.to_schema()
    assert "paper_id" in schema.columns
    assert "_lookup_method" in schema.columns
    assert "tldr" in schema.columns
    assert "SemanticScholarPublicationSchema" in __all__
