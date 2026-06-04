"""Tests for publication structured-field policy specs constants."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization._publication_structured_field_policy_specs import (
    CROSSREF_PUBLICATION,
    OPENALEX_PUBLICATION,
    ORDERED_SEQUENCE,
    ORCID,
    PUBLICATION_STRUCTURED_FIELD_POLICY_SPECS,
    PUBMED_PUBLICATION,
    SEMANTICSCHOLAR_PUBLICATION,
    UNORDERED_SET,
)

pytestmark = pytest.mark.unit


def test_policy_specs_constants_are_defined() -> None:
    assert CROSSREF_PUBLICATION == "crossref.publication"
    assert OPENALEX_PUBLICATION == "openalex.publication"
    assert PUBMED_PUBLICATION == "pubmed.publication"
    assert SEMANTICSCHOLAR_PUBLICATION == "semanticscholar.publication"
    assert ORDERED_SEQUENCE == "ordered_sequence"
    assert UNORDERED_SET == "unordered_set"
    assert ORCID == "orcid"


def test_policy_specs_is_tuple() -> None:
    assert isinstance(PUBLICATION_STRUCTURED_FIELD_POLICY_SPECS, tuple)


def test_policy_specs_has_expected_structure() -> None:
    assert len(PUBLICATION_STRUCTURED_FIELD_POLICY_SPECS) > 0
    for spec in PUBLICATION_STRUCTURED_FIELD_POLICY_SPECS:
        assert isinstance(spec, tuple)
        assert len(spec) == 5
        profile_name, field_name, semantics, identifier_family, raw_sidecar = spec
        assert isinstance(profile_name, str)
        assert isinstance(field_name, str)
        assert isinstance(semantics, str)
        assert identifier_family is None or isinstance(identifier_family, str)
        assert raw_sidecar is None or isinstance(raw_sidecar, str)


def test_policy_specs_contains_crossref_publication() -> None:
    crossref_specs = [
        spec
        for spec in PUBLICATION_STRUCTURED_FIELD_POLICY_SPECS
        if spec[0] == CROSSREF_PUBLICATION
    ]
    assert len(crossref_specs) > 0


def test_policy_specs_contains_pubmed_publication() -> None:
    pubmed_specs = [
        spec
        for spec in PUBLICATION_STRUCTURED_FIELD_POLICY_SPECS
        if spec[0] == PUBMED_PUBLICATION
    ]
    assert len(pubmed_specs) > 0


def test_policy_specs_contains_openalex_publication() -> None:
    openalex_specs = [
        spec
        for spec in PUBLICATION_STRUCTURED_FIELD_POLICY_SPECS
        if spec[0] == OPENALEX_PUBLICATION
    ]
    assert len(openalex_specs) > 0


def test_policy_specs_contains_semanticscholar_publication() -> None:
    semanticscholar_specs = [
        spec
        for spec in PUBLICATION_STRUCTURED_FIELD_POLICY_SPECS
        if spec[0] == SEMANTICSCHOLAR_PUBLICATION
    ]
    assert len(semanticscholar_specs) > 0
