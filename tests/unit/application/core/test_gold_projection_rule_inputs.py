"""Gold rules see normalized companion fields before storage-schema projection."""

from unittest.mock import AsyncMock

import pandera.pandas as pa
import pytest

from bioetl.domain.config.validation import CrossFieldValidation
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.domain.types.gold_contracts import GoldWriteCategory
from tests.unit.application.core.test_gold_outcome_quarantine_routing import (
    _config,
    _gold_validator,
    _writer,
)
from tests.helpers.deterministic_ids import deterministic_batch_uuid_from_callsite

pytestmark = pytest.mark.unit


def test_rule_inputs_must_retain_projected_row_alignment():
    schema = pa.DataFrameSchema({"entity_id": pa.Column(str)})
    validator = _gold_validator(schema, _config())
    with pytest.raises(ValueError, match="projected row alignment"):
        validator.validate_with_rule_inputs([{"entity_id": "row"}], [])


def test_rule_input_entry_point_preserves_schema_validation_without_dq_policy():
    from bioetl.infrastructure.validation.contract_validator import (
        ContractAwareGoldValidator,
    )

    validator = ContractAwareGoldValidator(pa.DataFrameSchema({"id": pa.Column(int)}))
    assert not validator.validate_with_rule_inputs(
        [{"id": "invalid"}], [{"id": "invalid"}]
    ).is_valid


@pytest.mark.asyncio
async def test_cross_field_rules_run_before_gold_projection_removes_companion():
    schema = pa.DataFrameSchema({"entity_id": pa.Column(str), "clo_id": pa.Column(str)})
    config = _config(
        cross_field_validations=(
            CrossFieldValidation(
                name="clo_id_requires_mapping_status",
                fields=("clo_id", "clo_mapping_status"),
                condition="conditional_required",
                trigger_field="clo_id",
                required_field="clo_mapping_status",
            ),
        ),
        disposition_overrides=(
            ("cross.clo_id_requires_mapping_status", DQDisposition.QUARANTINE),
        ),
    )
    quarantine = AsyncMock()
    writer, storage = _writer(
        _gold_validator(schema, config), quarantine, schema=schema
    )
    writer.bind_gold_quarantine_batch(
        deterministic_batch_uuid_from_callsite("projection_companion")
    )
    records = [
        {"entity_id": "valid", "clo_id": "CLO_0008331", "clo_mapping_status": "mapped"},
        {"entity_id": "invalid", "clo_id": "CLO_0008331", "clo_mapping_status": None},
    ]
    receipt = await writer.write_gold(records)
    assert receipt.category == GoldWriteCategory.COMPLETE
    written = storage.write_gold.await_args.kwargs["records"]
    assert written == [{"entity_id": "valid", "clo_id": "CLO_0008331"}]
    assert writer._last_gold_outcome_quarantine_count == 1
    quarantine.write_many.assert_awaited_once()
