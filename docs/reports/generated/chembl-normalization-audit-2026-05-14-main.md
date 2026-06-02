# ChEMBL Normalization Audit on `main`

Date: 2026-05-14

Scope: all current `chembl_*` entity pipelines on branch `main`:

- `chembl_activity`
- `chembl_assay`
- `chembl_molecule`
- `chembl_target`
- `chembl_target_component`
- `chembl_cell_line`
- `chembl_tissue`
- `chembl_compound_record`
- `chembl_protein_class`
- `chembl_assay_parameters`
- `chembl_subcellular_fraction`
- `chembl_publication`
- `chembl_publication_term`
- `chembl_publication_similarity`

Method:

- current registry/config/schema/profile/contract review
- current generated normalization matrix and Bronze observed-value inventory
- provider adapter model review
- targeted runtime checks through `RecordNormalizationProcessor`
- targeted audit test suites

## Executive Summary

### Established facts

- The ChEMBL family has one real shared normalization layer, not 14 unrelated implementations. The common seams are the ChEMBL policy registry, controlled vocabulary registry, ontology registry, reference-identifier registry, pseudo-null matrix, and JSON ordering/hash policy: `src/bioetl/domain/normalization/profiles/chembl_policy_registry.py`, `configs/vocab/chembl_controlled.yaml`, `configs/vocab/chembl_ontology.yaml`, `configs/vocab/chembl_reference_identifiers.yaml`, `src/bioetl/domain/normalization/profiles/chembl_pseudo_nulls.py`, `src/bioetl/domain/normalization/profiles/chembl_json_ordering_policy.py`.
- All 14 pipelines are currently registered in the canonical pipeline manifest with Silver schema and Gold contract surfaces: `src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py`.
- Fresh generated matrix on current code reports `828/828` explicit entity-record profile coverage and `100%` on the shipped meta/set-like/non-meta semantic invariants: `/tmp/chembl_norm_matrix_20260514/pipeline_normalization_field_matrix.csv` generated from `scripts/docs/generate_pipeline_normalization_field_matrix.py`.
- Enum/catalog/DQ/hash/derived-vocabulary invariants are actively enforced by tests, not just documented:
  `tests/integration/config/test_chembl_enum_parity.py`,
  `tests/integration/config/test_chembl_dq_catalog_sync.py`,
  `tests/integration/config/test_chembl_observed_value_fixtures.py`,
  `tests/integration/test_cross_pipeline_normalization.py`,
  `tests/contract/test_chembl_derived_vocabulary_contracts.py`,
  `tests/architecture/test_chembl_derived_vocabulary_policy.py`,
  `tests/unit/application/core/test_chembl_normalization_hash_golden.py`,
  `tests/unit/domain/hash_policy/test_chembl_high_risk_hash_golden.py`.

### Confirmed findings

1. `P0` confirmed cross-pipeline normalization drift on `bao_label`.
   `chembl_assay.bao_label` is canonicalized from sibling `bao_format`, but `chembl_activity.bao_label` is only pseudo-null cleaned and remains free text. This is not theoretical: two semantically equivalent `chembl_activity` records with the same `bao_format=BAO_0000357` but different `bao_label` spellings normalize differently and produce different `content_hash` values. Sources: `src/bioetl/domain/normalization/profiles/chembl_assay.py`, `src/bioetl/domain/normalization/profiles/chembl_activity.py`, `configs/vocab/chembl_ontology.yaml`, `src/bioetl/domain/schemas/chembl/activity.py`.
2. `P1` confirmed normalization-vs-DQ gap on `chembl_target.component_types` and `chembl_target.component_relationships`.
   They are canonicalized through strict JSON vocabulary rules and included in hash policy, but entity DQ does not expose explicit JSON-array enum validation. Unknown elements collapse the normalized field to `None`, which is deterministic but semantically lossy and currently not surfaced through explicit field-level DQ. Sources: `src/bioetl/domain/normalization/profiles/chembl_target.py`, `src/bioetl/domain/normalization/profiles/_profile_value_normalizers.py`, `configs/entities/chembl/target.yaml`.
