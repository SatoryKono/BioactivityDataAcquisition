# ChEMBL Assay Historical Nullability Analysis

Date: 2026-03-31

## Scope

This report studies `chembl_assay` using repository-local evidence only:

- Schema: [assay.py](../../../src/bioetl/domain/schemas/chembl/assay.py)
- Transformer: [assay_transformer.py](../../../src/bioetl/application/pipelines/chembl/assay_transformer.py)
- Pipeline config: [assay.yaml](../../../configs/entities/chembl/assay.yaml)
- Tests:
  - [test_chembl_transformers.py](../../../tests/unit/application/pipelines/test_chembl_transformers.py)
  - [test_transformer_snapshots.py](../../../tests/unit/application/pipelines/test_transformer_snapshots.py)
  - [test_schemas.py](../../../tests/unit/domain/schemas/chembl/test_schemas.py)
- Structural contract export: [chembl_matrix_structural_contract_v1.json](chembl_matrix_structural_contract_v1.json)
- Historical data sample:
  - [test_chembl_assay_full_cycle.yaml](../../../tests/fixtures/vcr/chembl/test_chembl_assay_full_cycle.yaml)
  - [test_chembl_assay_metadata_fields.yaml](../../../tests/fixtures/vcr/chembl/test_chembl_assay_metadata_fields.yaml)
  - [test_chembl_assay_confidence_score.yaml](../../../tests/fixtures/vcr/chembl/test_chembl_assay_confidence_score.yaml)

Historical completeness below is based on `110` unique assay API payloads deduplicated by `assay_chembl_id` across the dedicated assay VCR files above.

## Executive Summary

- Fields already non-nullable and fully supported by observed history: `assay_id`, `description`, `assay_type`, `target_id`, `publication_id`, `bao_format`.
- Current `>99.99%` observed candidates for additional `nullable=False` consideration:
  - `assay_type_description`
  - `relationship_type`
  - `confidence_score`
  - `src_id`
  - `aidx`
- `Normalization before tightening` candidates:
  - `relationship_description`
  - `confidence_description`
  - `bao_label`
- Runtime contract is now aligned for current non-nullable assay fields:
  - `publication_id`, `bao_format`, `assay_type_description`, `relationship_type`, and `confidence_score` are guarded by `silver_filters.required_fields` in [assay.yaml](../../../configs/entities/chembl/assay.yaml).
- Strong sparse/optional fields that should remain nullable:
  - `assay_organism`, `assay_taxonomy_id`
  - `assay_tissue`, `assay_cell_type`, `assay_subcellular_fraction`
  - `cell_id`, `tissue_id`
  - all `variant_*` fields
  - `assay_test_type`, `assay_category`, `assay_group`, `assay_strain`, `src_assay_id`, `assay_pref_name`, `score`
- Type cleanup candidates:
  - `assay_taxonomy_id`
  - `variant_taxonomy_id`

## Important Caveat

The `>99.99%` threshold is satisfied in the observed repository sample only when the field is `100%` populated in the `110/110` unique assay payloads. This is strong local evidence, but still conditioned on:

- current ChEMBL extraction parameters in [assay.yaml](../../../configs/entities/chembl/assay.yaml)
- current repository VCR coverage, not the entire upstream ChEMBL corpus

When a field is extraction-locked by filters such as `relationship_type: D`, `confidence_score__gte: 8`, or `src_id: 1`, that is called out below.

## Current Contract Notes

From the structural contract export:

- `assay_id`, `assay_type`, `description`, `target_id` are runtime-required through `silver_required_fields`.
- `publication_id`, `bao_format`, `assay_type_description`, `relationship_type`, and `confidence_score` are now runtime-required and quarantine before schema validation.

Inference:

- The original assay contract gap has been closed. Remaining assay work should focus on normalization and consistency rather than required-field alignment.

## Field Analysis

