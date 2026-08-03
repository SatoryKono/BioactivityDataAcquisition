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
"""Contracts for derived ChEMBL subcellular-fraction raw/canonical seams."""

from __future__ import annotations

import pytest

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.core.subcellular_fraction_data_source import (
    SubcellularFractionDataSource,
)
from tests.unit.application.core.test_subcellular_fraction_data_source import (
    ASSAY_CANONICAL_VARIANT_FRACTION,
    ASSAY_WITH_FRACTION,
    MockDataSource,
)


async def _collect(async_iterable):
    rows = []
    async for row in async_iterable:
        rows.append(row)
    return rows


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subcellular_fraction_datasource_dedup_path_keeps_raw_sidecar_optional() -> (
    None
):
    wrapper = SubcellularFractionDataSource(
        data_source=MockDataSource(
            assays=[ASSAY_WITH_FRACTION, ASSAY_CANONICAL_VARIANT_FRACTION]
        )
    )

    records = await _collect(wrapper.fetch("subcellular_fraction"))

    assert len(records) == 1
    assert "subcellular_fraction_raw" not in records[0]

    normalized = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="subcellular_fraction",
    ).normalize_business_data(records[0])
    assert normalized["subcellular_fraction"] == "Microsomes"
    assert normalized.get("subcellular_fraction_raw") is None