3. `P1` source-schema anchoring is uneven across the family.
   API-backed pipelines `tissue`, `compound_record`, and `publication_similarity` have canonical pipeline registration and downstream schema/contract coverage, but they do not have typed DTO coverage in `CHEMBL_DTO_MODELS`, unlike `activity`, `assay`, `molecule`, `target`, `target_component`, `publication`, `cell_line`, and `protein_class`. Sources: `src/bioetl/infrastructure/adapters/chembl/constants.py`, `src/bioetl/infrastructure/adapters/chembl/client.py`, `src/bioetl/infrastructure/adapters/chembl/_entity_mapping_lookup.py`.
4. `P2` observed-value evidence depth is uneven.
   All 14 pipelines have tracked Bronze fixtures in `configs/base/bronze_fixture_manifest.yaml`, but the current Bronze observed-value inventory is shallow for some API-backed entities, especially `chembl_activity` and `chembl_molecule` (`5` raw fields each in the tracked CI sample). That limits confidence when classifying provider-side string fields that do not already have explicit registry ownership. Sources: `scripts/engineering/qa/report_chembl_observed_value_inventory.py`, `/tmp/chembl_obs_20260514.json`, `tests/fixtures/bronze/chembl/**`.

### Overall verdict

- Shared normalization architecture: strong
- Deterministic hashing architecture: strong, with one confirmed `bao_label` defect
- Cross-pipeline operator/unit/identifier/organism normalization: mostly aligned
- Enum/controlled-vocabulary externalization: materially present and enforced
- Full-family evidence depth against raw ChEMBL payload diversity: incomplete

## Fact Base

| Area | Pipeline | Artifact | Fact | Conclusion |
| --- | --- | --- | --- | --- |
| Registry completeness | all | `src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py` | 14 ChEMBL pipelines are registered with Silver schema and Gold contract classes | audit scope is structurally complete |
| Shared policy layer | all | `src/bioetl/domain/normalization/profiles/chembl_policy_registry.py` | semantic category, registry source, and invalid-value mode are centralized per field family | normalization logic is not primarily transformer-local |
| Controlled vocabularies | activity/assay/assay_parameters/target/publication | `configs/vocab/chembl_controlled.yaml` | units, operators, assay categories, OA status, target component JSON vocab, subcellular fractions are registry-backed | common vocab semantics are explicit |
| Ontology families | activity/assay/cell_line/tissue | `configs/vocab/chembl_ontology.yaml` | BAO/UO/QUDT/BTO/EFO/CLO/UBERON/Cellosaurus/CALOHA families are declared with accepted input forms and companion bundles | ontology handling is explicit, with some identifier-only exceptions |
| Reference IDs | cross-family | `configs/vocab/chembl_reference_identifiers.yaml` | ChEMBL IDs, NCBI taxonomy IDs, UniProt accessions, DOI/PMID/PMCID, MeSH IDs are centralized | identifier canonicalization is shared, not ad hoc |
| Hash policy | all | `src/bioetl/domain/transformations/hashing.py` | hash input is `provider + canonical_json(normalized_record)` with meta and `_` fields excluded | base hash contract is deterministic |
| JSON ordering | activity/publication/target/target_component | `src/bioetl/domain/normalization/profiles/chembl_json_ordering_policy.py` | set-like and order-sensitive JSON fields are explicitly separated | structured fields do not all hash the same way |
| Bronze evidence | all | `configs/base/bronze_fixture_manifest.yaml`, `/tmp/chembl_obs_20260514.json` | all 14 have tracked fixtures, but raw field coverage differs sharply by entity | inventory confidence is entity-asymmetric |
| Runtime defect | activity | direct processor check on 2026-05-14 | same `bao_format` + noisy vs canonical `bao_label` yields different normalized records and different hashes | confirmed `P0` hash-relevant drift |
| Runtime semantic loss | target | direct processor check on 2026-05-14 | unknown `component_types` / `component_relationships` JSON elements normalize to `None` | confirmed `P1` normalization-vs-DQ exposure gap |

## Shared, Subfamily, and Entity-Specific Rules

