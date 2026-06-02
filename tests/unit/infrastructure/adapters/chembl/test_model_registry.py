"""Registry coverage tests for API-backed ChEMBL model families."""

from __future__ import annotations

import pytest

import json
from pathlib import Path

from bioetl.domain.entities.chembl import (
    ChemblPublicationRecord,
    ProteinClassRecord,
    PublicationSimilarityRecord,
)
from bioetl.infrastructure.adapters.chembl.constants import CHEMBL_DTO_MODELS
from bioetl.infrastructure.adapters.chembl.models import (
    CHEMBL_RECORD_MODELS,
    CHEMBL_RESPONSE_MODELS,
    ChemblCompoundRecordApiRecord,
    ChemblPublicationApiRecord,
    ChemblPublicationSimilarityApiRecord,
    ChemblTissueApiRecord,
)
from bioetl.infrastructure.adapters.chembl.models_additional import (
    ChemblProteinClassApiRecord,
)


pytestmark = pytest.mark.unit


def _load_first_fixture_row(relative_path: str) -> dict[str, object]:
    path = Path(relative_path)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            return json.loads(line)
    raise AssertionError(f"No rows in fixture: {relative_path}")


def test_chembl_dto_registry_covers_remaining_api_backed_aliases() -> None:
    assert CHEMBL_DTO_MODELS["publication"] is ChemblPublicationRecord
    assert CHEMBL_DTO_MODELS["document"] is ChemblPublicationRecord
    assert CHEMBL_DTO_MODELS["protein_classification"] is ProteinClassRecord
    assert CHEMBL_DTO_MODELS["document_similarity"] is PublicationSimilarityRecord


def test_chembl_record_and_response_registries_cover_remaining_api_backed_entities() -> (
    None
):
    expected_entities = {
        "activity",
        "assay",
        "cell_line",
        "compound",
        "compound_record",
        "document",
        "document_similarity",
        "molecule",
        "protein_class",
        "protein_classification",
        "publication",
        "publication_similarity",
        "target",
        "target_component",
        "tissue",
    }

    assert expected_entities <= set(CHEMBL_RECORD_MODELS)
    assert expected_entities <= set(CHEMBL_RESPONSE_MODELS)


def test_remaining_api_backed_record_models_validate_tracked_fixture_shapes() -> None:
    publication_row = _load_first_fixture_row(
        "tests/fixtures/bronze/chembl/publication/sample_ci_2026-04-24.jsonl"
    )
    tissue_row = _load_first_fixture_row(
        "tests/fixtures/bronze/chembl/tissue/sample_ci_2026-04-29.jsonl"
    )
    compound_record_row = _load_first_fixture_row(
        "tests/fixtures/bronze/chembl/compound_record/sample_ci_2026-04-29.jsonl"
    )
    protein_class_row = _load_first_fixture_row(
        "tests/fixtures/bronze/chembl/protein_class/sample_ci_2026-04-29.jsonl"
    )
    publication_similarity_row = _load_first_fixture_row(
        "tests/fixtures/bronze/chembl/publication_similarity/sample_ci_2026-04-30.jsonl"
    )

    assert isinstance(
        CHEMBL_RECORD_MODELS["publication"].model_validate(publication_row),
        ChemblPublicationApiRecord,
    )
    assert isinstance(
        CHEMBL_RECORD_MODELS["tissue"].model_validate(tissue_row),
        ChemblTissueApiRecord,
    )
    assert isinstance(
        CHEMBL_RECORD_MODELS["compound_record"].model_validate(compound_record_row),
        ChemblCompoundRecordApiRecord,
    )
    assert isinstance(
        CHEMBL_RECORD_MODELS["protein_class"].model_validate(protein_class_row),
        ChemblProteinClassApiRecord,
    )
    assert isinstance(
        CHEMBL_RECORD_MODELS["publication_similarity"].model_validate(
            publication_similarity_row
        ),
        ChemblPublicationSimilarityApiRecord,
    )
