"""Cross-layer parity checks for non-ChEMBL publication controlled vocabularies."""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.domain.normalization.profiles import (
    CROSSREF_PUBLICATION_PROFILE,
    OPENALEX_PUBLICATION_PROFILE,
    PUBMED_PUBLICATION_PROFILE,
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
)
from scripts.docs.matrix.generate_pipeline_normalization_matrix import (
    build_field_matrix_rows,
)

_CONTROLLED = yaml.safe_load(
    Path("configs/vocab/publication_controlled.yaml").read_text(encoding="utf-8")
)
_OBSERVED = yaml.safe_load(
    Path("tests/fixtures/normalization/non_chembl_observed_values.yaml").read_text(
        encoding="utf-8"
    )
)["pipelines"]
_PROFILES = {
    "crossref_publication": CROSSREF_PUBLICATION_PROFILE,
    "openalex_publication": OPENALEX_PUBLICATION_PROFILE,
    "pubmed_publication": PUBMED_PUBLICATION_PROFILE,
    "semanticscholar_publication": SEMANTICSCHOLAR_PUBLICATION_PROFILE,
}


def _row(
    rows: list[dict[str, str]],
    pipeline_name: str,
    field_name: str,
) -> dict[str, str]:
    return next(
        row
        for row in rows
        if row["pipeline_name"] == pipeline_name and row["field_name"] == field_name
    )


def test_raw_publication_type_vocabularies_match_observed_fixture_and_matrix_sources() -> (
    None
):
    rows = build_field_matrix_rows()
    provider_fields = {
        "crossref_publication": ("crossref", "publication_type"),
        "openalex_publication": ("openalex", "publication_type"),
        "pubmed_publication": ("pubmed", "publication_types"),
        "semanticscholar_publication": ("semanticscholar", "publication_types"),
    }

    for pipeline_name, (provider_name, config_field) in provider_fields.items():
        config_values = set(
            _CONTROLLED["providers"][provider_name][config_field]["values"]
        )
        observed_values = set(
            _OBSERVED[pipeline_name]["observed_values"]["publication_type"]
        )
        row = _row(rows, pipeline_name, "publication_type")

        assert observed_values <= config_values
        assert row["controlled_vocabulary_source"] == (
            "configs/vocab/publication_controlled.yaml"
        )
        assert _PROFILES[pipeline_name].rule_for("publication_type") is not None


def test_openalex_type_crossref_inherits_crossref_registry_and_matrix_source() -> None:
    rows = build_field_matrix_rows()
    crossref_values = set(
        _CONTROLLED["providers"]["crossref"]["publication_type"]["values"]
    )
    observed_values = set(
        _OBSERVED["openalex_publication"]["expected_normalized_values"]["type_crossref"]
    )
    row = _row(rows, "openalex_publication", "type_crossref")

    assert observed_values <= crossref_values | {"future-crossref-type"}
    assert row["controlled_vocabulary_source"] == (
        "configs/vocab/publication_controlled.yaml"
    )


def test_open_access_status_registry_remains_matrix_backed_closed_vocabulary() -> None:
    rows = build_field_matrix_rows()
    row = _row(rows, "openalex_publication", "oa_status")

    assert row["strictness"] == "strict_enum"
    assert row["controlled_vocabulary_source"] == (
        "domain.schemas.common.publication_base.OA_STATUS_VALUES"
    )