### Shared family-wide rules

- Pseudo-null collapse: `src/bioetl/domain/normalization/profiles/chembl_pseudo_nulls.py`
- ChEMBL/reference identifier normalization: `configs/vocab/chembl_reference_identifiers.yaml`, `src/bioetl/domain/normalization/profiles/_chembl_reference_identifier_rules.py`
- Boolean/flag families: `configs/vocab/chembl_controlled.yaml`, `src/bioetl/domain/normalization/profiles/chembl_policy_registry_data.py`
- Canonical hashing and structured JSON ordering: `src/bioetl/domain/transformations/hashing.py`, `src/bioetl/domain/normalization/profiles/chembl_json_ordering_policy.py`

### Subfamily rules

- Bioactivity-like: `chembl_activity` and `chembl_assay_parameters` share operator, raw-unit, standard-unit, standard-type, and reference-identifier families.
- Assay/context-like: `chembl_assay`, `chembl_subcellular_fraction`, and `chembl_assay_parameters` share BAO context, subcellular-fraction vocabulary, and assay-linked identifiers.
- Target/component-like: `chembl_target`, `chembl_target_component`, `chembl_cell_line`, `chembl_tissue` share taxonomy, ontology IDs, and organism canonicalization.
- Publication-like: `chembl_publication`, `chembl_publication_term`, `chembl_publication_similarity` share DOI/PMID/PMCID/MeSH normalization and publication taxonomy.
- Reference-dictionary-like: `chembl_subcellular_fraction`, `chembl_tissue`, `chembl_cell_line`, `chembl_protein_class` mostly normalize identifiers, names, and hierarchy/context fields.

### Entity-specific rules

- `chembl_publication`: dual-field strategy for `publication_type_raw` -> `publication_type` -> `publication_type_unified` / `publication_subclass` / `publication_class`.
- `chembl_assay_parameters`: dual-field strategy for `type_raw` -> `type`, with `standard_type` remaining strict.
- `chembl_subcellular_fraction`: dual-field strategy for `subcellular_fraction_raw` -> `subcellular_fraction`; entity id is derived from normalized value.
- `chembl_target`: derives `organism_class` from `organism` and `taxonomy_id`; collapses target component JSON lists through special normalizers.
- `chembl_activity`: carries both BAO identifiers and BAO label, but currently does not canonicalize `bao_label`.

## Unified Enum / Vocabulary Inventory

Complete per-field field-level inventory already exists in the current generated normalization matrix:

- `docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md`
- `/tmp/chembl_norm_matrix_20260514/pipeline_normalization_field_matrix.csv`

The rows below list all materially distinct enum-like families and the main cross-pipeline seams that matter for Silver/Gold/hash/composites.

