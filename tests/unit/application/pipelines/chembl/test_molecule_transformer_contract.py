"""Preserve provider phase codes until application-owned normalization."""

from __future__ import annotations

import pytest

from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.exceptions.validation import ValidationError
from bioetl.domain.types import BronzeRecord
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies

pytestmark = pytest.mark.unit

type PhaseInput = str | int | float | None


@pytest.fixture
def molecule_transformer() -> MoleculeTransformer:
    return MoleculeTransformer(dependencies=build_test_transformer_dependencies())


@pytest.fixture
def normalizer() -> RecordNormalizationProcessor:
    return RecordNormalizationProcessor(provider="chembl", entity_type="molecule")


def _record(phase: PhaseInput) -> BronzeRecord:
    return {
        "molecule_chembl_id": "CHEMBL25",
        "pref_name": "Example Molecule",
        "molecule_type": "Small molecule",
        "structure_type": "MOL",
        "max_phase": phase,
        "first_approval": "1998",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        ("-1.0", -1),
        ("0.0", 0),
        ("0.5", 0.5),
        ("1.0", 1),
        ("2.0", 2),
        ("3.0", 3),
        ("4.0", 4),
        (-1, -1),
        (0, 0),
        (0.5, 0.5),
        (4.0, 4),
        (None, None),
    ],
)
async def test_phase_survives_transformer_and_silver_finalization(
    molecule_transformer: MoleculeTransformer,
    normalizer: RecordNormalizationProcessor,
    mock_context: PipelineContext,
    phase: PhaseInput,
    expected: int | float | None,
) -> None:
    staged = await molecule_transformer.transform_pre_silver(
        mock_context, _record(phase), index=7
    )

    assert isinstance(staged, PreSilverRecord)
    assert staged.business_data["max_phase"] == phase
    assert type(staged.business_data["max_phase"]) is type(phase)
    assert staged.business_data["first_approval"] == 1998
    assert isinstance(staged.business_data["first_approval"], int)

    silver = normalizer.finalize_pre_silver(staged, mock_context, index=7)
    direct = await molecule_transformer.transform(mock_context, _record(phase), index=7)

    assert silver is not None
    assert direct is not None
    assert silver["max_phase"] == direct.get("max_phase") == expected
    assert type(silver["max_phase"]) is type(expected)
    assert silver["molecule_id"] == direct.get("molecule_id") == "CHEMBL25"
    assert silver["entity_id"] == direct["entity_id"] == staged.entity_id
    assert silver["content_hash"] == direct["content_hash"]


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [1.5, 4.9, 5, "1.5", "4.9", "5.0"])
async def test_invalid_phase_keeps_its_validation_reason(
    molecule_transformer: MoleculeTransformer,
    normalizer: RecordNormalizationProcessor,
    mock_context: PipelineContext,
    phase: PhaseInput,
) -> None:
    staged = await molecule_transformer.transform_pre_silver(
        mock_context, _record(phase), index=0
    )
    assert isinstance(staged, PreSilverRecord)

    with pytest.raises(ValidationError) as caught:
        normalizer.finalize_pre_silver(staged, mock_context, index=0)

    assert caught.value.field == "max_phase"
    assert caught.value.reason_code == "INVALID_DATA:max_phase"


@pytest.mark.asyncio
async def test_phase_normalization_precedes_hash_without_changing_identity(
    molecule_transformer: MoleculeTransformer,
    normalizer: RecordNormalizationProcessor,
    mock_context: PipelineContext,
) -> None:
    records = []
    for phase in ("0.5", 0.5, 0, None):
        staged = await molecule_transformer.transform_pre_silver(
            mock_context, _record(phase), index=0
        )
        assert isinstance(staged, PreSilverRecord)
        silver = normalizer.finalize_pre_silver(staged, mock_context, index=0)
        assert silver is not None
        records.append(silver)

    assert {record["molecule_id"] for record in records} == {"CHEMBL25"}
    assert len({record["entity_id"] for record in records}) == 1
    assert records[0]["content_hash"] == records[1]["content_hash"]
    assert len({records[index]["content_hash"] for index in (0, 2, 3)}) == 3
