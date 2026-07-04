______________________________________________________________________

Version: 1.1.0
Status: Active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-17'

______________________________________________________________________

# ChEMBL Protein Classification Migration Closeout

This closeout covers GitHub issues #5245 through #5252.

## Decisions

- BioETL canonical ownership remains `chembl_protein_class` /
  `protein_class`; ChEMBL `protein_classification` is the external provider
  resource name.
- `chembl_target` is target-only for content hashing and does not own
  `protein_classifications` or `target_protein_class_*_L1..L5`.
- `chembl_target_protein_classification` owns target-level classification
  relation rows and publishes the active Gold contract
  `chembl_target_protein_classification_v2.2.json`.
- Path fields (`path_ids`, `path_names`, `path_labels`) are canonical.
  `l1_*` through `l5_*` remain legacy projections.
- `canonical_l1` is the versioned normalized top-level evidence used by
  composite target typing; raw `l1_name` remains provider evidence.
- `target_protein_class_type` is not ChEMBL `target.target_type`. It is a
  composite semantic summary derived from informative `canonical_l1` values.
- `major_family` is computed from L2+ evidence and remains separate from the
  top-level classification rule.
- Snapshot enrichment reads local `chembl.target`,
  `chembl.target_component`, and `chembl.protein_class` tables before Silver
  hashing; runtime HTTP lookup against `/protein_classification` is not part
  of this relation path.

## Acceptance Gates

- Domain graph resolves full root-to-leaf paths and rejects parent cycles,
  replacement cycles, missing nodes, duplicate levels, and broken level gaps.
- Resolution service publishes path fields, depth/root metadata, and legacy
  L1-L5 projection fields from the same hierarchy object.
- Snapshot data source attaches deterministic source manifest fields and
  fingerprinted row-count evidence to every relation row.
- Transformer, domain schema, Gold contract schema, entity config, contract
  registry, and generated JSON export expose the same active field set.
- Target type mapping artifacts are generated from
  `configs/enums/protein_class_l1_target_type.csv` and guarded by
  `tests/architecture/test_protein_class_target_type_codegen_contract.py`.
- Registration tests guard that `target_protein_classification` uses the local
  snapshot data source instead of the generic ChEMBL HTTP adapter.

## Known Limitation

Current local `chembl.protein_class` snapshot rows do not carry ChEMBL status
resource metadata. Until that metadata is added upstream, `chembl_release` and
`chembl_api_version` are published as `unknown` and
`source_manifest_status` is `release_metadata_unavailable`.
