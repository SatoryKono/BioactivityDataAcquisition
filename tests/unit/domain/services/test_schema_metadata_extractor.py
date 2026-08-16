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
"""Domain-pure tests for schema metadata extraction rules."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.schema_metadata_extractor import extract_schema_metadata
from bioetl.domain.models.metadata import (
    SchemaColumnInspection,
    SchemaInspectionResult,
)


pytestmark = pytest.mark.unit


def test_extract_schema_metadata_none_returns_defaults() -> None:
    metadata = extract_schema_metadata(None)
    assert metadata.contract_path is None
    assert metadata.version == "1.0"
    assert metadata.validation == "strict"
    assert metadata.columns == []


def test_extract_schema_metadata_from_schema_with_columns() -> None:
    metadata = extract_schema_metadata(
        SchemaInspectionResult(
            version="2",
            validation="lenient",
            columns=(
                SchemaColumnInspection(
                    name="entity_id",
                    dtype="pandera.dtypes.String",
                    nullable=False,
                ),
                SchemaColumnInspection(
                    name="score",
                    dtype="pandera.dtypes.Float64",
                    nullable=True,
                ),
            ),
        )
    )

    assert metadata.version == "2"
    assert metadata.validation == "lenient"
    assert len(metadata.columns) == 2
    assert metadata.columns[0].name == "entity_id"
    assert metadata.columns[0].type == "String"
    assert metadata.columns[0].nullable is False
    assert metadata.columns[1].name == "score"
    assert metadata.columns[1].type == "Float64"
    assert metadata.columns[1].nullable is True


def test_extract_schema_metadata_handles_empty_inspection_columns() -> None:
    metadata = extract_schema_metadata(
        SchemaInspectionResult(version="3.1.0", validation="strict")
    )
    assert metadata.version == "3.1.0"
    assert metadata.validation == "strict"
    assert metadata.columns == []


def test_extract_schema_metadata_contract_path_vector() -> None:
    metadata = extract_schema_metadata(
        SchemaInspectionResult(
            contract_path="src/bioetl/domain/contracts/gold/fake_schema.py"
        )
    )
    assert metadata.contract_path == "src/bioetl/domain/contracts/gold/fake_schema.py"
