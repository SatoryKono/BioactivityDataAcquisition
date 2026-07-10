# Semantic Pipeline Audit

Generated: `2026-05-15`

## Executive Summary

- Semantic clusters: `282`
- Pair rows: `3233`
- Base config files covered: `5`
- Base config semantic surfaces: `286`
- CRITICAL drift risks: `0`
- HIGH drift risks: `0`
- Normalization mismatches: `0`
- Validation strictness mismatches: `0`
- Typing conflicts: `0`
- Reviewed PARTIAL rows: `68`
- Reviewed WEAK inventory rows: `319`
- Reviewed generic collision rows: `0`
- Compatible normalization rows: `886`
- Compatible validation rows: `1039`
- Compatible typing rows: `654`
- Residual blocking tasks: `0`

## Artifact Index

- `semantic_pair_matrix_2026-05-15.csv`
- `semantic_cluster_registry_2026-05-15.json`
- `critical_inconsistencies_2026-05-15.md`
- `recommended_canonical_fields_2026-05-15.csv`
- `base_config_semantic_coverage_2026-05-15.json`
- `semantic_residual_backlog_2026-05-15.json`
- `semantic_residual_backlog_2026-05-15.md`
- `semantic_pipeline_audit_manifest_2026-05-15.json`

## Notes

This generated snapshot refreshes member evidence from active pipeline configs, base config defaults, normalization profiles, DQ visibility, Pandera-derived Gold contracts, and the reviewed semantic cluster registry.

## Reviewed Composite Typing Residuals

- Reviewed residual rows with composite `unknown` typing: `65`
- Covered by review registry: `65`
- Uncovered residual rows: `0`

| Review ID | Rows | Schema authority | Owner | Residual fields |
| --- | ---: | --- | --- | --- |
| composite_activity_unknown_schema | 5 | `seed_and_provider_gold_contracts` | BioETL Team | composite_activity.taxonomy_id |
| composite_system_fields_unknown_schema | 60 | `medallion_system_metadata_contract` | BioETL Team | composite_activity._lookup_method, composite_activity._original_id, composite_activity._source, composite_assay._lookup_method, composite_assay._original_id, composite_assay._source, composite_molecule._source, composite_target._lookup_method, composite_target._original_id, composite_target._source |
