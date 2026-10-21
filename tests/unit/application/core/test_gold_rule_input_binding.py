"""Gold renames retain pre-transform DQ values without leaking Silver-only keys."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, Mock

import pandera.pandas as pa
import pytest

from bioetl.application.core._gold_rule_inputs import (
    bind_gold_rule_inputs,
    resolve_gold_rule_inputs,
)
from bioetl.application.core.batch_transformer_attempt_success import _build_gold_record
from bioetl.domain.config.validation import CrossFieldValidation
from bioetl.domain.types.dq_contracts import DQDisposition
from tests.helpers.deterministic_ids import deterministic_batch_uuid_from_callsite
from tests.unit.application.core.test_gold_outcome_quarantine_routing import (
    _config,
    _gold_validator,
    _writer,
)

pytestmark = pytest.mark.unit


def test_bound_rule_inputs_are_a_snapshot_outside_the_persisted_mapping():
    original = {"entity_id": "row", "assay_description": "original"}
    gold = bind_gold_rule_inputs(
        {"entity_id": "row", "description": "original"}, original
    )
    original["assay_description"] = "changed"
    assert resolve_gold_rule_inputs([gold])[0]["assay_description"] == "original"
    assert json.loads(json.dumps(gold)) == {
        "entity_id": "row",
        "description": "original",
    }
    resolved = resolve_gold_rule_inputs([gold])
    resolved[0]["assay_description"] = "changed copy"
    assert resolve_gold_rule_inputs([gold])[0]["assay_description"] == "original"


def test_absent_gold_output_stays_absent():
    assert bind_gold_rule_inputs(None, {"entity_id": "row"}) is None


def test_direct_gold_record_retains_its_existing_rule_input_contract():
    record = {"entity_id": "row", "description": "direct"}
    assert resolve_gold_rule_inputs([record])[0] is record


def test_gold_transform_cannot_attach_another_records_rule_inputs():
    with pytest.raises(ValueError, match="changed record identity"):
        bind_gold_rule_inputs({"entity_id": "other"}, {"entity_id": "row"})


@pytest.mark.asyncio
async def test_renamed_gold_description_does_not_quarantine_valid_silver_input():
    schema = pa.DataFrameSchema(
        {
            "entity_id": pa.Column(str),
            "assay_id": pa.Column(str),
            "description": pa.Column(str, nullable=True),
        }
    )
    config = _config(
        cross_field_validations=(
            CrossFieldValidation(
                name="assay_identifiable",
                fields=("assay_id", "assay_description"),
                condition="all_present",
            ),
        ),
        disposition_overrides=(("cross.assay_identifiable", DQDisposition.QUARANTINE),),
    )
    quarantine = AsyncMock()
    writer, storage = _writer(
        _gold_validator(schema, config), quarantine, schema=schema
    )
    writer.bind_gold_quarantine_batch(
        deterministic_batch_uuid_from_callsite("renamed_gold_description")
    )

    def rename(context, silver):
        gold = dict(silver)
        gold["description"] = gold.pop("assay_description")
        return gold

    records = []
    for entity_id, description in (
        ("valid", "Recorded assay description"),
        ("invalid", None),
    ):
        silver = {
            "entity_id": entity_id,
            "assay_id": "CHEMBL615159",
            "assay_description": description,
        }
        gold, excluded, details = _build_gold_record(
            context=Mock(),
            silver_record=silver,
            gold_filter=lambda *args: True,
            gold_transform=rename,
        )
        assert not excluded and details is None and "assay_description" not in gold
        records.append(gold)
    await writer.write_gold(records)
    assert storage.write_gold.await_args.kwargs["records"] == [
        {
            "entity_id": "valid",
            "assay_id": "CHEMBL615159",
            "description": "Recorded assay description",
        }
    ]
    assert writer._last_gold_outcome_quarantine_count == 1
    assert (
        quarantine.write_many.await_args.args[0][0]["payload"]["entity_id"] == "invalid"
    )
