# JSON Field Typing Inventory

Scope: governed non-ChEMBL structured fields covered by ADR-035 canonical JSON string policy.

This inventory is the compact operator-facing subset for fields that MUST remain
`canonical JSON string` across Silver, domain schemas, and Gold contracts.
For a full generated cross-repo sweep, use
`src/tools/generate_json_field_typing_inventory.py`.

Related:
- `docs/02-architecture/decisions/ADR-035-json-field-typing-policy.md`
- `src/bioetl/domain/normalization/publication_structured_fields.py`
- `src/bioetl/domain/normalization/structured_payload_policies.py`

| Pipeline | Field | Representation | Notes |
| --- | --- | --- | --- |
| `crossref_publication` | `authors` | `canonical JSON string` | ordered author list |
| `crossref_publication` | `affiliation_list` | `canonical JSON string` | set-like affiliation list |
| `crossref_publication` | `author_details` | `canonical JSON string` | ordered author objects |
| `crossref_publication` | `author_orcids` | `canonical JSON string` | set-like ORCID list |
| `crossref_publication` | `issn_list` | `canonical JSON string` | set-like ISSN list |
| `crossref_publication` | `references` | `canonical JSON string` | ordered reference objects |
| `crossref_publication` | `subject_keywords` | `canonical JSON string` | set-like keyword list |
| `openalex_publication` | `authors` | `canonical JSON string` | ordered author list |
| `openalex_publication` | `affiliation_list` | `canonical JSON string` | set-like affiliation list |
| `openalex_publication` | `author_openalex_ids` | `canonical JSON string` | set-like identifier list |
| `openalex_publication` | `author_orcids` | `canonical JSON string` | set-like identifier list |
| `openalex_publication` | `institution_ids` | `canonical JSON string` | set-like identifier list |
| `openalex_publication` | `institution_country_codes` | `canonical JSON string` | set-like code list |
| `openalex_publication` | `ror_ids` | `canonical JSON string` | set-like identifier list |
| `openalex_publication` | `subject_topics` | `canonical JSON string` | set-like topic list |
| `openalex_publication` | `subject_keywords` | `canonical JSON string` | set-like keyword list |
| `openalex_publication` | `subject_mesh` | `canonical JSON string` | set-like mesh list |
| `openalex_publication` | `grants` | `canonical JSON string` | semantic-sensitive; persisted with `grants_raw_json` and `grants_canonical_json` companions |
| `openalex_publication` | `primary_topic` | `canonical JSON string` | semantic-sensitive object; persisted with `primary_topic_raw_json` and `primary_topic_canonical_json` companions |
| `pubmed_publication` | `authors` | `canonical JSON string` | ordered author list |
| `pubmed_publication` | `affiliation_list` | `canonical JSON string` | set-like affiliation list |
| `pubmed_publication` | `author_orcids` | `canonical JSON string` | set-like ORCID list |
| `pubmed_publication` | `chemicals` | `canonical JSON string` | set-like chemical list |
| `pubmed_publication` | `databanks` | `canonical JSON string` | set-like databank list |
| `pubmed_publication` | `gene_symbols` | `canonical JSON string` | set-like gene symbol list |
| `pubmed_publication` | `publication_types` | `canonical JSON string` | set-like raw publication type list |
| `pubmed_publication` | `subject_keywords` | `canonical JSON string` | set-like keyword list |
| `pubmed_publication` | `subject_mesh` | `canonical JSON string` | set-like mesh list |
| `pubmed_publication` | `affiliation_structured` | `canonical JSON string` | semantic-sensitive; persisted with `affiliation_structured_raw_json` and `affiliation_structured_canonical_json` companions |
| `pubmed_publication` | `authors_with_affiliations` | `canonical JSON string` | semantic-sensitive; persisted with `authors_with_affiliations_raw_json` and `authors_with_affiliations_canonical_json` companions |
| `pubmed_publication` | `publication_types` | `canonical JSON string` | governed JSON list in persisted contracts |
| `semanticscholar_publication` | `authors` | `canonical JSON string` | ordered author list |
| `semanticscholar_publication` | `affiliation_list` | `canonical JSON string` | set-like affiliation list |
| `semanticscholar_publication` | `author_orcids` | `canonical JSON string` | set-like identifier list |
| `semanticscholar_publication` | `author_s2_ids` | `canonical JSON string` | set-like identifier list |
| `semanticscholar_publication` | `author_h_indices` | `canonical JSON string` | semantic-sensitive; persisted with `author_h_indices_raw_json` and `author_h_indices_canonical_json` companions |
| `semanticscholar_publication` | `citation_contexts` | `canonical JSON string` | semantic-sensitive; persisted with `citation_contexts_raw_json` and `citation_contexts_canonical_json` companions |
| `semanticscholar_publication` | `publication_types` | `canonical JSON string` | semantic-sensitive set-like classification evidence |
| `semanticscholar_publication` | `subject_fields` | `canonical JSON string` | semantic-sensitive set-like classification evidence |
| `uniprot_protein` | `features_json` | `canonical JSON string` | semantic-sensitive ordered feature payload with `features_raw_json` and `features_canonical_json` companions |

Sidecar companion policy:
- semantic-sensitive fields keep the current canonical JSON field for compatibility
- raw provider evidence is preserved in `*_raw_json`
- semantic-ready canonical companion payloads are preserved in `*_canonical_json`
- shipped sidecar fields currently include
  `grants_raw_json`, `grants_canonical_json`,
  `primary_topic_raw_json`, `primary_topic_canonical_json`,
  `affiliation_structured_raw_json`, `affiliation_structured_canonical_json`,
  `authors_with_affiliations_raw_json`, `authors_with_affiliations_canonical_json`,
  `author_h_indices_raw_json`, `author_h_indices_canonical_json`,
  `citation_contexts_raw_json`, `citation_contexts_canonical_json`,
  `publication_types_raw_json`, `publication_types_canonical_json`,
  `subject_fields_raw_json`, `subject_fields_canonical_json`,
  `features_raw_json`, and `features_canonical_json`

Null semantics:
- absence of data MUST remain `NULL`
- new non-ChEMBL structured fields MUST NOT use native `list`/`dict` contracts in Silver or Gold
