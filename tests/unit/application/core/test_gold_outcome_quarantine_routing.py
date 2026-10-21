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
"""Gold write-path consumption of attributed DQ outcomes."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pandera.pandas as pa
import pytest

from bioetl.application.core._gold_outcome_disposition import plan_gold_outcome_write
from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_writer import BatchWriter, BatchWriterOptions
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.validation import FieldValidation
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.types import RunType
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.domain.types.gold_contracts import GoldWriteCategory, GoldWriteReceipt
from bioetl.infrastructure.validation.contract_validator import (
    ContractAwareGoldValidator,
)
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid_from_callsite,
    deterministic_uuid_from_callsite,
)

pytestmark = pytest.mark.unit

_SCHEMA = pa.DataFrameSchema(
    {
        "entity_id": pa.Column(str),
        "name": pa.Column(str, nullable=True),
    }
)


def _config(**kwargs: object) -> DQConfig:
    base: dict[str, object] = {
        "contract_ref": "gold.molecule",
        "contract_version": "1.0.0",
        "rule_bundle_version": "1.0.0",
    }
    base.update(kwargs)
    return DQConfig(**base)  # type: ignore[arg-type]


def _writer(
    validator: ContractAwareGoldValidator,
    quarantine: AsyncMock,
    *,
    schema: pa.DataFrameSchema | None = None,
) -> tuple[BatchWriter, AsyncMock]:
    storage = AsyncMock()
    storage.write_gold = AsyncMock(
        return_value=GoldWriteReceipt(
            "synthetic",
            "1.0.0",
            GoldWriteCategory.COMPLETE,
            ("synthetic",),
        )
    )
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    context = PipelineContext(
        run_id=deterministic_uuid_from_callsite("test_gold_outcome_quarantine_routing"),
        run_type=RunType.INCREMENTAL,
        logger=logger,
        started_at=datetime(2026, 10, 21, tzinfo=UTC),
    )
    writer = BatchWriter(
        storage=storage,
        context=context,
        config=RecordProcessorConfig(
            pipeline_name="chembl_molecule",
            provider="chembl",
            entity_type="molecule",
            silver_schema=MagicMock(),
            gold_schema=schema if schema is not None else _SCHEMA,
            dq_config=validator._dq_config,
        ),
        gold_validator=validator,
        error_classifier=ErrorClassifier(),
        batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        options=BatchWriterOptions(gold_quarantine_port=quarantine),
    )
    return writer, storage


def test_parity_fail_closed_matches_strict_validate() -> None:
    schema = pa.DataFrameSchema({"field": pa.Column(str, nullable=False)})
    validator = ContractAwareGoldValidator(schema=schema, dq_config=DQConfig())
    writer, storage = _writer(validator, AsyncMock())
    records = [{"field": None}]
    direct = validator.validate(records)
    with pytest.raises(SchemaViolationError) as caught:
        writer._prepare_gold_records(records)
        from bioetl.application.core._batch_writer_gold_support import (
            validate_gold_records,
        )

        validate_gold_records(writer, records)
    assert caught.value.errors == list(direct.errors)
    storage.write_gold.assert_not_called()


def test_fail_disposition_stays_batch_fail_closed() -> None:
    validator = ContractAwareGoldValidator(
        schema=_SCHEMA,
        dq_config=_config(
            field_validations=(
                FieldValidation(
                    field="name",
                    validation_type="required",
                    severity="error",
                ),
            ),
            disposition_overrides=(("field.name.required", DQDisposition.FAIL),),
        ),
    )
    writer, _storage = _writer(validator, AsyncMock())
    with pytest.raises(SchemaViolationError):
        from bioetl.application.core._batch_writer_gold_support import (
            validate_gold_records,
        )

        validate_gold_records(
            writer,
            [{"entity_id": "a", "name": None}, {"entity_id": "b", "name": "ok"}],
        )


def test_unattributable_schema_error_stays_fail_closed() -> None:
    strict = pa.DataFrameSchema({"name": pa.Column(str, nullable=True)}, strict=True)
    validator = ContractAwareGoldValidator(
        schema=strict,
        dq_config=_config(
            field_validations=(
                FieldValidation(
                    field="name",
                    validation_type="required",
                    severity="warn",
                ),
            )
        ),
    )
    writer, _storage = _writer(validator, AsyncMock())
    direct = validator.validate([{"name": "ok", "extra": 1}])
    with pytest.raises(SchemaViolationError) as caught:
        from bioetl.application.core._batch_writer_gold_support import (
            validate_gold_records,
        )

        validate_gold_records(writer, [{"name": "ok", "extra": 1}])
    assert caught.value.errors == list(direct.errors)


def test_schema_override_quarantines_only_failing_row() -> None:
    schema = pa.DataFrameSchema(
        {
            "entity_id": pa.Column(str),
            "name": pa.Column(str, nullable=False),
        }
    )
    validator = ContractAwareGoldValidator(
        schema=schema,
        dq_config=_config(
            disposition_overrides=(("schema.name", DQDisposition.QUARANTINE),),
        ),
    )
    channel = validator.validate_with_outcomes(
        [
            {"entity_id": "keep", "name": "ok"},
            {"entity_id": "drop", "name": None},
        ]
    )
    plan = plan_gold_outcome_write(
        [
            {"entity_id": "keep", "name": "ok"},
            {"entity_id": "drop", "name": None},
        ],
        channel,
        validator._dq_config,
    )
    assert plan.fail_closed is False
    assert [row["entity_id"] for row in plan.records_to_write] == ["keep"]
    assert len(plan.quarantine_items) == 1
    assert plan.quarantine_items[0].record_key == "drop"
    assert plan.quarantine_items[0].source_index == 1
    assert plan.quarantine_items[0].rules[0].rule_id == "schema.name"
    assert plan.quarantine_items[0].rules[0].contract_ref == "gold.molecule"


@pytest.mark.asyncio
async def test_write_gold_routes_one_request_per_record_with_rule_metadata() -> None:
    schema = pa.DataFrameSchema(
        {
            "entity_id": pa.Column(str),
            "name": pa.Column(str, nullable=True),
            "smiles": pa.Column(str, nullable=True),
        }
    )
    validator = ContractAwareGoldValidator(
        schema=schema,
        dq_config=_config(
            field_validations=(
                FieldValidation(
                    field="name",
                    validation_type="required",
                    severity="error",
                ),
                FieldValidation(
                    field="smiles",
                    validation_type="required",
                    severity="error",
                ),
            )
        ),
    )
    quarantine = AsyncMock()
    quarantine.write_many = AsyncMock()
    writer, storage = _writer(validator, quarantine, schema=schema)
    batch_id = deterministic_batch_uuid_from_callsite(
        "test_gold_outcome_quarantine_routing"
    )
    writer.bind_gold_quarantine_batch(batch_id)
    records = [
        {"entity_id": "drop", "name": None},
        {"entity_id": "keep", "name": "ok", "smiles": "C"},
    ]
    await writer.write_gold(records)
    quarantine.write_many.assert_awaited_once()
    requests = quarantine.write_many.await_args.args[0]
    assert len(requests) == 1
    metadata = requests[0]["metadata"]
    assert metadata["rule_id"] == "field.name.required"
    assert metadata["contract_ref"] == "gold.molecule"
    assert metadata["config_path"] == "contracts/gold.molecule/dq_rules.yaml"
    assert [rule["rule_id"] for rule in metadata["rules"]] == [
        "field.name.required",
        "field.smiles.required",
    ]
    assert requests[0]["payload"]["entity_id"] == "drop"
    assert requests[0]["bronze_batch_id"] == batch_id
    written = storage.write_gold.await_args.kwargs["records"]
    assert [row["entity_id"] for row in written] == ["keep"]
    replay = validator.validate_with_outcomes(records)
    assert [item.outcome.disposition for item in replay.violations] == [
        item.outcome.disposition
        for item in validator.validate_with_outcomes(records).violations
    ]


def test_affected_fields_do_not_select_other_rows() -> None:
    schema = pa.DataFrameSchema({"name": pa.Column(str, nullable=False)})
    validator = ContractAwareGoldValidator(
        schema=schema,
        dq_config=_config(
            disposition_overrides=(("schema.name", DQDisposition.QUARANTINE),),
        ),
    )
    records = [{"name": "ok"}, {"name": None}]
    channel = validator.validate_with_outcomes(records)
    plan = plan_gold_outcome_write(records, channel, validator._dq_config)
    assert [row["name"] for row in plan.records_to_write] == ["ok"]
    assert plan.quarantine_items[0].source_index == 1
    assert plan.quarantine_items[0].record_key is None