| Pipeline | Field(s) | Layer(s) | Classification | Current strategy | Observed examples from repo | Target strategy |
| --- | --- | --- | --- | --- | --- | --- |
| `chembl_activity` | `standard_relation`, `relation` | Silver/Gold | strict operator + raw controlled vocabulary | canonical operator normalization; strict enum for `standard_relation` | `=`, `>`, `<`, `>=`, `<=`, `~` in repo fixtures/tests | keep shared operator seam |
| `chembl_activity` | `standard_type`, `assay_type`, `data_validity_comment` | Silver/Gold | strict enum | enum-backed profile + DQ | repo-observed `EC50`, `IC50`, `Ki` for `standard_type` | keep |
| `chembl_activity` | `standard_units`, `units` | Silver/Gold | strict enum + controlled unit | alias collapse + unit policy | provider examples include `nM`, `uM`/`µM`, `%` in tests | keep |
| `chembl_activity` | `standard_flag`, `potential_duplicate`, `manual_curation_flag` | Silver/Gold | flag-like | shared binary-flag coercion | `0/1` families | keep |
| `chembl_activity` | `bao_endpoint`, `bao_format`, `uo_units`, `qudt_units` and companion fields | Silver/Gold | ontology-backed + mapping metadata | canonical prefix/IRI/status/version companion bundle | BAO/UO/QUDT values appear in fixtures/tests | keep |
| `chembl_activity` | `bao_label` | Silver/Gold/hash | same-semantics BAO label | currently only pseudo-null cleanup | confirmed divergence between `noisy label` and `single protein format` | mirror assay-style label resolution from `bao_format` |
| `chembl_assay` | `assay_type`, `assay_test_type`, `assay_group`, `relationship_type` | Silver/Gold | strict enum | enum-backed profile + DQ | repo-observed `B`, `F`, `D` | keep |
| `chembl_assay` | `assay_category`, `confidence_description` | Silver/Gold | controlled vocabulary | governed vocab; fail closed where configured | `Direct single protein target assigned` observed | keep |
| `chembl_assay` | `assay_subcellular_fraction` + `assay_subcellular_fraction_raw` | Silver/Gold | controlled vocabulary + raw sidecar | preserve raw + canonical normalized field | observed raw examples in assay-derived fixtures | keep |
| `chembl_assay` | `bao_format`, `bao_label`, companion fields | Silver/Gold/hash | ontology-backed + derived vocabulary | canonical BAO ID and label resolution from sibling field | `BAO_0000219`, `cell-based format` observed | keep |
| `chembl_assay_parameters` | `standard_type`, `standard_relation`, `standard_units` | Silver/Gold | strict enum / strict operator / strict unit | shared with activity family | no broad Bronze set; profile and DQ are explicit | keep |
| `chembl_assay_parameters` | `type` + `type_raw` | Silver/Gold | controlled vocabulary + raw sidecar | preserve raw lexeme, uppercase canonical unknowns | repo fixtures and contract tests cover split behavior | keep |
| `chembl_molecule` | `molecule_type`, `structure_type`, `max_phase`, `ro3_pass` | Silver/Gold | strict enum / quasi-enum | enum/quasi-enum coercion | observed `max_phase` 0..4 in Bronze sample | keep |
| `chembl_molecule` | `oral`, `parenteral`, `topical`, `therapeutic_flag`, `withdrawn_flag` | Silver/Gold | boolean-like | shared boolean coercion | current fixtures shallow | keep |
| `chembl_molecule` | `black_box_warning`, `dosed_ingredient`, `polymer_flag`, `first_in_class`, `inorganic_flag`, `natural_product`, `prodrug` | Silver/Gold | flag-like / reviewed provider codes | shared flag-code policy | current fixtures shallow | keep |
| `chembl_target` | `target_type` | Silver/Gold | strict enum | enum-backed profile + DQ | observed `SINGLE PROTEIN` | keep |
| `chembl_target` | `organism_class` | Silver/Gold | controlled vocabulary derived from organism/taxonomy | derived strict canonicalization + DQ | observed set not directly present in Bronze fixture | keep |
| `chembl_target` | `component_types`, `component_relationships` | Silver/Gold/hash/composite | controlled vocabulary in JSON arrays | strict JSON vocab normalization to canonical JSON | derived from nested `target_components`; no direct Bronze scalar field | add explicit JSON-array DQ and raw/canonical review strategy |
| `chembl_target` | `component_accessions` | Silver/Gold/hash/composite | reference identifier JSON array | ordered accession normalization | derived from nested `target_components` | add array-level DQ visibility |
| `chembl_target_component` | `component_type` | Silver/Gold | strict enum | scalar strict enum + DQ | observed `PROTEIN` | keep |
| `chembl_cell_line` | `cellosaurus_id`, `clo_id`, `efo_id` and companions | Silver/Gold | ontology/reference identifiers | shared ontology canonicalization | observed CLO/EFO/Cellosaurus values in Bronze sample | keep |
| `chembl_tissue` | `bto_id`, `caloha_id`, `efo_id`, `uberon_id` and companions | Silver/Gold | ontology/reference identifiers | shared ontology canonicalization, with CALOHA identifier-only policy | observed BTO/EFO/UBERON/CALOHA values in Bronze sample | keep |
| `chembl_publication` | `publication_type_raw` -> `publication_type` -> `publication_type_unified` / `publication_subclass` / `publication_class` | Silver/Gold/hash | raw sidecar + strict enum + derived vocabulary | explicit dual-field taxonomy mapping | repo Bronze shows `doc_type`; contract tests cover split behavior | keep |
| `chembl_publication` | `oa_status`, `is_oa` | Silver/Gold | controlled vocabulary + boolean | shared OA status and bool policy | Bronze sample shallow for OA | keep |
| `chembl_publication_term` | `term_type`, `mesh_id` | Silver/Gold | strict enum + ontology/reference identifier | enum + MeSH id canonicalization | term types are governed in enum config and tests | keep |
| `chembl_publication_similarity` | `pubmed_id1`, `pubmed_id2` | Silver/Gold | reference identifier | shared PMID canonicalization | Bronze sample shallow | keep |
| `chembl_subcellular_fraction` | `subcellular_fraction_raw` -> `subcellular_fraction` | Silver/Gold/derived | controlled derived vocabulary + raw sidecar | preserve raw plus canonical normalized reference value | observed `Membrane`, `Microsome` | keep |

