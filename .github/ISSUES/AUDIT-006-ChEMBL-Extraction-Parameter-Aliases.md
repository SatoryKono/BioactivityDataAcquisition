# [configs] Govern ChEMBL extraction-parameter aliases explicitly

## Problem
ChEMBL extraction parameters mix canonical project field names and provider API field names. chembl_target schema/DQ/hash uses taxonomy_id, while extraction params use tax_id__isnull. chembl_cell_line uses canonical cell_id in schema but filter_field: cell_chembl_id in config. The adapter has _SILVER_TO_CHEMBL_API_FIELD for several canonical ID aliases, and the comment states that ChEMBL silently ignores unknown filter params and returns all records, making mapping correctness critical. Extraction params are currently merged into HTTP params directly via ExtractionParams.to_query_dict().

## Evidence
- configs/entities/chembl/target.yaml: schema/business field: taxonomy_id, quality validation field: taxonomy_id, extraction param: tax_id__isnull
- configs/entities/chembl/cell_line.yaml: schema/business field: cell_id, filters.input_filter.filter_field: cell_chembl_id
- src/bioetl/infrastructure/adapters/chembl/constants.py: _SILVER_TO_CHEMBL_API_FIELD
- src/bioetl/infrastructure/adapters/chembl/client.py::ChemblAdapter._build_params
- src/bioetl/infrastructure/adapters/chembl/client.py::ChemblAdapter._normalize_filter_field
- src/bioetl/infrastructure/adapters/chembl/client.py::ChemblAdapter._build_filter_params

## Root Cause
Provider API aliases are not governed as an explicit config contract. Runtime filtering can depend on unvalidated provider-specific parameter names.

## Architectural Impact
- Determinism / reproducibility: an ignored filter can fetch a different record universe
- DQ / validation: schema field names and extraction field names can diverge silently
- Observability: over-fetch caused by ignored filters can appear as volume anomaly, not config error
- Layer boundaries: alias translation belongs in infrastructure adapter/config validation, not domain

## Required Outcome
After the fix:
- every ChEMBL extraction/filter field is classified as either canonical project field (translated by adapter alias mapping) or explicit provider API field (validated against an allowlist)
- tax_id__isnull is no longer an unexplained local string in target config
- cell_chembl_id usage in cell-line filtering is either translated from cell_id or explicitly declared as provider API field
- invalid ChEMBL extraction params fail preflight/config validation before network calls

## Priority
P0 - The adapter evidence states ChEMBL silently ignores unknown filter params, which can cause over-fetch and non-reproducible dataset scope.

## Size
M - Requires adapter alias registry, config validation, and config updates.

## Labels
architecture, dq, testing, configs, governance