| Field                        | Current Nullable | Completeness | Observed Types                               | Normalization Opportunities                                                             | Validation Opportunities                                                 | Recommendation                                                          | Risk   |
| ---------------------------- | ---------------- | -----------: | -------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------- | ------ |
| `assay_id`                   | `False`          |       `100%` | `str`                                        | Already normalized via alias support from `assay_chembl_id`; optional trim guard only   | Keep ChEMBL ID regex                                                     | Keep as-is                                                              | Low    |
| `description`                | `False`          |       `100%` | `str`                                        | Optional trim and whitespace collapse                                                   | Optional minimum-length or non-blank guard                               | Keep as-is                                                              | Low    |
| `assay_type`                 | `False`          |       `100%` | `str`                                        | Trim and uppercase controlled vocabulary normalization                                  | Existing enum is good; keep strict enum                                  | Keep as-is                                                              | Low    |
| `assay_type_description`     | `True`           |       `100%` | `str`                                        | Controlled label normalization or derive from `assay_type`                              | Enum or cross-field consistency with `assay_type`                        | Safe candidate; tighten after adding consistency test                   | Low    |
| `assay_test_type`            | `True`           |         `0%` | none                                         | None until field appears historically                                                   | Existing optional enum is enough                                         | Keep nullable                                                           | Low    |
| `assay_category`             | `True`           |         `0%` | none                                         | None until field appears historically                                                   | Existing optional enum is enough                                         | Keep nullable                                                           | Low    |
| `assay_group`                | `True`           |         `0%` | none                                         | None until field appears historically                                                   | Free-text only if field starts appearing                                 | Keep nullable                                                           | Low    |
| `assay_organism`             | `True`           |     `97.27%` | `str`                                        | ChEMBL organism display normalization, whitespace collapse, trailing annotation cleanup | Cross-check with `assay_taxonomy_id` when both exist                     | Keep nullable; normalization now implemented, no tightening yet         | Medium |
| `assay_taxonomy_id`          | `True`           |     `97.27%` | `int`                                        | Already validated through `validate_taxonomy_id`                                        | Nullable integer semantics are good; improve physical dtype              | Keep nullable; type cleanup candidate                                   | Medium |
| `assay_strain`               | `True`           |         `0%` | none                                         | None until field appears historically                                                   | None now                                                                 | Keep nullable                                                           | Low    |
| `assay_tissue`               | `True`           |      `8.18%` | `str`                                        | Trim, whitespace normalization                                                          | Optional controlled vocabulary later if needed                           | Keep nullable                                                           | Low    |
| `assay_cell_type`            | `True`           |     `33.64%` | `str`                                        | Trim, whitespace normalization                                                          | Optional pattern or lookup later                                         | Keep nullable                                                           | Low    |
| `assay_subcellular_fraction` | `True`           |      `3.64%` | `str`                                        | Trim and case normalization                                                             | Candidate enum only after more evidence                                  | Keep nullable                                                           | Low    |
| `target_id`                  | `False`          |       `100%` | `str`                                        | Already source-to-silver mapped cleanly                                                 | Keep ChEMBL ID regex                                                     | Keep as-is                                                              | Low    |
| `relationship_type`          | `True`           |       `100%` | `str`                                        | Trim and uppercase                                                                      | Existing enum is good; extraction currently fixes this to `D`            | Safe candidate; tightening is extraction-conditioned                    | Low    |
| `relationship_description`   | `True`           |       `100%` | `str`                                        | Prefer deriving from `relationship_type` or canonical mapping                           | Add cross-field consistency with `relationship_type`                     | Normalize first, then tighten if still desired                          | Medium |
| `confidence_score`           | `True`           |       `100%` | `int`                                        | Already integer-like; no extra normalization needed                                     | Existing range is good; extraction currently constrains values to `8..9` | Safe candidate; tightening is extraction-conditioned                    | Low    |
| `confidence_description`     | `True`           |       `100%` | `str`                                        | Prefer deriving from `confidence_score` or controlled mapping                           | Add cross-field consistency with `confidence_score`                      | Normalize first, then tighten if still desired                          | Medium |
| `src_id`                     | `True`           |       `100%` | `int`                                        | Already integer-like                                                                    | Candidate enum `{1}` under current ChEMBL extraction                     | Safe candidate but low business value                                   | Low    |
| `src_assay_id`               | `True`           |         `0%` | none                                         | None until field appears                                                                | None now                                                                 | Keep nullable                                                           | Low    |
| `publication_id`             | `False`          |       `100%` | `str`                                        | Already source-mapped from `document_chembl_id`                                         | Keep ChEMBL ID regex; add runtime required guard                         | Keep non-nullable; fix filter alignment                                 | Low    |
| `assay_pref_name`            | `True`           |         `0%` | none                                         | None until field appears                                                                | None now                                                                 | Keep nullable                                                           | Low    |
| `score`                      | `True`           |         `0%` | none                                         | None until field appears                                                                | Existing float coercion path is enough                                   | Keep nullable                                                           | Low    |
| `cell_id`                    | `True`           |     `30.00%` | `str`                                        | Trim only                                                                               | Add ChEMBL ID pattern if not already enforced elsewhere                  | Keep nullable                                                           | Low    |
| `tissue_id`                  | `True`           |      `8.18%` | `str`                                        | Trim only                                                                               | Add ChEMBL ID pattern if not already enforced elsewhere                  | Keep nullable                                                           | Low    |
| `bao_format`                 | `False`          |       `100%` | `str`                                        | BAO canonicalization to `BAO_########`                                                  | Existing BAO regex is good; runtime required guard is now aligned        | Keep non-nullable; normalization implemented                            | Low    |
| `bao_label`                  | `True`           |       `100%` | `str`                                        | Controlled mapping from `bao_format`; fallback trim/lower                               | Add cross-field consistency with `bao_format`                            | Normalize first, then reconsider tightening                             | Medium |
| `aidx`                       | `True`           |       `100%` | `str`                                        | Trim only                                                                               | Add pattern check if semantics are known                                 | Safe candidate, but low ROI                                             | Low    |
| `variant_accession`          | `True`           |      `7.27%` | derived `str` when present                   | Normalize UniProt-like accessions if needed                                             | Add accession pattern if business use increases                          | Keep nullable                                                           | Low    |
| `variant_isoform`            | `True`           |         `0%` | none                                         | None now                                                                                | None now                                                                 | Keep nullable                                                           | Low    |
| `variant_mutation`           | `True`           |      `7.27%` | `str`                                        | Trim and mutation notation normalization later                                          | Optional mutation pattern checks                                         | Keep nullable                                                           | Low    |
| `variant_organism`           | `True`           |      `7.27%` | `str`                                        | Reuse ChEMBL organism normalization helper                                              | Optional consistency with `variant_taxonomy_id`                          | Keep nullable                                                           | Low    |
| `variant_sequence`           | `True`           |      `7.27%` | `str` after flattening                       | Uppercase amino acid sequence normalization if needed                                   | Optional amino-acid alphabet check                                       | Keep nullable                                                           | Low    |
| `variant_taxonomy_id`        | `True`           |      `7.27%` | `int`                                        | Already validated through `validate_taxonomy_id`                                        | Improve physical dtype to nullable integer                               | Keep nullable; type cleanup candidate                                   | Low    |
| `variant_sequence_json`      | `True`           |      `7.27%` | JSON string after serialization              | None beyond serialization                                                               | Optional JSON-shape regression tests                                     | Keep nullable                                                           | Low    |
| `assay_classifications`      | `True`           |       `100%` | raw `list`, serialized JSON string in silver | Serialization already stable                                                            | Optional JSON-shape or list-shape checks only                            | Keep nullable; semantic payload is optional despite structural presence | Low    |
| `assay_parameters`           | `True`           |       `100%` | raw `list`, serialized JSON string in silver | Serialization already stable                                                            | Optional JSON-shape or list-shape checks only                            | Keep nullable; semantic payload is optional despite structural presence | Low    |