## Reuse / Drift Matrix

| Rule family | Pipelines using it | Implemented where | Identical behavior? | Drift risk | Recommendation |
| --- | --- | --- | --- | --- | --- |
| Reference identifier normalization | activity, assay, assay_parameters, molecule, target, target_component, cell_line, tissue, compound_record, publication, publication_term, publication_similarity, subcellular_fraction | `configs/vocab/chembl_reference_identifiers.yaml`, `_chembl_reference_identifier_rules.py` | mostly yes | low | keep |
| Unit/operator normalization | activity, assay_parameters | `configs/vocab/chembl_controlled.yaml`, `_profile_governed_value_normalizers.py` | yes | low | keep |
| Organism normalization | activity, target, target_component | `normalize_profile_chembl_organism_name` | yes, covered by integration test | low | keep |
| Ontology companion bundles | activity, assay, cell_line, tissue | `configs/vocab/chembl_ontology.yaml`, companion normalizers | mostly yes | medium | fix `activity.bao_label` to align with assay bundle semantics |
| JSON structured hash policy | activity, publication, target, target_component | `chembl_json_ordering_policy.py`, hash golden tests | yes | low | keep |
| Raw-plus-canonical sidecars | publication, assay_parameters, subcellular_fraction | profile special rules + config metadata | yes | low | keep |
| JSON controlled vocab arrays | target | target profile special rules | no; normalization exists but DQ exposure is weaker than scalar counterpart in `target_component` | medium | add JSON-array DQ/contract coverage |
| Provider DTO schema anchoring | activity, assay, molecule, target, target_component, publication, cell_line, protein_class vs tissue, compound_record, publication_similarity | `CHEMBL_DTO_MODELS` | no | medium | add missing DTO coverage for API-backed entities |

## Gap Analysis

### Missing normalization

- Confirmed: `chembl_activity.bao_label` lacks identifier-backed canonicalization even though the same semantic field is canonicalized in `chembl_assay`.

### Weak canonicalization

- Confirmed: `chembl_target.component_types` and `component_relationships` fail closed by nulling the whole JSON array on unknown elements; this is deterministic but lossy and currently opaque from DQ.

### Missing enum externalization

- Not confirmed as a family-wide defect. Current shared registries already externalize most high-risk enum-like surfaces.

### Schema / contract mismatch

- No direct Silver/Gold schema mismatch was confirmed in the audited suites.
- Source-model mismatch was confirmed at adapter DTO level for some API-backed entities.

### Hashing inconsistency

- Confirmed: `chembl_activity.bao_label` causes hash divergence for semantically equivalent BAO context.

### DQ mismatch

- Confirmed: `chembl_target.component_types` and `component_relationships` are normalized against a strict controlled vocabulary seam without equivalent explicit JSON-array DQ coverage in entity config.

### Ontology-handling mismatch

- Confirmed: BAO label handling differs between `activity` and `assay`.

### JSON canonicalization mismatch

- Not confirmed for current shipped high-risk structured fields; hash golden tests are green.

### Architectural placement issue

