# [governance] Align ChEMBL Gold contract registry statuses with active pipeline modes

## Problem
The contract registry marks several ChEMBL contracts as deprecated, including chembl.assay_parameters, chembl.publication_similarity, chembl.publication_term, and chembl.subcellular_fraction. At least some corresponding entity configs still define active Gold write modes, for example chembl_assay_parameters has gold: mode: scd2 and chembl_publication_term has gold: mode: overwrite. This creates a contract lifecycle mismatch for Gold outputs.

## Evidence
- configs/base/contract_registry.yaml:
  - chembl.assay_parameters.status: deprecated
  - chembl.publication_similarity.status: deprecated
  - chembl.publication_term.status: deprecated
  - chembl.subcellular_fraction.status: deprecated
- configs/entities/chembl/assay_parameters.yaml: pipeline.sink.gold.mode: scd2
- configs/entities/chembl/publication_term.yaml: pipeline.sink.gold.mode: overwrite
- configs/entities/chembl/publication_similarity.yaml: Gold mode config
- configs/entities/chembl/subcellular_fraction.yaml: Gold mode config
- src/bioetl/domain/contracts/gold/_chembl_activity_assay_schemas.py
- src/bioetl/domain/contracts/gold/_chembl_reference_publication_schemas.py
- src/bioetl/domain/contracts/gold/_chembl_target_lookup_schemas.py

## Root Cause
Governance drift between contract lifecycle status and active Gold pipeline configuration.

## Architectural Impact
- Gold strict validation: active Gold outputs can reference deprecated contracts
- Reproducibility: replay metadata and contract registry may report incompatible lifecycle state
- DQ / validation: DQ policy resolution can select a deprecated contract for active pipeline output
- Governance: contract registry no longer reflects operational truth

## Required Outcome
After the fix:
- any ChEMBL pipeline with sink.gold.enabled != false and an active Gold mode has an active contract registry entry
- deprecated ChEMBL contracts are used only for non-active legacy contracts with documented replacement
- contract registry validation fails if active Gold config points to a deprecated or missing contract
- migration guide fields are populated where a deprecated contract remains

## Priority
P0 - Gold strict validation and contract governance cannot be reliable while active Gold outputs are marked deprecated.

## Size
M - Primarily config and governance tests, with possible generated contract artifact updates.

## Labels
dq, testing, configs, governance
