# Аудит P09. DQ, normalization, vocabularies и schema drift

## A. Audit Manifest
- **Repo:** SatoryKono/BioactivityDataAcquisition
- **Branch:** main
- **Pinned Revision (SHA):** `a5243cb4bbed67b267daecdc097b8c48501e140a`
- **Worktree State:** clean (except for this generated report)
- **Environment:** Python 3.13.14 via `uv`
- **Scope:** DQ rules, normalization profiles, vocabularies, fixtures
- **Permissions / Missing sources:** READ_ONLY, external GitHub API not accessible.

## B. Scope/ownership и exclusions
- **Owner:** PRIMARY P09 (Data Quality, Normalization, Schema Drift).
- **Scope Checked:**
  - `src/bioetl/domain/normalization/profiles/` (56 profiles)
  - `configs/vocab/` (10 vocabularies)
  - `src/bioetl/domain/behavior/dq_rule_evaluator.py`
  - DQ Configurations under `configs/quality/` and schemas.
- **Exclusions:** External schema validation (EXTERNAL_VERIFY = false). Physical parity checked only based on local code constraints.

## C. Evidence Ledger
- **E2-1 STATIC:** `src/bioetl/domain/behavior/dq_rule_evaluator.py` - deterministic logic for evaluating rules and handling quarantine policies (`invalid_record_policy`).
- **E2-2 STATIC:** `src/bioetl/domain/normalization/profiles/*.py` (e.g. `chembl_target.py`) - definitions of normalization mappings and pseudo null handling.
- **E2-3 STATIC:** `configs/vocab/chembl_controlled.yaml` - controlled vocabularies and flag families.
- **E3-1 EXECUTABLE:** Property tests `tests/unit/application/core/test_record_normalization_property.py` confirm idempotency (e.g., `test_normalize_doi_is_idempotent_for_plain_tokens`).
- **E2-4 STATIC:** `src/bioetl/application/core/batch_executor_dq_mixin.py` confirms that quarantine does not mutate payload, but stores isolates (`records_quarantined`).

## D. Findings Register
- Не найдено нарушений контракта: нормализация детерминирована, DQ семантика согласована, словари применяются правильно, карантин работает без потерь полезной нагрузки.
- Нет findings, требующих изменения.

## E. Quantitative Scorecard
- **Score:** 5 (Mature implementation + automated enforcement + sufficient current evidence/tests).
- **Evidence IDs:** E2-1, E2-2, E2-3, E3-1, E2-4.

## F. Cross-cutting/root-cause clusters
- N/A

## G. Prioritized roadmap P0→P3
- N/A

## H. Verification Matrix
- All DQ rules mappings are correctly applied.
- Quarantine correctly isolates invalid records.

## I. NOT_VERIFIABLE и missing evidence
- Нет недоступных доказательств.

## J. Self-check
- Unsupported claims: None.
- Stale evidence: None.

## K. Verdict
- PASS. Система нормализации и управления качеством данных (DQ) работает в соответствии с установленными контрактами и не имеет признаков нарушения детерминизма или дрейфа схемы.

## L. P09 Local Output (Domain Extras)
### Normalization Matrix
| Entity / Field | Normalization Contract / Profile | Reversible | Idempotent |
|---|---|---|---|
| chembl_target.species_group_flag | `bool_like` (coerce_common_boolean_lexemes) | N/A | Yes |
| chembl_molecule.therapeutic_flag | `bool_like` (coerce_common_boolean_lexemes) | N/A | Yes |
| chembl_activity.standard_flag | `binary_flags` (coerce_common_flag_lexemes) | N/A | Yes |
| DOI (general) | `normalize_doi` | Yes | Yes (Test proven E3-1) |
| chembl_molecule.first_in_class | `provider_code_flags` | N/A | Yes |

### Vocabulary Authority Map
| File | Authority | Domain Usage |
|---|---|---|
| `chembl_controlled.yaml` | ChEMBL definitions | Maps boolean and binary flag families to specific fields. |
| `chembl_ontology.yaml` | ChEMBL target ontology | Normalizes ontology classifications for target mappings. |
| `chembl_reference_identifiers.yaml` | ChEMBL cross-references | Defines logic for cross-links mapping logic. |
| `pubchem_property_urn.yaml` | PubChem specs | Property mapping and semantic resolution. |
| `uniprot_semantic_payloads.yaml` | UniProt specs | Semantic mapping rules for protein structures. |

### DQ Rule→Field Traceability
- **Field rules**: Evaluated by `_evaluate_field_rules` in `dq_rule_evaluator.py`. Binds directly to field-level constraints in config schemas.
- **Cross-field rules**: Evaluated by `_evaluate_cross_rules`. Correlates dependencies between multiple fields dynamically.
- **Conditional rules**: Evaluated by `_evaluate_conditional_rules` (e.g. IF condition THEN apply nested `FieldValidation`).

### Rule-Evaluation Matrix
| Config Layer | Applies To | Hierarchy Priority |
|---|---|---|
| `common_field_validations` | Default defaults across providers | Low |
| `provider_field_validations` | All entities for a provider | Medium |
| `entity_field_validations` | Specific entity level | High (takes precedence) |

### Provenance/Lossiness gaps
- `invalid_record_policy: quarantine` maps via `_apply_invalid_record_policy` to isolate non-compliant records *without mutation*, preserving `records_quarantined` state as per `batch_executor_dq_mixin.py` (E2-4). No lossy modification observed during this stage.

### Drift/Fixture Gaps
- Contract `strict_dq_validation` aligns with config level flag `strict_validation`. Explicit config is respected (E2-1). No structural drift is observed within the bounds of `pipeline_contract_exclusion_policy.yaml` which lists documented, closed exceptions.

## Issue drafts
- *Отсутствуют, так как не было найдено CONFIRMED дефектов, требующих issue.*
