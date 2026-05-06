# [testing] Add parity tests for ChEMBL enum, vocabulary, profile and DQ policies

## Problem
ChEMBL enum and controlled-vocabulary definitions exist across several policy surfaces: configs/enums/chembl.yaml, configs/vocab/chembl_controlled.yaml, configs/vocab/chembl_ontology.yaml, domain policy registry data, normalization profiles, and entity-level DQ rules. The audit found concrete drift in confidence_description and structural duplication in units and JSON ordering. There is no single parity gate covering these ChEMBL policy surfaces.

## Evidence
- configs/enums/chembl.yaml
- configs/vocab/chembl_controlled.yaml
- configs/vocab/chembl_ontology.yaml
- configs/entities/chembl/activity.yaml
- configs/entities/chembl/assay.yaml
- configs/entities/chembl/assay_parameters.yaml
- configs/entities/chembl/target.yaml
- src/bioetl/domain/normalization/profiles/_chembl_policy_registry_data.py
- src/bioetl/domain/normalization/profiles/_chembl_policy_registry.py
- src/bioetl/domain/normalization/profiles/chembl_activity.py
- src/bioetl/domain/normalization/profiles/chembl_assay.py
- src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py
- src/bioetl/domain/normalization/profiles/chembl_target.py

## Root Cause
Missing governance test suite for cross-surface ChEMBL normalization policy parity.

## Architectural Impact
- DQ / validation: profile and DQ enum behavior can diverge
- Determinism: hash policy and normalization policy can drift
- Reproducibility: config changes can alter behavior without failing tests
- Governance: ADR-038 enum externalization is not fully protected by automated parity

## Required Outcome
After the fix:
- CI fails when ChEMBL enum/vocab/profile/DQ policy surfaces diverge
- every ChEMBL enum-like field has an explicit classification: strict enum, controlled vocabulary, flag-like, operator, ontology/reference identifier, unit-like
- parity tests cover all current chembl_* profiles

## Priority
P1 - This prevents recurrence of confirmed P0 drift but does not itself change production semantics.

## Size
M - Multiple test modules and policy comparisons, limited production code change.

## Labels
dq, testing, configs, governance
