# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Golden normalization/hash tests for non-ChEMBL profiles."""

from __future__ import annotations

import pytest

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from pathlib import Path
from tests.helpers.golden_files import load_named_json_fixture

GOLDEN_DIR = Path("tests/golden/normalization/non_chembl")

RAW_CASES: dict[str, tuple[str, str, dict[str, object]]] = {
    "crossref_publication": (
        "crossref",
        "publication",
        {
            "doi": " HTTPS://doi.org/10.1000/XYZ ",
            "title": "  Example <b>Crossref</b> Title  ",
            "issn": "2049-3630",
            "issn_list": ["ISSN:1234567X", "2049-3630"],
            "issn_print": "issn:1234567x",
            "issn_electronic": "20493630",
            "publication_type": " journal-article ",
        },
    ),
    "openalex_publication": (
        "openalex",
        "publication",
        {
            "openalex_id": "https://openalex.org/W123",
            "doi": " DOI:10.1000/OA ",
            "pmid": " PMID:0012345 ",
            "issn": "issn:20493630",
            "oa_status": " GOLD ",
            "author_openalex_ids": ["https://openalex.org/A2", "a10"],
            "publication_type": " article ",
        },
    ),
    "semanticscholar_publication": (
        "semanticscholar",
        "publication",
        {
            "paper_id": "ABCDEFABCDEFABCDEFABCDEFABCDEFABCDEFABCD",
            "pmid": 12345,
            "author_s2_ids": [
                "ABCDEFABCDEFABCDEFABCDEFABCDEFABCDEFABCD",
                "abcdefabcdefabcdefabcdefabcdefabcdefabcd",
            ],
            "publication_type": " journalarticle ",
            "publication_types": ["Review", "JournalArticle"],
            "oa_status": " GREEN ",
        },
    ),
    "pubchem_compound": (
        "pubchem",
        "compound",
        {
            "canonical_smiles": " CCO ",
            "isomeric_smiles": " C[C@H](O)C ",
            "chemical_standardization_status": " standardized ",
            "chemical_standardization_policy_version": " pubchem-basic-v1 ",
        },
    ),
    "uniprot_protein": (
        "uniprot",
        "protein",
        {
            "protein_name": "  Sample protein  ",
            "secondary_accessions": ["q8n158", "P12345"],
            "chembl_ids": ["chembl25", "CHEMBL1"],
            "go_terms": ["go:0005634", "GO:0003677"],
            "entry_type": " UniProtKB reviewed (Swiss-Prot) ",
            "reviewed": True,
        },
    ),
    "uniprot_idmapping": (
        "uniprot",
        "idmapping",
        {
            "target_id": " chembl203 ",
            "uniprot_accession": " p00742 ",
            "all_mappings": ["p00742", "q9y6k9"],
            "mapping_status": "found",
            "reviewed": False,
        },
    ),
    "pubmed_publication": (
        "pubmed",
        "publication",
        {
            "pmid": " PMID:0012345 ",
            "doi": " HTTPS://doi.org/10.1000/PM ",
            "issn": "issn:20493630",
            "publication_type": " Review ",
            "publication_types": ["Review", "Journal Article"],
            "title": "  Example Title  ",
        },
    ),
}


def _load_golden(name: str) -> dict[str, object]:
    return load_named_json_fixture(GOLDEN_DIR, name)


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(RAW_CASES))
def test_non_chembl_normalization_payload_and_hash_match_golden(name: str) -> None:
    provider, entity_type, raw = RAW_CASES[name]
    processor = RecordNormalizationProcessor(provider=provider, entity_type=entity_type)
    golden = _load_golden(name)

    normalized = processor.normalize_business_data(dict(raw))

    assert normalized == golden["normalized"]
    assert processor.compute_content_hash(normalized) == golden["content_hash"]


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(RAW_CASES))
def test_non_chembl_hash_excludes_runtime_meta_fields(name: str) -> None:
    provider, entity_type, raw = RAW_CASES[name]
    processor = RecordNormalizationProcessor(provider=provider, entity_type=entity_type)
    normalized = processor.normalize_business_data(dict(raw))

    baseline_hash = processor.compute_content_hash(normalized)
    with_runtime_meta = {
        **normalized,
        "_run_id": "run-a",
        "_ingestion_ts": "2026-05-05T00:00:00Z",
        "_index": 7,
        "_source_batch_id": "batch-a",
    }
    with_other_runtime_meta = {
        **normalized,
        "_run_id": "run-b",
        "_ingestion_ts": "2026-05-06T00:00:00Z",
        "_index": 99,
        "_source_batch_id": "batch-b",
    }

    assert processor.compute_content_hash(with_runtime_meta) == baseline_hash
    assert processor.compute_content_hash(with_other_runtime_meta) == baseline_hash


@pytest.mark.unit
def test_non_chembl_set_like_field_permutations_keep_hash_stable() -> None:
    cases = (
        (
            "crossref",
            "publication",
            {"issn_list": ["ISSN:1234567X", "2049-3630"]},
            {"issn_list": ["2049-3630", "ISSN:1234567X"]},
            True,
        ),
        (
            "openalex",
            "publication",
            {"author_openalex_ids": ["https://openalex.org/A2", "a10"]},
            {"author_openalex_ids": ["a10", "https://openalex.org/A2"]},
            True,
        ),
        (
            "semanticscholar",
            "publication",
            {"publication_types": ["Review", "JournalArticle"]},
            {"publication_types": ["JournalArticle", "Review"]},
            True,
        ),
        (
            "semanticscholar",
            "publication",
            {"subject_fields": ["Biology", "Chemistry"]},
            {"subject_fields": ["Chemistry", "Biology"]},
            True,
        ),
        (
            "uniprot",
            "idmapping",
            {"all_mappings": ["q9y6k9", "p00742"]},
            {"all_mappings": ["p00742", "q9y6k9"]},
            True,
        ),
    )

    for provider, entity_type, left, right, expect_equal_payload in cases:
        processor = RecordNormalizationProcessor(
            provider=provider, entity_type=entity_type
        )
        normalized_left = processor.normalize_business_data(left)
        normalized_right = processor.normalize_business_data(right)
        if expect_equal_payload:
            assert normalized_left == normalized_right
        assert processor.compute_content_hash(
            normalized_left
        ) == processor.compute_content_hash(normalized_right)
