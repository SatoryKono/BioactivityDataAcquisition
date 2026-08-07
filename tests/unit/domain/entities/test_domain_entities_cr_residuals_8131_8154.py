# pyright: reportArgumentType=false
"""Residual closeout coverage for domain/entities CR-FULL #8131-#8154."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from bioetl.domain.entities._chembl_additional_models import (
    CompoundLinkRecord,
    PublicationSimilarityRecord,
    TissueRecord,
)
from bioetl.domain.entities._chembl_activity_assay_models import ActivityRecord
from bioetl.domain.entities._chembl_molecule_target_models import (
    MoleculeRecord,
    TargetRecord,
)
from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.entities.bioactivity import Bioactivity, BioactivityState
from bioetl.domain.entities.bioactivity._converters import _safe_str
from bioetl.domain.entities.chembl_tissue import Tissue
from bioetl.domain.entities.semanticscholar import SemanticScholarPublicationEntity


BASE_KWARGS = cast(
    Any,
    {
        "entity_id": "test:entity:001",
        "content_hash": "sha256hash",
        "run_id": "run-001",
        "run_type": "incremental",
        "ingestion_ts": datetime(2024, 1, 1, tzinfo=UTC),
        "_index": 0,
    },
)


def test_base_entity_requires_lineage_fields() -> None:
    with pytest.raises(ValueError, match="run_id"):
        BaseEntity(
            **{
                **BASE_KWARGS,
                "run_id": "",
            }
        )


def test_tissue_rejects_whitespace_ids() -> None:
    with pytest.raises(ValueError, match="Tissue ChEMBL ID"):
        Tissue(**{**BASE_KWARGS, "tissue_id": "   ", "pref_name": "Brain"})
    with pytest.raises(ValueError, match="pref_name"):
        Tissue(**{**BASE_KWARGS, "tissue_id": "CHEMBL123", "pref_name": "  "})


def test_safe_str_rejects_bool_and_normalizes_integral_float() -> None:
    assert _safe_str(True) is None
    assert _safe_str(False) is None
    assert _safe_str(3.0) == "3"
    assert _safe_str("  x  ") == "x"


def test_bioactivity_state_transitions() -> None:
    raw = Bioactivity(
        **BASE_KWARGS,
        activity_id="A1",
        molecule_id="M1",
        _state=BioactivityState.RAW,
    )
    normalized = raw.with_state(BioactivityState.NORMALIZED)
    assert normalized._state is BioactivityState.NORMALIZED
    validated = normalized.with_state(BioactivityState.VALIDATED)
    assert validated._state is BioactivityState.VALIDATED
    with pytest.raises(ValueError, match="Invalid bioactivity state transition"):
        raw.with_state(BioactivityState.VALIDATED)


def test_activity_record_tax_id_is_int() -> None:
    rec = ActivityRecord(
        activity_id="ACT1",
        molecule_id="MOL1",
        target_tax_id=9606,
    )
    assert rec.target_tax_id == 9606


def test_chembl_ids_reject_empty_strings() -> None:
    with pytest.raises(ValidationError):
        MoleculeRecord(molecule_id="")
    with pytest.raises(ValidationError):
        TargetRecord(target_id="")
    with pytest.raises(ValidationError):
        TissueRecord(tissue_id="", pref_name="x")
    with pytest.raises(ValidationError):
        CompoundLinkRecord(
            record_id=1,
            molecule_id="",
            publication_id="DOC1",
            src_id=1,
        )


def test_tanimoto_bounds() -> None:
    ok = PublicationSimilarityRecord(sim_id=1, doc_1=1, doc_2=2, avg_tani=0.5)
    assert ok.avg_tani == 0.5
    with pytest.raises(ValidationError):
        PublicationSimilarityRecord(sim_id=1, doc_1=1, doc_2=2, avg_tani=1.5)
    with pytest.raises(ValidationError):
        PublicationSimilarityRecord(sim_id=1, doc_1=1, doc_2=2, mol_tani=-0.1)


def test_semanticscholar_paper_id_hex() -> None:
    good = "a" * 40
    entity = SemanticScholarPublicationEntity(
        **BASE_KWARGS,
        paper_id=good,
    )
    assert entity.paper_id == good
    with pytest.raises(ValueError, match="40 hexadecimal"):
        SemanticScholarPublicationEntity(**BASE_KWARGS, paper_id="not-hex")
