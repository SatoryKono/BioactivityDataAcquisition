______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-02'

______________________________________________________________________

# Reference Identifiers

This page is the concise normalization-governance entrypoint for non-ChEMBL
identifier families. The detailed registry inventory remains:
[reference-identifier-families.md](../../03-data-model/reference-identifier-families.md).

## Core Rule

Reference identifiers are canonicalized by family and storage semantics.
They are not strict enums.

Do not create fail-closed enum policy for:

- DOI, PMID, PMCID
- OpenAlex work/author/institution/topic IDs
- UniProt accessions
- ORCID, ROR, ISSN
- GO, InterPro, Pfam, Reactome, PDB
- Semantic Scholar stable IDs

The only reviewed boundary is canonical form plus collection semantics.

## Family Summary

| Family | Canonical form | Storage semantics | Example fields |
| --- | --- | --- | --- |
| `orcid` | `0000-0000-0000-0000` | set-like string array | publication author ORCIDs |
| `issn` | `1234-567X` | scalar or set-like string array | publication ISSN fields |
| `ror` | `https://ror.org/...` | set-like string array | OpenAlex institution RORs |
| `openalex_author` | `A123` | set-like string array | `author_openalex_ids` |
| `openalex_institution` | `I123` | set-like string array | `institution_ids` |
| `openalex_topic` | `T123` inside canonical JSON | structured JSON object/array | `primary_topic`, `subject_topics` |
| `openalex_work` | `W123` | scalar string | `openalex_id` |
| `semantic_scholar_author` | lowercase 40-char hex | set-like string array | `author_s2_ids` |
| `semantic_scholar_paper` | lowercase 40-char hex | scalar string | `paper_id` |
| `uniprot_accession` | uppercase accession | scalar or set-like string array | `uniprot_accession`, `all_mappings` |
| `go` | `GO:0000000` | set-like JSON array | `go_terms`, GO-derived arrays |
| `interpro` | `IPR000000` | set-like JSON array | `interpro_xrefs` |
| `pfam` | `PF00000` | set-like JSON array | `pfam_xrefs` |
| `reactome` | `R-HSA-123456` | set-like JSON array | `reactome_xrefs` |
| `pdb` | uppercase 4-char code | set-like JSON array | `pdb_xrefs` |
| `chembl` | `CHEMBL123` | scalar or set-like string array | `target_id`, `chembl_ids` |
| `drugbank` | `DB00001` | set-like string array | `drugbank_ids` |

## Why This Is Not Enum Governance

Identifier families expand over time as providers and ontologies add records.
Normalization must therefore:

- canonicalize syntax and casing
- deduplicate and sort when the field is explicitly set-like
- preserve valid new identifiers without requiring enum catalog updates

What can still be strict:

- companion status fields such as `mapping_status`
- provider-reviewed descriptive vocabularies such as `entry_type`
- derived publication taxonomy fields

## Evidence

- matrix entrypoint:
  [Normalization Plan P0-P6](../../05-engineering/normalization_plan_P0_P6.md)
  with generated artifact path
  `docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md`
- identifier fixtures:
  [non_chembl_identifier_cases.yaml](../../../tests/fixtures/normalization/non_chembl_identifier_cases.yaml)
- source registry:
  [reference_ids.py](../../../src/bioetl/domain/normalization/reference_ids.py)
