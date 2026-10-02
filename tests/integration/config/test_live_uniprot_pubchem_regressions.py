"""Contracts for provider records observed in the limit-1000 live matrix."""

import json
import re
from pathlib import Path

import pytest
import yaml

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from tests.helpers.transformer_dependencies import instantiate_test_transformer


def pattern(provider, entity, field):
    root = Path(__file__).resolve().parents[3]
    payload = yaml.safe_load(
        (root / f"configs/entities/{provider}/{entity}.yaml").read_text(
            encoding="utf-8"
        )
    )
    return next(
        row["pattern"]
        for row in payload["quality"]["entity_field_validations"]
        if row["field"] == field
    )


@pytest.mark.parametrize("method", ["_transform_impl", "transform_pre_silver"])
@pytest.mark.asyncio
async def test_inactive_uniprot_tombstone_is_explicitly_filtered(method):
    transformer = instantiate_test_transformer(UniProtProteinTransformer)
    record = {
        "entryType": "Inactive",
        "primaryAccession": "Q0ZMF1",
        "annotationScore": 0.0,
        "inactiveReason": {"inactiveReasonType": "DELETED"},
    }
    original = json.loads(json.dumps(record))
    with pytest.raises(FilteredOutError, match="inactive") as error:
        await getattr(transformer, method)(None, record, 0)
    assert error.value.details["accession"] == "Q0ZMF1"
    assert error.value.details["inactive_reason"] == record["inactiveReason"]
    assert record == original


@pytest.mark.parametrize(
    "entry_type",
    ["UniProtKB reviewed (Swiss-Prot)", "UniProtKB unreviewed (TrEMBL)", None],
)
def test_active_or_unknown_records_are_not_silently_filtered(entry_type):
    transformer = instantiate_test_transformer(UniProtProteinTransformer)
    record = {"entryType": entry_type, "annotationScore": 0.0}
    transformer._reject_inactive_record(record)
    assert record == {"entryType": entry_type, "annotationScore": 0.0}


@pytest.mark.parametrize(
    "name",
    [
        "Homo sapiens",
        "Human T-cell leukemia virus 1 (strain Japan ATK-1 subtype A)",
        "Influenza A virus (strain A/Puerto Rico/8/1934 H1N1)",
    ],
)
def test_viral_scientific_names_are_valid(name):
    assert re.fullmatch(pattern("uniprot", "protein", "organism_scientific"), name)


@pytest.mark.parametrize("name", ["", "12345", "homo sapiens", "Homo"])
def test_invalid_scientific_names_remain_invalid(name):
    assert not re.fullmatch(pattern("uniprot", "protein", "organism_scientific"), name)


@pytest.mark.parametrize(
    "term",
    [
        "dehydrogenase [NAD(P)+] activity",
        'term with "quotes" and {braces}',
        "term with backslash \\ and bracket ]",
    ],
)
def test_go_descriptive_text_does_not_break_array_validation(term):
    value = json.dumps(
        [{"aspect": "F", "id": "GO:0140169", "term": term}],
        separators=(",", ":"),
        sort_keys=True,
    )
    assert re.fullmatch(pattern("uniprot", "protein", "go_terms"), value)


@pytest.mark.parametrize(
    "value",
    [
        '["GO:123"]',
        '[{"id":"invalid"}]',
        '[{"id":"GO:1234567"},{"id":"invalid"}]',
        '[{"term":"GO:1234567"}]',
    ],
)
def test_invalid_go_references_remain_invalid(value):
    assert not re.fullmatch(pattern("uniprot", "protein", "go_terms"), value)


@pytest.mark.parametrize(
    "value", ["C21H37ClN+", "C12H19N2O2+", "C2H3O2-", "Fe+3", "H2O", "NaCl"]
)
def test_ionic_molecular_formula_is_valid(value):
    assert re.fullmatch(pattern("pubchem", "compound", "molecular_formula"), value)


@pytest.mark.parametrize(
    "value", ["", "12", "h2o", "C+H", "C++", "C;H", "C2H5 garbage"]
)
def test_malformed_molecular_formula_remains_invalid(value):
    assert not re.fullmatch(pattern("pubchem", "compound", "molecular_formula"), value)
