# Semantic Audit 2026-07-03 Issue Pack

This pack converts the confirmed residual findings from the `2026-07-03`
semantic audit refresh into a publish-ready GitHub issue set. It follows the
closed governance refinement wave `SEMANTIC-021` through `SEMANTIC-025` and
publishes only the two findings that remain actionable on the current repo
state.

Reviewed baseline: `reports/semantic_pipeline_audit/semantic_pipeline_audit_2026-07-01.md`

Refresh source: `reports/semantic_pipeline_audit/semantic_pipeline_audit_2026-07-03.md`

## Decision Summary

| Finding theme | Current repo actuality | Action |
| --- | --- | --- |
| Reviewed semantic baseline health | Reviewed package still reports `CRITICAL=0`, `HIGH=0`, pair rows `3245`, clusters `290` | Do not create umbrella blocker issue |
| Generator environment | Canonical generators could not be rerun because local/WLS venvs are broken and system `python3` misses `pandas`/`pyarrow` | Do not create issue from tooling environment alone |
| Active pipeline coverage gap | `chembl_target_protein_classification` is active but missing from the reviewed semantic pair matrix and cluster registry | Create issue |
| PubChem provider-local identifier naming drift | Canonical registry already distinguishes `pubchem_cid_identifier`, but internal config/contract surfaces still expose it as generic `molecule_id` | Create issue |

## Publish-Ready Set

1. `SEMANTIC-026` Cover `chembl_target_protein_classification` in the reviewed semantic audit package
2. `SEMANTIC-027` Finish explicit `pubchem_cid` naming across internal semantic surfaces

## Why Only These Two

The refreshed `2026-07-03` package is intentionally source-first and uses the
reviewed `2026-07-01` semantic baseline plus a live scope scan. That refresh
does not reproduce broad semantic drift. It confirms only two residuals:

- one active pipeline is outside the reviewed semantic coverage set
- one provider-local identifier family still uses a generic internal field name

Everything else in the refreshed package remains non-blocking and does not
justify additional GitHub issue churn.

## Evidence Anchors

- `reports/semantic_pipeline_audit/semantic_pipeline_audit_2026-07-03.md`
- `reports/semantic_pipeline_audit/semantic_pipeline_audit_manifest_2026-07-03.json`
- `reports/semantic_pipeline_audit/critical_inconsistencies_2026-07-03.md`
- `reports/semantic_pipeline_audit/semantic_pair_matrix_2026-07-01.csv`
- `reports/semantic_pipeline_audit/semantic_cluster_registry_2026-07-01.json`
- `configs/field_registry/canonical_registry.json`
- `configs/entities/chembl/target_protein_classification.yaml`
- `configs/entities/pubchem/compound.yaml`
- `docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md`
