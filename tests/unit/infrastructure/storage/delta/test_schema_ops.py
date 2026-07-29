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
from __future__ import annotations

import pytest

import pyarrow as pa

from bioetl.infrastructure.storage.delta.schema_ops import (
    drop_nondeterministic_persisted_fields,
)


pytestmark = pytest.mark.unit


def test_drop_nondeterministic_persisted_fields_removes_runtime_provenance() -> None:
    table = pa.table(
        {
            "entity_id": ["chembl:1"],
            "_run_id": ["run-1"],
            "_run_type": ["incremental"],
            "_source_batch_id": ["batch-1"],
            "_ingestion_ts": ["2026-04-10T14:00:00Z"],
            "_composite_run_id": ["composite-1"],
            "_lineage_created_at": ["2026-04-10T14:00:01Z"],
        }
    )

    result = drop_nondeterministic_persisted_fields(table)

    assert result.column_names == ["entity_id"]
