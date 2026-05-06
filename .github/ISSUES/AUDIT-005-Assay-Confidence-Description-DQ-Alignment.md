# [dq] Align assay confidence-description normalization with DQ policy

## Problem
chembl_assay DQ config treats confidence_description as an enum with a fixed allowed set. The controlled vocabulary registry marks assay_confidence_descriptions with invalid_value_mode: reject_unknown_lexeme. The assay normalization profile normalizes the same field with preserve_unknown=True. This is an explicit drift between normalization and DQ policy: unknown values are preserved by normalization but rejected by controlled-vocabulary/DQ governance.

## Evidence
- configs/entities/chembl/assay.yaml: quality.entity_field_validations[].field: confidence_description, type: enum
- configs/vocab/chembl_controlled.yaml: controlled_vocabularies.assay_confidence_descriptions.invalid_value_mode: reject_unknown_lexeme
- src/bioetl/domain/normalization/profiles/chembl_assay.py: _CONTROLLED_CONFIDENCE_FIELDS, _SPECIAL_RULE_COMPONENTS, normalize_profile_governed_vocabulary(... preserve_unknown=True ...)
- src/bioetl/domain/normalization/profiles/_chembl_policy_registry_data.py

## Root Cause
Controlled-vocabulary policy drift between domain normalization profile and externalized DQ/vocabulary config.

## Architectural Impact
- DQ / validation: normalized Silver can preserve values that DQ rejects
- Reproducibility: behavior depends on which layer is used as source of truth
- Gold strict validation: Gold validation can fail on values accepted by normalization
- Observability: unknown lexemes may not have consistent warning/quarantine metrics

## Required Outcome
After the fix:
- confidence_description has one invalid-value mode across profile, controlled vocabulary config, and entity DQ
- unknown values are either consistently rejected/quarantined or consistently preserved with DQ warning and explicit downstream handling
- Silver and Gold validation behavior is deterministic and tested

## Priority
P0 - The current drift can produce a Silver/Gold validation mismatch for a controlled-vocabulary field.

## Size
M - One pipeline plus shared vocabulary policy and tests.

## Labels
dq, testing, configs, governance
