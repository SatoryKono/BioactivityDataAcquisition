"""Stream A remaining domain coverage (#10469): idmapping, identifiers, assay/ontology."""

from __future__ import annotations

import pandas as pd
import pytest

from bioetl.domain.normalization._reference_id_normalizers import _normalize_orcid_text
from bioetl.domain.normalization.chembl import normalize_cellosaurus_id
from bioetl.domain.normalization.profiles._profile_activity_ontology_normalizers import (
    normalize_profile_activity_bao_format_mapping_status,
)
from bioetl.domain.normalization.profiles.chembl_assay import create_case_normalizer
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema, MAPPING_STATUSES

pytestmark = pytest.mark.unit


def test_idmapping_schema_check_methods_accept_valid_and_null_series() -> None:
    targets = pd.Series(["CHEMBL204", "CHEMBL1"], dtype="object")
    accessions = pd.Series([None, "P00742"], dtype="object")
    statuses = pd.Series(list(MAPPING_STATUSES[:2]), dtype="object")
    assert bool(IDMappingSchema._check_target_id(targets).all())
    assert bool(IDMappingSchema._check_uniprot_accession(accessions).all())
    assert bool(IDMappingSchema._check_mapping_status(statuses).all())


def test_orcid_normalizer_rejects_non_matching_compact_text() -> None:
    assert _normalize_orcid_text("not-an-orcid") is None
    assert _normalize_orcid_text("0000") is None


def test_cellosaurus_normalizer_returns_original_when_regex_does_not_match() -> None:
    assert normalize_cellosaurus_id("not-a-cellosaurus") == "not-a-cellosaurus"
    assert normalize_cellosaurus_id("CVCL_0001") == "CVCL_0001"


def test_bao_format_mapping_status_falls_back_when_record_is_absent() -> None:
    assert normalize_profile_activity_bao_format_mapping_status("mapped") == "mapped"
    assert (
        normalize_profile_activity_bao_format_mapping_status("mapped", record=None)
        == "mapped"
    )
    assert normalize_profile_activity_bao_format_mapping_status("nope") is None


def test_chembl_assay_case_normalizer_applies_strategy() -> None:
    assert create_case_normalizer("uppercase")("ab") == "AB"
    assert create_case_normalizer("lowercase")("Ab") == "ab"
    assert create_case_normalizer("preserve")("Ab") == "Ab"