- No I/O leakage inside domain normalization was confirmed.
- Source-schema typing asymmetry exists in the adapter layer rather than the domain layer.

### Cross-pipeline normalization drift

- Confirmed: `activity.bao_label` vs `assay.bao_label`.

## Recommended Expansion / Repair Plan

### P0

1. Canonicalize `chembl_activity.bao_label` from sibling `bao_format`, mirroring `chembl_assay`.
   - Layer: domain normalization profile + ontology policy registry
   - Target files: `src/bioetl/domain/normalization/profiles/chembl_activity.py`, `configs/vocab/chembl_ontology.yaml`, optionally `src/bioetl/domain/normalization/profiles/chembl_policy_registry_data.py`
   - Input/output: noisy/free-text BAO label -> canonical identifier-backed label
   - Backward compatibility: additive at schema level, breaking at hash level
   - `content_hash` impact: yes, activity hashes will migrate for rows where label spelling differs but BAO ID is equivalent
   - Silver/Gold/DQ impact: higher consistency; new contract/golden tests required
   - Composite impact: stabilizes downstream activity identity/versioning

### P1

1. Add explicit JSON-array DQ/contract coverage for `chembl_target.component_types` and `chembl_target.component_relationships`.
   - Layer: entity DQ config + normalization matrix/test coverage
   - Target files: `configs/entities/chembl/target.yaml`, `tests/integration/config/test_chembl_dq_catalog_sync.py`, matrix/tests
   - Input/output: canonical JSON arrays remain, but unknown members must surface through explicit reviewed DQ semantics
   - Backward compatibility: additive if warning-only; potentially filtering-breaking if error-level
   - `content_hash` impact: none if normalization logic unchanged
   - Composite impact: reduces silent semantic loss before Gold filters and joins
2. Decide whether these target array fields need raw/canonical sidecars.
   - Rationale: current behavior can erase provider detail by collapsing to `None`
   - Candidate fields: `component_types`, `component_relationships`, possibly `component_accessions`
3. Add typed DTO coverage for API-backed `tissue`, `compound_record`, and `publication_similarity`.
   - Layer: adapter/domain DTO models
   - Target files: `src/bioetl/domain/entities/**`, `src/bioetl/infrastructure/adapters/chembl/constants.py`, related tests
   - Impact: stronger direct anchoring to ChEMBL API shape; no normalization semantics change required

### P2

1. Enrich Bronze observed-value fixtures for shallow entities, especially `activity` and `molecule`.
2. Extend observed-value governance to cover more entity families where current fixture evidence is thin or registry-backed behavior is indirect.
3. Add an explicit activity BAO label cross-layer hash contract test parallel to the current assay test.

## Validation Performed

- Confirmed local `HEAD == main`
- Generated fresh normalization matrix: `./.venv/bin/python scripts/docs/generate_pipeline_normalization_field_matrix.py --out-dir /tmp/chembl_norm_matrix_20260514`
- Generated fresh Bronze observed-value inventory: `./.venv/bin/python scripts/engineering/qa/report_chembl_observed_value_inventory.py --json-out /tmp/chembl_obs_20260514.json --csv-out /tmp/chembl_obs_20260514.csv --markdown-out /tmp/chembl_obs_20260514.md`
- Ran targeted audit suites:
  `tests/integration/config/test_chembl_enum_parity.py`
  `tests/integration/config/test_chembl_dq_catalog_sync.py`
  `tests/integration/config/test_chembl_observed_value_fixtures.py`
  `tests/integration/test_cross_pipeline_normalization.py`
  `tests/contract/test_chembl_derived_vocabulary_contracts.py`
  `tests/architecture/test_chembl_derived_vocabulary_policy.py`
  `tests/unit/application/core/test_chembl_normalization_hash_golden.py`
  `tests/unit/domain/hash_policy/test_chembl_high_risk_hash_golden.py`
  `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py`
- Ran two direct processor probes:
  - `chembl_activity.bao_label`: confirmed hash divergence under equivalent `bao_format`
  - `chembl_target.component_types/component_relationships`: confirmed collapse to `None` on unknown JSON-array members
