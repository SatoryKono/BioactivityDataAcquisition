# ChEMBL Ontology Governance

This reference documents how ChEMBL ontology and reference families are normalized
and whether they publish a companion bundle beyond the canonical identifier.

## Families

| Family | Canonical Prefix | Primary Fields | Companion Governance | Accepted Inputs | Version Source |
| --- | --- | --- | --- | --- | --- |
| `bao` | `BAO_` | `chembl_activity.bao_endpoint`, `chembl_activity.bao_format`, `chembl_assay.bao_format` | companion bundle with `iri`, `mapping_status`, `version` | `prefixed_id`, `colon_form`, `obo_iri` | `configs/vocab/chembl_ontology.yaml` |
| `uo` | `UO_` | `chembl_activity.uo_units` | companion bundle with `iri`, `mapping_status`, `version` | `prefixed_id`, `colon_form` | `configs/vocab/chembl_ontology.yaml` |
| `qudt` | `https://qudt.org/vocab/unit/` | `chembl_activity.qudt_units` | companion bundle with `iri`, `mapping_status`, `version` | `qudt_iri`, `legacy_openphacts_unit_uri`, `canonical_standard_unit_token` | `configs/vocab/chembl_ontology.yaml` |
| `bto` | `BTO_` | `chembl_tissue.bto_id` | companion bundle with `iri`, `mapping_status`, `version` | `prefixed_id`, `colon_form`, `obo_iri` | `configs/vocab/chembl_ontology.yaml` |
| `caloha` | `TS-` | `chembl_tissue.caloha_id` | `identifier_only_no_companion_bundle` | `ts_code`, `caloha_prefixed_code` | config-only |
| `efo` | `EFO_` | `chembl_cell_line.efo_id`, `chembl_tissue.efo_id` | companion bundle with `iri`, `mapping_status`, `version` | `prefixed_id`, `colon_form`, `obo_iri` | `configs/vocab/chembl_ontology.yaml` |
| `clo` | `CLO_` | `chembl_cell_line.clo_id` | companion bundle with `iri`, `mapping_status`, `version` | `prefixed_id`, `colon_form`, `obo_iri` | `configs/vocab/chembl_ontology.yaml` |
| `uberon` | `UBERON_` | `chembl_tissue.uberon_id` | companion bundle with `iri`, `mapping_status`, `version` | `prefixed_id`, `colon_form`, `obo_iri` | `configs/vocab/chembl_ontology.yaml` |
| `cellosaurus` | `CVCL_` | `chembl_cell_line.cellosaurus_id` | `identifier_only_no_companion_bundle` | `prefixed_id`, `colon_form`, `dash_form` | config-only |

## Unit Boundary

`chembl_activity` is the only current ChEMBL pipeline that publishes UO/QUDT
ontology companions for unit semantics.

`chembl_assay_parameters` intentionally does **not** publish ontology companion
fields today. The reviewed policy is:

- `companion_governance`: `standard_unit_only_no_ontology_companion_bundle`
- fields: `chembl_assay_parameters.standard_units`, `chembl_assay_parameters.units`
- rationale: keep canonical unit-token normalization without silently expanding
  Silver/Gold contracts or hash surfaces

The authoritative configuration for this decision lives in
`configs/vocab/chembl_ontology.yaml` under `unit_companion_policies`.

## Source Of Truth

- config: `configs/vocab/chembl_ontology.yaml`
- profile registry: `src/bioetl/domain/normalization/profiles/_chembl_policy_registry_data.py`
- normalization profiles:
  - `src/bioetl/domain/normalization/profiles/chembl_activity.py`
  - `src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py`
  - `src/bioetl/domain/normalization/profiles/chembl_cell_line.py`
  - `src/bioetl/domain/normalization/profiles/chembl_tissue.py`
