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

`chembl_activity` publishes the primary UO/QUDT ontology companion bundle for
unit semantics.

`chembl_assay_parameters` also participates in the same ontology families, but
only through an additive optional companion bundle declared under
`unit_companion_policies` in `configs/vocab/chembl_ontology.yaml`.

The effective policy is:

- `companion_governance`: `optional_uo_qudt_companion_bundle`
- primary unit-token surfaces remain authoritative:
  `chembl_assay_parameters.standard_units`, `chembl_assay_parameters.units`
- optional ontology surfaces may be populated when runtime/provider context
  emits them:
  `chembl_assay_parameters.uo_units`,
  `chembl_assay_parameters.uo_unit_iri`,
  `chembl_assay_parameters.uo_unit_mapping_status`,
  `chembl_assay_parameters.uo_ontology_version`,
  `chembl_assay_parameters.qudt_units`,
  `chembl_assay_parameters.qudt_unit_iri`,
  `chembl_assay_parameters.qudt_unit_mapping_status`,
  `chembl_assay_parameters.qudt_ontology_version`
- rationale: preserve canonical analytical unit-token semantics while allowing
  nullable ontology sidecars without changing the authoritative unit boundary

## Source Of Truth

- config: `configs/vocab/chembl_ontology.yaml`
- profile registry: `src/bioetl/domain/normalization/profiles/_chembl_policy_registry_data.py`
- normalization profiles:
  - `src/bioetl/domain/normalization/profiles/chembl_activity.py`
  - `src/bioetl/domain/normalization/profiles/chembl_assay_parameters.py`
  - `src/bioetl/domain/normalization/profiles/chembl_cell_line.py`
  - `src/bioetl/domain/normalization/profiles/chembl_tissue.py`
