# JSON Field Typing Inventory (Silver vs Gold)

Scope: `src/bioetl/infrastructure/schemas/silver.py` и `src/bioetl/domain/contracts/gold/*.py`.

| Field                        | Silver type kind              | Gold type kind                  | Status                         |
| ---------------------------- | ----------------------------- | ------------------------------- | ------------------------------ |
| `active_sites`               | canonical_string              | —                               | only one layer (manual review) |
| `activity_properties`        | canonical_string              | —                               | only one layer (manual review) |
| `affiliation_list`           | canonical_string              | canonical_string                | consistent (canonical string)  |
| `affiliation_structured`     | canonical_string              | —                               | only one layer (manual review) |
| `all_mappings`               | canonical_string              | canonical_string                | consistent (canonical string)  |
| `alternative_id`             | native_list                   | native_object                   | consistent legacy (native)     |
| `assay_classifications`      | canonical_string              | —                               | only one layer (manual review) |
| `assay_parameters`           | canonical_string              | —                               | only one layer (manual review) |
| `author_details`             | canonical_string              | —                               | only one layer (manual review) |
| `author_h_indices`           | canonical_string              | —                               | only one layer (manual review) |
| `author_orcids`              | —                             | canonical_string                | only one layer (manual review) |
| `author_s2_ids`              | canonical_string              | canonical_string                | consistent (canonical string)  |
| `authors`                    | canonical_string              | canonical_string                | consistent (canonical string)  |
| `authors_with_affiliations`  | canonical_string              | —                               | only one layer (manual review) |
| `binding_sites`              | canonical_string              | —                               | only one layer (manual review) |
| `chembl_ids`                 | canonical_string              | canonical_string                | consistent (canonical string)  |
| `chemicals`                  | canonical_string              | native_object                   | MISMATCH                       |
| `citation_contexts`          | canonical_string              | canonical_string                | consistent (canonical string)  |
| `component_accessions`       | native_list                   | native_object                   | consistent legacy (native)     |
| `component_descriptions`     | native_list                   | —                               | only one layer (manual review) |
| `component_ids`              | native_list                   | native_object                   | consistent legacy (native)     |
| `component_relationships`    | native_list                   | native_object                   | consistent legacy (native)     |
| `component_types`            | native_list                   | native_object                   | consistent legacy (native)     |
| `content_domain_domains`     | native_list                   | native_object                   | consistent legacy (native)     |
| `cross_references`           | —                             | canonical_string                | only one layer (manual review) |
| `databanks`                  | canonical_string              | native_object                   | MISMATCH                       |
| `domains`                    | canonical_string              | —                               | only one layer (manual review) |
| `drugbank_ids`               | canonical_string              | canonical_string                | consistent (canonical string)  |
| `features_json`              | canonical_string              | canonical_string                | consistent (canonical string)  |
| `gene_names`                 | native_list                   | native_object                   | consistent legacy (native)     |
| `gene_symbols`               | canonical_string              | native_object                   | MISMATCH                       |
| `go_terms`                   | canonical_string              | canonical_string                | consistent (canonical string)  |
| `grants`                     | —                             | canonical_string                | only one layer (manual review) |
| `institution_country_codes`  | native_list                   | native_object                   | consistent legacy (native)     |
| `institution_ids`            | native_list                   | native_object                   | consistent legacy (native)     |
| `interpro_xrefs`             | canonical_string              | canonical_string                | consistent (canonical string)  |
| `issn_list`                  | canonical_string              | canonical_string                | consistent (canonical string)  |
| `pdb_xrefs`                  | canonical_string              | canonical_string                | consistent (canonical string)  |
| `pfam_xrefs`                 | canonical_string              | canonical_string                | consistent (canonical string)  |
| `pipeline_stages`            | —                             | canonical_string                | only one layer (manual review) |
| `primary_topic`              | canonical_string              | canonical_string                | consistent (canonical string)  |
| `protein_classification_ids` | native_list                   | native_object                   | consistent legacy (native)     |
| `protein_classifications`    | canonical_string              | —                               | only one layer (manual review) |
| `publication_type`           | —                             | native_object                   | only one layer (manual review) |
| `publication_type_list`      | canonical_string              | —                               | only one layer (manual review) |
| `publication_types`          | canonical_string, native_list | canonical_string, native_object | MISMATCH                       |
| `reactome_xrefs`             | canonical_string              | canonical_string                | consistent (canonical string)  |
| `references`                 | canonical_string              | canonical_string                | consistent (canonical string)  |
| `ror_ids`                    | canonical_string              | canonical_string                | consistent (canonical string)  |
| `subject_keywords`           | native_list                   | native_object                   | consistent legacy (native)     |
| `subject_mesh`               | native_list                   | native_object                   | consistent legacy (native)     |
| `subject_topics`             | canonical_string              | canonical_string                | consistent (canonical string)  |
| `target_components`          | —                             | canonical_string                | only one layer (manual review) |
| `variant_sequence_json`      | canonical_string              | canonical_string                | consistent (canonical string)  |
