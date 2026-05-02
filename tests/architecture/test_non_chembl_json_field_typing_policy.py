"""Architecture guards for ADR-035 non-ChEMBL structured-field typing."""

from __future__ import annotations

from pathlib import Path

import pandera.pandas as pa
import pyarrow as pa_arrow

from bioetl.domain.contracts.gold.publications_crossref import (
    CrossRefPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.publications_openalex import (
    OpenAlexPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.publications_pubmed import PubMedPublicationGoldSchema
from bioetl.domain.contracts.gold.publications_semanticscholar import (
    SemanticScholarPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.uniprot import UniProtProteinGoldSchema
from bioetl.domain.normalization.publication_structured_fields import (
    publication_structured_field_policies,
)
from bioetl.domain.normalization.structured_payload_policies import (
    semantic_sensitive_structured_payload_policies,
)
from scripts.docs.generate_pipeline_normalization_field_matrix import (
    ENTITY_DOMAIN_SCHEMA_REGISTRY,
    ENTITY_SILVER_SCHEMA_REGISTRY,
    build_field_matrix_rows,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = PROJECT_ROOT / "docs/03-data-model/json-field-typing-inventory.md"

GOLD_SCHEMA_REGISTRY: dict[str, type[pa.DataFrameModel]] = {
    "crossref_publication": CrossRefPublicationGoldSchema,
    "openalex_publication": OpenAlexPublicationGoldSchema,
    "pubmed_publication": PubMedPublicationGoldSchema,
    "semanticscholar_publication": SemanticScholarPublicationGoldSchema,
    "uniprot_protein": UniProtProteinGoldSchema,
}


def _governed_field_keys() -> set[tuple[str, str]]:
    keys = {
        (
            policy.profile_name.replace(".", "_"),
            policy.field_name,
        )
        for policy in publication_structured_field_policies()
    }
    keys.update(
        (
            policy.profile_name.replace(".", "_"),
            policy.field_name,
        )
        for policy in semantic_sensitive_structured_payload_policies()
    )
    return keys


def _is_arrow_string_type(data_type: pa_arrow.DataType) -> bool:
    return pa_arrow.types.is_string(data_type) or pa_arrow.types.is_large_string(
        data_type
    )


def _is_pandera_string_dtype(dtype: object) -> bool:
    normalized = str(dtype).strip().lower()
    return "str" in normalized or normalized == "string"


def test_governed_non_chembl_structured_fields_use_canonical_json_string_contracts() -> (
    None
):
    rows_by_key = {
        (row["pipeline_name"], row["field_name"]): row
        for row in build_field_matrix_rows()
    }

    for pipeline_name, field_name in sorted(_governed_field_keys()):
        silver_schema = ENTITY_SILVER_SCHEMA_REGISTRY[pipeline_name]
        domain_schema = ENTITY_DOMAIN_SCHEMA_REGISTRY[pipeline_name].to_schema()
        gold_schema = GOLD_SCHEMA_REGISTRY[pipeline_name].to_schema()

        if (
            field_name not in silver_schema.names
            or field_name not in domain_schema.columns
            or field_name not in gold_schema.columns
        ):
            # Policy registries can lead shipped schemas during staged rollout.
            continue

        assert _is_arrow_string_type(silver_schema.field(field_name).type), (
            f"{pipeline_name}.{field_name}: Silver must store canonical JSON strings"
        )
        assert _is_pandera_string_dtype(domain_schema.columns[field_name].dtype), (
            f"{pipeline_name}.{field_name}: domain schema must expose string contract"
        )
        assert _is_pandera_string_dtype(gold_schema.columns[field_name].dtype), (
            f"{pipeline_name}.{field_name}: Gold contract must expose string contract"
        )

        row = rows_by_key[(pipeline_name, field_name)]
        assert row["field_type"] == "string"


def test_json_field_typing_inventory_documents_governed_non_chembl_fields() -> None:
    actual = INVENTORY_PATH.read_text(encoding="utf-8")

    assert "# JSON Field Typing Inventory" in actual
    assert "ADR-035" in actual
    assert "canonical JSON string" in actual
    assert "src/tools/generate_json_field_typing_inventory.py" in actual

    for field_name in (
        "authors",
        "affiliation_list",
        "affiliation_structured",
        "authors_with_affiliations",
        "grants",
        "primary_topic",
        "citation_contexts",
        "publication_types",
        "subject_fields",
        "features_json",
    ):
        assert f"`{field_name}`" in actual
