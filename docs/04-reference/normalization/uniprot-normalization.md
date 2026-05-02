______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-02'

______________________________________________________________________

# UniProt Normalization

Scope:

- `uniprot_protein`
- `uniprot_idmapping`
- the UniProt-derived anchors consumed by `composite_target`

Primary evidence:

- [Normalization Plan P0-P6](../../05-engineering/normalization_plan_P0_P6.md)
  plus generated matrix path
  `docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md`
- [non_chembl_observed_values.yaml](../../../tests/fixtures/normalization/non_chembl_observed_values.yaml)
- [non_chembl_identifier_cases.yaml](../../../tests/fixtures/normalization/non_chembl_identifier_cases.yaml)
- [reference-identifiers.md](reference-identifiers.md)

## Identifier And Evidence Families

| Field family | Governance category | Current rule |
| --- | --- | --- |
| `accession`, `uniprot_accession` | identifier namespace | canonical UniProt accession syntax/casing is governed; values are not enumized |
| `all_mappings`, `secondary_accessions` | canonical identifier arrays | canonicalized through the UniProt accession family in `domain.normalization.reference_ids` |
| `target_id` | canonical identifier | canonicalized as a ChEMBL identifier, not a finite enum |
| `taxonomy_id` | numeric identifier | deterministic numeric coercion/range validation, not a vocabulary |
| `go_terms`, `pdb_xrefs`, `interpro_xrefs`, `pfam_xrefs`, `reactome_xrefs`, `drugbank_ids`, `chembl_ids` | ontology-backed or reference-backed IDs | canonical family normalization applies; do not freeze them as reviewed enums |

## Strictly Governed Vocabularies

These UniProt-facing fields are currently bounded reviewed vocabularies:

| Field | Pipeline | Category |
| --- | --- | --- |
| `entry_type` | `uniprot_protein` | strict enum |
| `flag` | `uniprot_protein` | strict enum |
| `protein_existence` | `uniprot_protein` | strict enum |
| `mapping_status` | `uniprot_idmapping` | strict enum |

The presence of reviewed vocabularies for these descriptive/status fields does
not justify enumizing identifier arrays or ontology references in adjacent
fields.

## Structured Features Payload

`uniprot_protein.features_json` is a semantic-sensitive structured payload with
explicit companions:

| Field | Role |
| --- | --- |
| `features_json` | canonical JSON string used by the current persisted contract |
| `features_canonical_json` | canonical sidecar for semantic-forward workflows |
| `features_raw_json` | raw provider envelope that must survive future semantic transforms |

Collection semantics are ordered sequence. Reordering feature objects is
hash-affecting unless the governing policy changes explicitly.

## Composite Target Impact

Current composite target normalization boundary:

- seed anchor: `target_id`
- bridge anchor: `uniprot_accession`
- gate: `mapping_status=found` remains the reviewed success condition for
  idmapping evidence
- non-key UniProt evidence such as `taxonomy_id`, GO/reference arrays, and
  feature-derived fields remains upstream inherited in matrix evidence

This means:

- composite logic depends on canonicalized identifiers and reviewed mapping
  status, not on local re-normalization of every UniProt field
- upstream normalization changes in `uniprot_idmapping` or `uniprot_protein`
  can change composite outputs even when `configs/composites/target.yaml`
  remains stable

## Related References

- [non-chembl-normalization-overview.md](non-chembl-normalization-overview.md)
- [UniProt protein provider reference](../providers/uniprot/protein.md)
- [UniProt idmapping provider reference](../providers/uniprot/idmapping.md)