## Safe Nullable Tightenings

These satisfy the observed `>99.99%` threshold in local history and do not require major new normalization logic first.

- `assay_type_description`
  - Why: `110/110`, only two observed values: `Binding`, `Functional`
  - Caveat: best paired with a cross-field consistency test against `assay_type`
- `relationship_type`
  - Why: `110/110`, single observed value `D`
  - Caveat: evidence is conditioned on current extraction params
- `confidence_score`
  - Why: `110/110`, observed ints only, values `8` and `9`
  - Caveat: evidence is conditioned on current extraction params
- `src_id`
  - Why: `110/110`, single observed value `1`
  - Caveat: low ROI, strongly extraction-conditioned
- `aidx`
  - Why: `110/110`, single observed value `CLD0`
  - Caveat: business value is weak unless this field matters downstream

## Normalization Before Tightening

- `relationship_description`
  - Historical completeness is `100%`, but this is redundant with `relationship_type`
  - Better to derive or validate against `relationship_type` before tightening
- `confidence_description`
  - Historical completeness is `100%`, but this is redundant with `confidence_score`
  - Better to derive or validate against `confidence_score` before tightening
- `bao_label`
  - Historical completeness is `100%`
  - Best next step is canonical mapping from `bao_format`, not direct tightening first
- `bao_format`
  - Already non-nullable
  - Still worth adding BAO canonicalization in the transformer to harden future drift
- `assay_organism`
  - Useful normalization target, but not a non-nullable candidate because completeness is below threshold

## Type Cleanup Candidates

- `assay_taxonomy_id`
  - Observed raw type is `int` when present
  - Current schema uses `Series[float] | None` only to support nullable integer behavior
  - Recommend moving toward a proper nullable integer representation if the Pandera/DataFrame stack supports it cleanly
