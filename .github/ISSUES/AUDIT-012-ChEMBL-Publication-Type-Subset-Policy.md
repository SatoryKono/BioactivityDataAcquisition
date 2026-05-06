# [dq] Encode source-specific ChEMBL publication-type subset policy

## Problem
The global ChEMBL enum config defines a broad cross-provider publication taxonomy, while the chembl_publication entity DQ config allows only journal-article, book, dataset, and patent for publication_type. The ChEMBL publication profile explicitly preserves publication_type_raw and maps provider-native publication types to canonical publication types. The source-specific subset is currently encoded in entity DQ/filter config, but not separated as an explicit source-specific subset policy.

## Evidence
- configs/enums/chembl.yaml: publication.types, publication.native_doc_types
- configs/entities/chembl/publication.yaml: quality.entity_field_validations[].field: publication_type, allowed: journal-article, book, dataset, patent; filters.extraction_params.doc_type: PUBLICATION; silver_filters.columns.publication_type; gold_filters.columns.publication_type
- src/bioetl/domain/normalization/profiles/chembl_publication.py: publication_type_raw, publication_type, normalize_profile_publication_type, normalize_profile_publication_type_raw
- src/bioetl/domain/normalization/profiles/_publication_classification_rules.py

## Root Cause
Global publication taxonomy and ChEMBL-source DQ subset are mixed implicitly in entity-level config instead of being governed as separate classification layers.

## Architectural Impact
- DQ / validation: source-specific filtering can be mistaken for global enum truth
- Gold strict validation: Gold contract may reject valid global publication types from other providers if policy is reused incorrectly
- Composite pipelines: cross-provider publication merges depend on consistent type taxonomy
- Governance: enum externalization and source-specific DQ policy are not explicitly separated

## Required Outcome
After the fix:
- global publication type taxonomy remains broad and cross-provider
- ChEMBL-specific allowed subset is represented as a source-specific DQ/filter policy
- publication_type_raw and canonical publication_type semantics are documented in config metadata
- tests prove ChEMBL subset policy does not redefine global publication enum

## Priority
P1 - This prevents source-specific ChEMBL DQ constraints from leaking into cross-provider publication semantics.

## Size
M - Config metadata, config validation, and focused tests.

## Labels
dq, testing, configs, governance
