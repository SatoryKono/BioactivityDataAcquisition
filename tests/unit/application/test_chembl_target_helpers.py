"""Unit tests for pure ChEMBL target helper projections."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from bioetl.application.pipelines.chembl.target_helpers import (
    ComponentHelper,
    SynonymHelper,
    XrefHelper,
)
from bioetl.domain.types import JsonDict


pytestmark = pytest.mark.unit


def test_xref_source_and_value_normalization_branches() -> None:
    assert XrefHelper.normalize_xref_source(None) is None
    assert XrefHelper.normalize_xref_source("  ") is None
    assert XrefHelper.normalize_xref_source("go component") == "GO_COMPONENT"
    assert XrefHelper.normalize_xref_source("go/component") == "GO_COMPONENT"
    assert XrefHelper.normalize_xref_source("go::component") == "GO_COMPONENT"

    assert XrefHelper.clean_pipe_value(None) is None
    assert XrefHelper.clean_pipe_value("  ") is None
    assert XrefHelper.clean_pipe_value("A|B") == r"A\|B"

    values: list[str] = []
    seen: set[str] = set()
    XrefHelper.append_unique_pipe_value(values, seen, "P12345")
    XrefHelper.append_unique_pipe_value(values, seen, "P12345")
    XrefHelper.append_unique_pipe_value(values, seen, "Q99999")
    assert values == ["P12345", "Q99999"]
    assert XrefHelper.pipe_or_unknown(values) == "P12345|Q99999"
    assert XrefHelper.pipe_or_unknown([]) == "unknown"


def test_collect_and_project_component_xrefs_cover_skip_and_projection_paths() -> None:
    assert XrefHelper.collect_component_xrefs(None) == []
    assert XrefHelper.collect_component_xrefs([{"target_component_xrefs": "bad"}]) == []

    components = [
        {
            "target_component_xrefs": [
                {"xref_src_db": "PDB", "xref_id": "1ABC"},
                {"xref_src_db": "PDBE", "xref_id": "1ABC"},
                {"xref_src_db": "GO component", "xref_name": "nucleus"},
                {"xref_src_db": "GO_FUNCTION", "xref_name": "binding"},
                {"xref_src_db": "GO-process", "xref_name": "signaling"},
                {"xref_src_db": "HGNC", "xref_id": "HGNC:1"},
                {"xref_src_db": "UniProt", "xref_id": "P12345|raw"},
                {"xref_src_db": "Reactome", "xref_id": "R-HSA-1"},
                {"xref_src_db": "unknown", "xref_id": "ignored"},
                {"xref_src_db": "PDB", "xref_id": " "},
                {"xref_src_db": None, "xref_id": "ignored"},
                "not-a-dict",
            ]
        },
        {"target_component_xrefs": [{"xref_src_db": "PDB", "xref_id": "2XYZ"}]},
    ]

    xrefs = XrefHelper.collect_component_xrefs(components)
    projection = XrefHelper.project_component_xrefs(xrefs)

    assert projection == {
        "target_xref_pdb_ids": "1ABC|2XYZ",
        "target_xref_go_component": "nucleus",
        "target_xref_go_function": "binding",
        "target_xref_go_process": "signaling",
        "target_xref_hgnc_ids": "HGNC:1",
        "target_xref_reactome_ids": "R-HSA-1",
        "target_xref_uniprot_ids": r"P12345\|raw",
    }


def test_synonym_target_field_and_unique_append_branches() -> None:
    assert SynonymHelper.synonym_target_field(None) is None
    assert SynonymHelper.synonym_target_field("  ") is None
    assert SynonymHelper.synonym_target_field("UNIPROT") == "target_protein_synonyms"
    assert SynonymHelper.synonym_target_field("EC_NUMBER") == "target_ec_numbers"
    assert SynonymHelper.synonym_target_field("GENE_SYMBOL") == "target_gene_synonyms"
    assert (
        SynonymHelper.synonym_target_field("GENE_SYMBOL_OTHER")
        == "target_gene_synonyms"
    )
    assert SynonymHelper.synonym_target_field("OTHER") is None

    values: list[str] = []
    seen: set[str] = set()
    SynonymHelper.append_unique_pipe_escaped(values, seen, None)
    SynonymHelper.append_unique_pipe_escaped(values, seen, " ")
    SynonymHelper.append_unique_pipe_escaped(values, seen, "A|B")
    SynonymHelper.append_unique_pipe_escaped(values, seen, "A|B")
    SynonymHelper.append_unique_pipe_escaped(values, seen, 123)
    assert values == [r"A\|B", "123"]
    assert SynonymHelper.pipe_or_unknown(values) == r"A\|B|123"
    assert SynonymHelper.pipe_or_unknown([]) == "unknown"


def test_project_component_synonyms_skips_invalid_payloads_and_projects_buckets() -> (
    None
):
    assert SynonymHelper.project_component_synonyms(None) == {
        "target_protein_synonyms": "unknown",
        "target_gene_synonyms": "unknown",
        "target_ec_numbers": "unknown",
    }
    assert SynonymHelper.project_component_synonyms("not-a-list") == {
        "target_protein_synonyms": "unknown",
        "target_gene_synonyms": "unknown",
        "target_ec_numbers": "unknown",
    }

    components = [
        "not-a-mapping",
        {"target_component_synonyms": "bad"},
        {
            "target_component_synonyms": [
                {"syn_type": "UNIPROT", "component_synonym": "Protein|A"},
                {"syn_type": "UNIPROT", "component_synonym": "Protein|A"},
                {"syn_type": "GENE_SYMBOL_OLD", "component_synonym": "GENE1"},
                {"syn_type": "EC_NUMBER", "component_synonym": "1.1.1.1"},
                {"syn_type": "OTHER", "component_synonym": "ignored"},
                "not-a-mapping",
            ]
        },
    ]

    assert list(SynonymHelper.iter_component_synonym_payloads(components)) == [
        {"syn_type": "UNIPROT", "component_synonym": "Protein|A"},
        {"syn_type": "UNIPROT", "component_synonym": "Protein|A"},
        {"syn_type": "GENE_SYMBOL_OLD", "component_synonym": "GENE1"},
        {"syn_type": "EC_NUMBER", "component_synonym": "1.1.1.1"},
        {"syn_type": "OTHER", "component_synonym": "ignored"},
    ]
    assert SynonymHelper.project_component_synonyms(components) == {
        "target_protein_synonyms": r"Protein\|A",
        "target_gene_synonyms": "GENE1",
        "target_ec_numbers": "1.1.1.1",
    }


def test_project_single_synonym_ignores_unmapped_synonym_types() -> None:
    buckets = {
        "target_protein_synonyms": [],
        "target_gene_synonyms": [],
        "target_ec_numbers": [],
    }
    seen_by_field = {
        "target_protein_synonyms": set(),
        "target_gene_synonyms": set(),
        "target_ec_numbers": set(),
    }

    SynonymHelper.project_single_synonym(
        {"syn_type": "OTHER", "component_synonym": "ignored"},
        buckets,
        seen_by_field,
    )
    SynonymHelper.project_single_synonym(
        {"syn_type": "UNIPROT", "component_synonym": "Protein A"},
        buckets,
        seen_by_field,
    )

    assert buckets == {
        "target_protein_synonyms": ["Protein A"],
        "target_gene_synonyms": [],
        "target_ec_numbers": [],
    }


def test_component_helper_flattens_components_with_transform_callback() -> None:
    assert ComponentHelper.flatten_target_components(None, lambda *_: []) == (
        ComponentHelper.empty_component_result()
    )
    assert ComponentHelper.flatten_target_components("not-a-list", lambda *_: []) == (
        ComponentHelper.empty_component_result()
    )

    components: list[JsonDict] = [
        {
            "accession": "P12345",
            "component_id": "7",
            "component_type": "PROTEIN",
            "relationship": "SINGLE PROTEIN",
            "component_description": "Target A",
        },
        {
            "accession": "Q99999",
            "component_id": "bad",
            "component_type": "PROTEIN",
            "relationship": "CHAIN",
            "component_description": None,
        },
    ]

    def extract_list_field(
        rows: list[JsonDict],
        field_name: str,
        transform: Callable[[Any], Any] | None = None,
    ) -> list[object]:
        values: list[object] = []
        for row in rows:
            value = row.get(field_name)
            if transform is not None:
                value = transform(value)
            values.append(value)
        return values

    assert ComponentHelper.flatten_target_components(
        components,
        extract_list_field,
    ) == {
        "component_accessions": ["P12345", "Q99999"],
        "component_ids": [7, None],
        "component_types": ["PROTEIN", "PROTEIN"],
        "component_relationships": ["SINGLE PROTEIN", "CHAIN"],
        "component_descriptions": ["Target A", None],
    }