- `variant_taxonomy_id`
  - Same reasoning as `assay_taxonomy_id`

## Keep Nullable

- `assay_test_type`
- `assay_category`
- `assay_group`
- `assay_organism`
- `assay_taxonomy_id`
- `assay_strain`
- `assay_tissue`
- `assay_cell_type`
- `assay_subcellular_fraction`
- `src_assay_id`
- `assay_pref_name`
- `score`
- `cell_id`
- `tissue_id`
- all `variant_*` fields
- `assay_classifications`
- `assay_parameters`

For `assay_classifications` and `assay_parameters`, the key nuance is:

- they are structurally present in observed history as empty lists
- but semantically they still behave like optional metadata
- tightening them to non-nullable adds little value and risks over-constraining future sparse payloads

## Recommended PR Waves

### PR0: Contract Alignment

Goal:

- align runtime required-field quarantine policy with current schema

Changes:

- update [assay.yaml](../../../configs/entities/chembl/assay.yaml)
  - add `publication_id`
  - add `bao_format`
  - to `filters.silver_filters.required_fields`

Tests:

- schema/transformer regression for missing `publication_id`
- schema/transformer regression for missing `bao_format`
- config alignment test similar to `chembl_activity` required-field coverage

Status:

- Implemented

Risk:

- low

### PR1: Safe Nullable Tightenings

Goal:

- tighten only fields with clean observed evidence and low semantic ambiguity

Suggested fields:

- `assay_type_description`
- `relationship_type`
- `confidence_score`
- optionally `src_id`
- optionally `aidx`

Files:

- [assay.py](../../../src/bioetl/domain/schemas/chembl/assay.py)
- [test_schemas.py](../../../tests/unit/domain/schemas/chembl/test_schemas.py)
- [test_chembl_transformers.py](../../../tests/unit/application/pipelines/test_chembl_transformers.py)

Tests:

- reject-null schema tests for each tightened field
- one transformer smoke assertion per field

Risk:

- low for `assay_type_description`, `relationship_type`, `confidence_score`
- low to medium for `src_id` and `aidx` because they are more extraction-artifact-like

### PR2: Normalization Hardening

Goal:

- add normalization where it improves determinism before any further tightening

Suggested scope:

- `bao_format`
  - reuse BAO canonicalization pattern used in activity normalization
- `bao_label`
  - map from `bao_format` or validate against controlled label set
- `assay_type_description`
  - cross-check against `assay_type`
- `relationship_description`
  - cross-check against `relationship_type`
- `confidence_description`
  - cross-check against `confidence_score`
- `assay_organism`
  - optional display normalization only

Status:

- In progress
- Implemented so far:
  - `bao_format` canonicalization to `BAO_########`
  - `bao_label` evidence-backed normalization from known `bao_format` mappings
  - `assay_organism` display normalization
- Still open:
  - explicit cross-field consistency enforcement for `bao_format <-> bao_label`
  - possible consistency rules for `assay_type_description`, `relationship_description`, `confidence_description`

Files:

- [assay_transformer.py](../../../src/bioetl/application/pipelines/chembl/assay_transformer.py)
- [normalization_chembl.py](../../../src/bioetl/domain/normalization_chembl.py)
- assay-related tests under `tests/unit`

Risk:

- low to medium

### PR3: Validation and Type Cleanup

Goal:

- strengthen deterministic checks without broad nullability changes

Suggested scope:

- add cross-field validation:
  - `assay_type` \<-> `assay_type_description`
  - `relationship_type` \<-> `relationship_description`
  - `confidence_score` \<-> `confidence_description`
  - `bao_format` \<-> `bao_label`
- evaluate nullable integer cleanup for:
  - `assay_taxonomy_id`
  - `variant_taxonomy_id`

Risk:

- medium

## Recommended Rollout Order

1. `PR0`: align runtime required fields for `publication_id` and `bao_format`
1. `PR1`: tighten `assay_type_description`, `relationship_type`, `confidence_score`
1. `PR2`: normalize `bao_format`, `bao_label`, and add controlled cross-field consistency
1. `PR3`: type cleanup for taxonomy IDs and optional additional tightenings like `src_id` or `aidx`

## Bottom Line

Best immediate moves:

- fix the runtime contract gap for `publication_id` and `bao_format`
- then tighten `assay_type_description`, `relationship_type`, and `confidence_score`

Best fields to leave alone for now:

- `assay_organism`
- `assay_taxonomy_id`
- all sparse biological-context fields
- all `variant_*` fields
- JSON metadata fields that are structurally present but semantically optional
