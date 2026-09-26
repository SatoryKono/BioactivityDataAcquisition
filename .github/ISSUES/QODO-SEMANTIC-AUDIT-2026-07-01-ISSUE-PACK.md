# Qodo Semantic Audit 2026-07-01 Issue Pack

This pack reconciles the external Qodo semantic audit against the canonical
BioETL semantic-governance artifacts on current `main` and publishes only the
still-actionable follow-up work.

## Decision Summary

| Finding theme | External audit claim | Current repo actuality | Action |
| --- | --- | --- | --- |
| Semantic scope | Only `8` ETL pipelines matter | Canonical semantic audit covers `26` active pipeline surfaces | Do not create issue for the stale scope claim |
| Semantic registry | Missing unified semantic registry | Canonical governance already exists in `configs/field_registry/canonical_registry.json`, `configs/field_registry/semantic_audit_review_registry.yaml`, and generated semantic audit artifacts | Do not create issue for “missing registry” as a blocker |
| SMILES normalization | Active CRITICAL mismatch across entity/composite pipelines | Canonical pair matrix reports `Normalization DIFFERENT/CONFLICTING = 0`; `canonical_smiles` is a reviewed `PARTIAL` cluster, not an active conflict | Do not create issue for false CRITICAL remediation |
| Enum validation | Missing enum validation for `standard_type`, `standard_units`, `assay_type`, `target_type` | Config and schema authority already enforce enum validation | Do not create issue for already-implemented validation |
| `pchembl_value` range | Missing validation | Range validation already exists in config and schema authority | Do not create issue for stale validation claim |
| Activity identity | `record_id` is a second PK | `activity_id` is the business PK; `record_id` is a supporting FK / lineage field, not a second primary business identity | Do not create issue for false identity defect |
| ADR blocker debt | Active CRITICAL/HIGH semantic violations remain | Canonical semantic governance snapshot reports `CRITICAL=0`, `HIGH=0`, `blocking tasks=0` | Do not create issue for false blocker claims |
| Governance clarity | Semantic authority is too implicit for maintainers and external tools | Confirmed refinement target | Create issue |
| Assay metadata ownership | Reviewed assay metadata stays `WEAK` without a dedicated registry | Confirmed refinement target | Create issue |
| PARTIAL identifier roles | Owner/composite/lineage roles remain mostly review-only metadata | Confirmed refinement target | Create issue |
| Inherited composite evidence | Many rows remain `COMPATIBLE` because composite Gold/DQ authority is still implicit | Confirmed refinement target | Create issue |
| Validator transition coverage | Custom-validator transitions need stronger regression coverage | Confirmed refinement target | Create issue |

## Publish-Ready Set

1. [#5785](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5785) `SEMANTIC-021 Split and document base semantic-governance authority surfaces`
2. [#5786](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5786) `SEMANTIC-022 Create a dedicated assay metadata semantic registry`
3. [#5787](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5787) `SEMANTIC-023 Surface explicit owner roles for PARTIAL identifier clusters`
4. [#5788](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5788) `SEMANTIC-024 Publish explicit Gold and DQ evidence for inherited composite semantic fields`
5. [#5789](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5789) `SEMANTIC-025 Add regression coverage for semantic validator transitions`

## Why Only These Five

The external audit was directionally useful but factually stale against the
current semantic-governance baseline. The canonical `2026-07-01` snapshot does
not reproduce blocker-level semantic drift. The remaining work is governance
refinement:

- make semantic authority surfaces easier to interpret
- promote reviewed assay metadata into explicit canonical ownership
- separate provider-owned and lineage/composite roles for `PARTIAL` clusters
- publish stronger explicit contract evidence for inherited composite fields
- guard validator-evidence transitions with focused regression coverage

The pack therefore converts only confirmed, still-actionable governance work
into issues and intentionally does not republish false CRITICAL remediation
tasks.
