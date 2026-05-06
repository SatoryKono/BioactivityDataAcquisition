# [dq] Split ChEMBL standard-unit enum from raw and ontology unit vocabularies

## Problem
standard_units is treated as a finite enum in ChEMBL activity and assay-parameters DQ configs. The shared controlled vocabulary registry also defines broader unit canonicalization with invalid_value_mode: preserve_unknown_lexeme, QUDT identifiers, UO companion fields, and fields including both raw units and standard_units. This mixes strict standard-unit validation, raw unit alias preservation, and ontology-backed unit canonicalization in one policy family.

## Evidence
- configs/entities/chembl/activity.yaml: quality.entity_field_validations[].field: standard_units, units, uo_units, qudt_units
- configs/entities/chembl/assay_parameters.yaml: quality.entity_field_validations[].field: standard_units, units
- configs/enums/chembl.yaml: activity.standard_units
- configs/vocab/chembl_controlled.yaml: controlled_vocabularies.units
- src/bioetl/domain/normalization/profiles/chembl_activity.py::CHEMBL_ACTIVITY_PROFILE
- src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py::CHEMBL_ASSAY_PARAMETERS_PROFILE

## Root Cause
Controlled-vocabulary design flaw: strict standard-unit enum, raw unit aliases, and ontology unit IDs share one governance boundary.

## Architectural Impact
- DQ / validation: raw units can be preserved while standard units are strict, but the boundary is not explicit
- Determinism / hashing: unit alias collapse can change content hash semantics
- Gold strict validation: Gold can fail if standard/raw/ontology unit rules diverge
- Composite pipelines: downstream grouping by units can change analytical meaning

## Required Outcome
After the fix:
- standard_units is governed by a strict provider/versioned allowed set
- raw units is governed by a raw-unit alias canonicalization policy that preserves unknowns for review
- uo_units and qudt_units are governed by ontology/reference unit policies
- DQ rules distinguish strict enum failure from raw-unit warning/review behavior
- content-hash impact is explicit for every unit normalization change

## Priority
P0 - Units affect analytical grouping, DQ acceptance, and hash identity.

## Size
M - Touches shared vocab config, two ChEMBL profiles, two entity configs, and tests.

## Labels
dq, testing, configs, governance
