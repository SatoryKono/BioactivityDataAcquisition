"""Molecule provider codes survive both application finalization paths."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.exceptions.validation import ValidationError
from bioetl.domain.types import BronzeRecord, RunType, SilverRecord
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture
def transformer() -> MoleculeTransformer:
    return MoleculeTransformer(dependencies=build_test_transformer_dependencies())


@pytest.fixture
def context() -> PipelineContext:
    logger = MagicMock()
    logger.bind.return_value = logger
    return PipelineContext(
        run_id=deterministic_uuid_from_callsite("molecule_phase_contract"),
        run_type=RunType.INCREMENTAL,
        logger=logger,
    )


def _record(phase: str | float | None) -> BronzeRecord:
    return {
        "molecule_chembl_id": "CHEMBL25",
        "molecule_type": "Small molecule",
        "structure_type": "MOL",
        "inorganic_flag": 0,
        "max_phase": phase,
    }


async def _finalize(
    transformer: MoleculeTransformer,
    context: PipelineContext,
    record: BronzeRecord,
    *,
    staged: bool,
) -> SilverRecord | None:
    if not staged:
        return await transformer.transform(context, record, 0)
    pre_silver = await transformer.transform_pre_silver(context, record, 0)
    assert pre_silver is not None
    return RecordNormalizationProcessor(
        provider="chembl", entity_type="molecule"
    ).finalize_pre_silver(pre_silver, context, 0)


@pytest.mark.parametrize("staged", [False, True], ids=["direct", "staged"])
@pytest.mark.parametrize(
    ("raw", "expected"),
    [("4.0", 4), ("-1.0", -1), ("0.5", 0.5), (0.5, 0.5), (None, None)],
)
async def test_molecule_phase_survives_application_finalization(
    transformer: MoleculeTransformer,
    context: PipelineContext,
    raw: str | float | None,
    expected: float | None,
    staged: bool,
) -> None:
    result = await _finalize(transformer, context, _record(raw), staged=staged)

    assert result is not None
    assert result["max_phase"] == expected
    assert result["molecule_id"] == "CHEMBL25"


@pytest.mark.parametrize("staged", [False, True], ids=["direct", "staged"])
@pytest.mark.parametrize("raw", [1.5, 4.9, 5, -2])
async def test_invalid_molecule_phase_is_not_truncated_into_a_valid_code(
    transformer: MoleculeTransformer,
    context: PipelineContext,
    raw: float,
    staged: bool,
) -> None:
    with pytest.raises(ValidationError) as caught:
        await _finalize(transformer, context, _record(raw), staged=staged)

    assert caught.value.field == "max_phase"
    assert caught.value.reason_code == "INVALID_DATA:max_phase"


async def test_equivalent_phase_inputs_preserve_identity_and_content_hash(
    transformer: MoleculeTransformer, context: PipelineContext
) -> None:
    text_phase = await transformer.transform(context, _record("0.5"), 0)
    numeric_phase = await transformer.transform(context, _record(0.5), 1)
    other_phase = await transformer.transform(context, _record(0), 2)

    assert text_phase is not None and numeric_phase is not None
    assert other_phase is not None
    assert text_phase["entity_id"] == numeric_phase["entity_id"]
    assert text_phase["entity_id"] == other_phase["entity_id"]
    assert text_phase["content_hash"] == numeric_phase["content_hash"]
    assert text_phase["content_hash"] != other_phase["content_hash"]
