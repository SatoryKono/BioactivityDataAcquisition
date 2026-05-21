# ChEMBL Normalization Audit on Current `main`

Date: 2026-05-19

Scope: all active `chembl_*` pipelines in the current repository state:

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

- source-first review of current configs, normalization profiles, transformers, Silver schemas, Gold contracts, registries, fixtures, composite configs, and generated inventories
- targeted audit test suites for enum/DQ/catalog/hash/derived-vocabulary/matrix parity
- direct architecture checks on domain normalization import and I/O boundaries

## Executive Summary

### Established facts

- All 14 `chembl_*` pipelines are active in the canonical ChEMBL registry manifest, and each ships a transformer class, Pandera domain schema, Silver schema, and Gold schema surface in one place:
  `src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py`.
- The ChEMBL family uses one real shared normalization layer rather than per-transformer ad hoc cleanup. The policy seams are centralized in
  `src/bioetl/domain/normalization/profiles/_chembl_policy_registry.py`,
  `src/bioetl/domain/normalization/profiles/_chembl_policy_registry_data.py`,
  `configs/enums/chembl.yaml`,
  `configs/vocab/chembl_controlled.yaml`,
  `configs/vocab/chembl_ontology.yaml`,
  `configs/vocab/chembl_reference_identifiers.yaml`,
  and `src/bioetl/domain/normalization/profiles/chembl_json_ordering_policy.py`.
- The current generated normalization matrix reports `100.00%` explicit shipped entity-record profile coverage for the repo-wide inventory (`857 / 857`) and `100.00%` for the meta/set-like/non-meta semantic invariants:
  `docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md`.
- The ChEMBL Bronze observed-value inventory currently covers all 14 pipelines and materializes `222` field rows from tracked fixtures:
  `docs/reports/generated/chembl_observed_value_inventory.md`,
  `configs/base/bronze_fixture_manifest.yaml`.
- Contract registry, fixture parity, enum/DQ sync, ontology companion policy, derived vocabulary policy, and hash determinism are enforced by active tests, not only by documentation:
  `tests/integration/config/test_chembl_contract_registry_coverage.py`,
  `tests/integration/config/test_chembl_registry_fixture_contract_parity.py`,
  `tests/integration/config/test_chembl_enum_parity.py`,
  `tests/integration/config/test_chembl_dq_catalog_sync.py`,
  `tests/contract/test_chembl_ontology_bundle_policy.py`,
  `tests/contract/test_chembl_derived_vocabulary_contracts.py`,
  `tests/unit/application/core/test_chembl_normalization_hash_golden.py`,
  `tests/unit/domain/hash_policy/test_chembl_high_risk_hash_golden.py`,
  `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py`.
- Recent ChEMBL residual issues are reflected in current source-of-truth artifacts:
  molecule provider-code governance (`availability_type`, `chirality`), optional assay-parameter ontology companion bundle, nested target xref source DQ, expanded weak-coverage fixtures, and synced provider docs are all present in current code/config/docs:
  `src/bioetl/domain/normalization/profiles/chembl_molecule.py`,
  `src/bioetl/domain/schemas/chembl/assay_parameters.py`,
  `configs/entities/chembl/target.yaml`,
  `configs/entities/chembl/target_component.yaml`,
  `tests/fixtures/normalization/chembl_observed_values.yaml`,
  `docs/04-reference/providers/chembl/*.md`.

### Conclusions

- Determinism: pass
- Reproducibility/content-hash readiness: pass
- Silver/Gold contract safety: pass
- Cross-pipeline enum/vocabulary alignment: pass
- Shared-vs-entity-specific normalization placement: pass
- Confirmed normalization defects on current `main`: none

### Audit limitation

- The audit is repo-bounded, not live-API-complete. Confidence is highest for policy-bearing fields already covered by shipped registries, matrix rows, and tracked fixtures. Confidence is lower for raw-provider diversity in pipelines with shallow Bronze fixture field coverage such as `chembl_publication_similarity`, `chembl_compound_record`, `chembl_tissue`, and `chembl_target`. This is a coverage-depth limitation, not a confirmed normalization defect. Sources:
  `docs/reports/generated/chembl_observed_value_inventory.md`,
  `tests/fixtures/bronze/chembl/**`,
  `tests/fixtures/normalization/chembl_observed_values.yaml`.

## Scope Inventory

| Pipeline | Config | Transformer | Domain schema | Silver schema | Gold contract | Fixture coverage | Included? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `chembl_activity` | `configs/entities/chembl/activity.yaml` | `ActivityTransformer` | `ActivitySchema` | `CHEMBL_ACTIVITY_SCHEMA` | `chembl_activity_v1.0.json` | tracked CI + edge | yes | bioactivity primary surface |
| `chembl_assay` | `configs/entities/chembl/assay.yaml` | `AssayTransformer` | `AssaySchema` | `CHEMBL_ASSAY_SCHEMA` | `chembl_assay_v1.0.json` | tracked CI | yes | assay/context surface |
| `chembl_assay_parameters` | `configs/entities/chembl/assay_parameters.yaml` | `AssayParametersTransformer` | `AssayParametersSchema` | `CHEMBL_ASSAY_PARAMETERS_SCHEMA` | `chembl_assay_parameters_v1.0.json` | tracked CI | yes | now includes optional UO/QUDT companion bundle |
| `chembl_molecule` | `configs/entities/chembl/molecule.yaml` | `MoleculeTransformer` | `MoleculeSchema` | `CHEMBL_MOLECULE_SCHEMA` | `chembl_molecule_v1.0.json` | tracked CI + edge | yes | reviewed provider-code surfaces now governed |
| `chembl_target` | `configs/entities/chembl/target.yaml` | `TargetTransformer` | `TargetSchema` | `CHEMBL_TARGET_SCHEMA` | `chembl_target_v1.0.json` | tracked CI | yes | nested xref source vocabulary now runtime-governed |
| `chembl_target_component` | `configs/entities/chembl/target_component.yaml` | `TargetComponentTransformer` | `TargetComponentSchema` | `CHEMBL_TARGET_COMPONENT_SCHEMA` | `chembl_target_component_v1.0.json` | tracked CI | yes | nested xref source vocabulary now runtime-governed |
| `chembl_cell_line` | `configs/entities/chembl/cell_line.yaml` | `CellLineTransformer` | `CellLineSchema` | `CHEMBL_CELL_LINE_SCHEMA` | `chembl_cell_line_v1.0.json` | tracked CI | yes | ontology-heavy reference surface |
| `chembl_tissue` | `configs/entities/chembl/tissue.yaml` | `TissueTransformer` | `TissueSchema` | `CHEMBL_TISSUE_SCHEMA` | `chembl_tissue_v1.0.json` | tracked CI | yes | ontology-heavy reference surface |
| `chembl_compound_record` | `configs/entities/chembl/compound_record.yaml` | `CompoundRecordTransformer` | `CompoundRecordSchema` | `CHEMBL_COMPOUND_RECORD_SCHEMA` | `chembl_compound_record_v1.0.json` | tracked CI | yes | publication/molecule linkage surface |
| `chembl_protein_class` | `configs/entities/chembl/protein_class.yaml` | `ProteinClassTransformer` | `ProteinClassificationSchema` | `CHEMBL_PROTEIN_CLASS_SCHEMA` | `chembl_protein_class_v1.0.json` | tracked CI + edge | yes | hierarchy/reference surface |
| `chembl_subcellular_fraction` | `configs/entities/chembl/subcellular_fraction.yaml` | `SubcellularFractionTransformer` | `SubcellularFractionSchema` | `CHEMBL_SUBCELLULAR_FRACTION_SCHEMA` | `chembl_subcellular_fraction_v1.0.json` | tracked CI | yes | derived from `chembl_assay` |
| `chembl_publication` | `configs/entities/chembl/publication.yaml` | `PublicationTransformer` | `ChemblPublicationSchema` | `CHEMBL_PUBLICATION_SCHEMA` | `chembl_publication_v1.0.json` | tracked CI | yes | publication taxonomy surface |
| `chembl_publication_term` | `configs/entities/chembl/publication_term.yaml` | `PublicationTermTransformer` | `PublicationTermSchema` | `CHEMBL_DOCUMENT_TERM_SCHEMA` | `chembl_publication_term_v1.0.json` | tracked CI | yes | derived/publication-term vocabulary |
| `chembl_publication_similarity` | `configs/entities/chembl/publication_similarity.yaml` | `PublicationSimilarityTransformer` | `PublicationSimilaritySchema` | `CHEMBL_DOCUMENT_SIMILARITY_SCHEMA` | `chembl_publication_similarity_v1.0.json` | tracked CI + edge | yes | weakest raw-field coverage among active ChEMBL fixtures |

Primary artifact for the table:
`src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py`.
Fixture and contract parity are also enforced in
`tests/integration/config/test_chembl_registry_fixture_contract_parity.py`
and `tests/integration/config/test_chembl_contract_registry_coverage.py`.

## Fact Base

| Area | Pipeline | Artifact | Fact | Conclusion |
| --- | --- | --- | --- | --- |
| Registry completeness | all | `_registry_manifest_chembl.py` | exactly 14 active ChEMBL pipeline configs are registered with transformer, Pandera Silver schema, Arrow Silver schema, and Gold schema classes | audit scope is structurally complete |
| Shared normalization layer | all | `_chembl_policy_registry.py`, `_chembl_policy_registry_data.py`, `normalization_policy_init.py` | domain policy surfaces are injected from config-backed immutable payloads; filesystem parsing stays in composition/infrastructure bootstrap | domain normalization stays pure |
| Domain import boundary | all ChEMBL profiles | `src/bioetl/domain/normalization/profiles/chembl*.py`, `src/bioetl/domain/normalization/profiles/_chembl*.py` | no imports from `bioetl.infrastructure`, `bioetl.application`, `bioetl.composition`, or `bioetl.interfaces` were found in ChEMBL normalization profiles | no architecture boundary violation in the normalization layer |
| Domain I/O boundary | all ChEMBL profiles | same profile set | no `open()`, HTTP client calls, YAML parsing, or file reads were found in ChEMBL normalization profiles | no domain I/O leakage |
| Transformer placement | all | `src/bioetl/application/pipelines/chembl/base_chembl_transformer.py` | transformers extract/massage source aliases, but normalization and identity are delegated through the shared application normalization path rather than embedding filesystem-driven vocab logic | common semantics are not transformer-fragmented |
| Contract registry completeness | all Gold-enabled ChEMBL entities | `configs/base/contract_registry.yaml`, `test_chembl_contract_registry_coverage.py` | every active Gold-enabled ChEMBL entity has an active contract registry entry with normalization profile hash and published artifact path | Gold contract governance is complete |
| Bronze evidence completeness | all | `docs/reports/generated/chembl_observed_value_inventory.md` | all 14 pipelines have tracked Bronze fixtures; inventory currently has `14` fixtures and `222` field rows | family-wide offline evidence exists |
| Coverage depth asymmetry | publication_similarity / compound_record / tissue / target | `chembl_observed_value_inventory.md` | tracked raw field counts are shallow: `4`, `6`, `6`, and `8` rows respectively | confidence on raw-provider diversity is lower for these pipelines |
| DTO anchoring | all API-backed ChEMBL entities in scope | `src/bioetl/infrastructure/adapters/chembl/constants.py` | `CHEMBL_DTO_MODELS` includes `activity`, `assay`, `molecule`, `target`, `target_component`, `publication`, `cell_line`, `protein_class`, `tissue`, `compound_record`, and `publication_similarity` | prior adapter-schema anchoring asymmetry is closed |
| Molecule provider-code governance | molecule | matrix rows for `availability_type`, `chirality`; `chembl_molecule.py`; `configs/entities/chembl/molecule.yaml` | both fields are now explicit enum-like surfaces with `strict_enum` matrix classification and `enum:error` DQ coverage | prior reviewed-code gap is closed |
| Assay parameter ontology companions | assay_parameters | matrix rows for `uo_units`, `qudt_units`, mapping statuses; `assay_parameters.py`; `assay_parameters.yaml` | optional UO/QUDT companion fields are part of domain schema, Silver schema, Gold contract, normalization profile, and DQ rules | prior unit-ontology bundle gap is closed |
| Nested xref vocabulary enforcement | target / target_component | matrix rows for `cross_references`, `target_component_xrefs`; `target.yaml`; `target_component.yaml`; `_dq_rule_evaluators.py` | both structured fields have `custom:error` DQ coverage against `configs/vocab/chembl_reference_sources.yaml` | prior nested-xref DQ gap is closed |
| Derived vocabulary governance | publication_term / subcellular_fraction / assay_parameters | `tests/contract/test_chembl_derived_vocabulary_contracts.py`, `tests/architecture/test_chembl_derived_vocabulary_policy.py` | derived pipelines and derived controlled surfaces have explicit contract/policy guards | no confirmed derived-vocabulary drift |
| Hash determinism | activity / molecule / target / target_component / publication | `tests/unit/application/core/test_chembl_normalization_hash_golden.py`, `tests/unit/domain/hash_policy/test_chembl_high_risk_hash_golden.py` | high-risk structured and semantic fields remain hash-stable under the current normalization rules | no confirmed content-hash inconsistency |
| Composite usage | activity / assay / molecule / publication / target families | `configs/composites/activity.yaml`, `assay.yaml`, `molecule.yaml`, `publication.yaml`, `target.yaml` | normalized ChEMBL Silver outputs are consumed downstream by composite pipelines as join/enrichment sources | ChEMBL normalization is materially downstream-relevant, not isolated |

## Unified Enum Inventory

The complete field-level inventory is the generated matrix:
`docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md`.
The table below lists the materially distinct enum-like families relevant for architectural conclusions.

| Pipeline | Field | Layer | Observed values/examples | Cardinality | Classification | Current normalization | Proposed normalization | Priority |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| `chembl_activity` | `standard_relation` | Bronze/Silver/Gold | `=`, `<`, `<=`, `>`, `>=`, `~` from `chembl_observed_values.yaml` | 6 | strict operator enum | shared operator normalization + DQ parity | keep | none |
| `chembl_activity` | `standard_units` | Bronze/Silver/Gold | `nM`, `µM`, `mM`, `%`, `ug.mL-1` from `chembl_observed_values.yaml` | controlled set | unit-like controlled terms | shared unit alias and catalog policy | keep | none |
| `chembl_activity` | `bao_endpoint`, `bao_format`, `uo_units`, `qudt_units` | Bronze/Silver/Gold | BAO/UO/QUDT ids from fixtures and observed-value policy | namespace-backed | ontology-backed identifiers | canonical ontology/reference normalization with companion metadata | keep | none |
| `chembl_assay` | `assay_type` | Bronze/Silver/Gold | `B`, `F`, `A`, `T`, `P`, `U` | 6 | strict enum | uppercase enum normalization + `enum:error` DQ | keep | none |
| `chembl_assay` | `assay_test_type`, `assay_category`, `relationship_type` | Bronze/Silver/Gold | observed families from `chembl_observed_values.yaml` | provider-bounded | controlled vocabulary / strict enum | registry-backed normalization | keep | none |
| `chembl_assay_parameters` | `standard_type`, `type`, `type_raw` | Bronze/Silver/Gold | `CONC`, `PH`, `TEMP`, `TIME`, `% Inhibition`; raw `conc`, `ph` | provider-bounded | controlled vocabulary with raw sidecar | raw+canonical dual-field strategy | keep | none |
| `chembl_assay_parameters` | `standard_relation`, `standard_units` | Bronze/Silver/Gold | same operator/unit families as activity | bounded | strict operator / unit-like controlled terms | shared bioactivity normalization seam | keep | none |
| `chembl_assay_parameters` | `uo_units`, `qudt_units`, `*_mapping_status` | Silver/Gold | optional ontology unit companions | namespace + status sets | ontology-backed identifiers / strict enum metadata | optional companion-bundle normalization | keep | none |
| `chembl_molecule` | `availability_type` | Bronze/Silver/Gold | `-1`, `2`; policy values `-2..2` | 5 | strict enum-like provider code | canonical numeric enum universe + `enum:error` DQ | keep | none |
| `chembl_molecule` | `chirality` | Bronze/Silver/Gold | `1`, `2`; policy values `-1,0,1,2` | 4 | strict enum-like provider code | canonical numeric enum universe + `enum:error` DQ | keep | none |
| `chembl_molecule` | `molecule_type`, `structure_type` | Bronze/Silver/Gold | `Small molecule`, `Antibody`, `Protein`, `Unknown`; `MOL`, `SEQ`, `BOTH`, `NONE` | provider-bounded | controlled vocabulary / strict enum | shared molecule registries | keep | none |
| `chembl_molecule` | `max_phase` | Bronze/Silver/Gold | `-1`, `0`, `0.5`, `1`, `2`, `3`, `4` | 7 | quasi-enum numeric | canonical numeric quasi-enum normalization | keep | none |
| `chembl_molecule` | `ro3_pass`, therapeutic/review flags | Bronze/Silver/Gold | `Y/N`, `0/1`, nullable flag codes | low-cardinality | boolean-like / flag-like | shared bool/flag families from policy registry | keep | none |
| `chembl_target` | `target_type` | Bronze/Silver/Gold | `SINGLE PROTEIN`, `PROTEIN FAMILY`, `PROTEIN COMPLEX`, `CELL-LINE`, `UNKNOWN` | provider-bounded | controlled vocabulary | registry-backed normalization + DQ | keep | none |
| `chembl_target` | `organism_class` | Silver/Gold | `unicellular`, `multicellular` | 2 in repo evidence | derived vocabulary | derived canonicalization from organism/taxonomy seam | keep | none |
| `chembl_target` | `cross_references` | Bronze/Silver/Gold | JSON payload with nested `xref_src_db` values | structured | structured JSON + nested controlled vocabulary | strict JSON canonicalization + custom source-vocab DQ | keep | none |
| `chembl_target_component` | `component_type` | Bronze/Silver/Gold | `PROTEIN`, `DNA`, `RNA` | 3 | strict enum | explicit enum normalization + DQ | keep | none |
| `chembl_target_component` | `target_component_xrefs` | Bronze/Silver/Gold | JSON payload with nested `xref_src_db` values | structured | structured JSON + nested controlled vocabulary | strict JSON canonicalization + custom source-vocab DQ | keep | none |
| `chembl_cell_line` | `cellosaurus_id`, `clo_id`, `efo_id`, `taxonomy_id` | Bronze/Silver/Gold | namespace ids in fixtures and observed policy | namespace-backed | ontology/reference identifiers | shared ontology/reference canonicalization | keep | none |
| `chembl_tissue` | `bto_id`, `caloha_id`, `efo_id`, `uberon_id` | Bronze/Silver/Gold | namespace ids in fixtures and observed policy | namespace-backed | ontology/reference identifiers | shared ontology/reference canonicalization | keep | none |
| `chembl_publication` | `publication_type_raw`, `publication_type`, `publication_type_unified`, `publication_subclass`, `publication_class` | Bronze/Silver/Gold | source `PUBLICATION/PATENT/...`; normalized `journal-article/patent/...` | provider-bounded | controlled vocabulary + derived vocabulary | explicit dual-field taxonomy mapping | keep | none |
| `chembl_publication_term` | `term_type` | Bronze/Silver/Gold | `MESH_HEADING`, `MESH_QUALIFIER`, `KEYWORD` | 3 | strict enum | strict enum normalization + DQ parity | keep | none |
| `chembl_publication_similarity` | `pubmed_id1`, `pubmed_id2` | Bronze/Silver/Gold | `"14695814"`, `"12345678"` etc. | open identifier family | ontology/reference identifier | shared PMID canonicalization | keep | none |
| `chembl_subcellular_fraction` | `subcellular_fraction_raw`, `subcellular_fraction` | Bronze/Silver/Gold | assay-derived labels such as `Membrane`, `Nucleus`, `Cytoplasm` | provider-expandable | derived vocabulary with raw sidecar | controlled extraction + canonical derived contract | keep | none |

## Reuse / Drift Matrix

| Rule / Field Family | Pipelines using it | Implemented where | Is behavior identical? | Drift risk | Recommendation |
| --- | --- | --- | --- | --- | --- |
| ChEMBL enum catalog | `activity`, `assay`, `assay_parameters`, `molecule`, `publication`, `publication_term`, `target`, `target_component` | `configs/enums/chembl.yaml`, `_chembl_enum_catalog.py`, profile modules, parity tests | yes | low | keep shared seam |
| Controlled vocabulary registry | `activity`, `assay`, `assay_parameters`, `molecule`, `publication`, `subcellular_fraction`, `target` | `configs/vocab/chembl_controlled.yaml`, `_chembl_policy_registry_data.py`, profiles | yes | low | keep |
| Reference identifier canonicalization | cross-family | `configs/vocab/chembl_reference_identifiers.yaml`, `_chembl_reference_identifier_rules.py` | yes | low | keep |
| Ontology companion bundles | `activity`, `assay`, `assay_parameters`, `cell_line`, `tissue` | `configs/vocab/chembl_ontology.yaml`, `_chembl_policy_registry_data.py`, ontology companion normalizers | yes | low | keep |
| Bool/flag governance | `activity`, `molecule`, `protein_class` and related surfaces | `_chembl_policy_registry_data.py`, `configs/enums/chembl.yaml` | yes | low | keep |
| Canonical JSON/hash ordering | `activity`, `publication`, `target`, `target_component`, selected set-like fields elsewhere | `chembl_json_ordering_policy.py`, hash golden tests | yes | low | keep |
| Raw-plus-canonical dual-field strategy | `publication`, `assay_parameters`, `subcellular_fraction` | profile special rules + entity configs + contracts | yes | low | keep |
| Nested xref source governance | `target`, `target_component` | entity DQ config + `_dq_rule_evaluators.py` + matrix custom coverage | yes | low | keep |
| Derived vocabulary contracts | `publication_term`, `subcellular_fraction`, `assay_parameters` | derived vocabulary contract tests + configs | yes | low | keep |

Conclusion from the matrix: no confirmed cross-pipeline normalization drift remains in the currently governed high-risk ChEMBL field families.

## Gap Analysis

### Missing normalization

- No confirmed missing normalization surface was found on current `main` for shipped ChEMBL profiles.

### Weak canonicalization

- No confirmed weak canonicalization defect was found in currently governed enum/operator/unit/ontology/reference/JSON seams.

### Missing enum externalization

- No confirmed missing enum externalization defect was found for currently reviewed ChEMBL enum-like surfaces. Current source of truth is `configs/enums/chembl.yaml` plus field-specific controlled/ontology registries.

### Schema / contract mismatch

- No confirmed active mismatch was found between current ChEMBL domain schema, Silver schema, Gold contract, and registry artifacts. This is enforced by
  `tests/integration/config/test_chembl_contract_registry_coverage.py`,
  `tests/contract/test_gold_schema_snapshot_registry.py`,
  `tests/architecture/test_gold_schema_contracts.py`.

### Hashing inconsistency

- No confirmed content-hash inconsistency was found in the currently shipped ChEMBL normalization rules. Relevant baselines:
  `docs/00-project/RULES.md`,
  `docs/02-architecture/decisions/ADR-014-deterministic-writes.md`,
  `docs/02-architecture/decisions/ADR-038-enum-externalization.md`,
  hash golden tests.

### DQ mismatch

- No confirmed DQ-vs-normalization mismatch was found for current reviewed ChEMBL policy-bearing surfaces. Newly governed target nested xref JSON fields and molecule provider-code fields now have explicit DQ coverage.

### Ontology-handling mismatch

- No confirmed ontology companion or identifier mismatch was found across `activity`, `assay`, `assay_parameters`, `cell_line`, and `tissue`.

### JSON canonicalization mismatch

- No confirmed JSON canonicalization drift was found for current ChEMBL structured fields under hash-sensitive policy tests and matrix invariants.

### Architectural placement issue

- No confirmed architecture placement defect was found in ChEMBL normalization. Domain normalization remains free of infrastructure/application/composition imports and free of direct I/O.

### Cross-pipeline normalization drift

- No confirmed residual cross-pipeline drift remains after the recent ChEMBL residual issue wave.

### Structural confidence gap

- Repo-observed raw evidence is still shallower for some reference-like pipelines. This affects confidence depth, not correctness proof. The main examples are `chembl_publication_similarity`, `chembl_compound_record`, `chembl_tissue`, and `chembl_target` in
  `docs/reports/generated/chembl_observed_value_inventory.md`.

## Proposed Expansion / Tightening

No mandatory normalization change is justified by the current repo evidence.

Optional P2-only improvements:

| Extension | Layer | Target file(s) | Expected input/output | Backward compatibility | `content_hash` impact | Silver/Gold impact | DQ impact | Composite/derived impact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Expand tracked edge Bronze fixtures for shallow ChEMBL entities | tests/fixtures | `tests/fixtures/bronze/chembl/**`, `configs/base/bronze_fixture_manifest.yaml` | more raw-provider diversity evidence only | additive | none | none | confidence only | confidence only |
| Extend offline observed-value inventory rows | scripts/docs/tests | `scripts/engineering/qa/report_chembl_observed_value_inventory.py`, `docs/reports/generated/chembl_observed_value_inventory.*` | broader observed set materialization | additive | none | none | confidence only | confidence only |
| Add additional hash golden cases when new structured ChEMBL fields appear | tests | `tests/unit/application/core/test_chembl_normalization_hash_golden.py`, `tests/unit/domain/hash_policy/test_chembl_high_risk_hash_golden.py` | stronger regression coverage | additive | none until semantics change | confidence only | confidence only | confidence only |

Dual-field strategy remains appropriate only where it already exists and is semantically justified:

- `chembl_publication`: `publication_type_raw` + normalized taxonomy surfaces
- `chembl_assay_parameters`: `type_raw` + normalized `type` / `standard_type`
- `chembl_subcellular_fraction`: `subcellular_fraction_raw` + canonical derived field

No new dual-field requirement is justified by current evidence.

## P0-P2 Plan

### P0

- No confirmed P0 blockers.

### P1

- No confirmed P1 normalization remediation tasks.

### P2

1. Keep ChEMBL observed-value fixture depth growing as new provider branches are encountered.
2. Keep matrix, contract, and observed-value inventory artifacts fresh after any future ChEMBL normalization change.
3. Add more high-risk hash golden cases only when new structured or semantic-sensitive ChEMBL fields are introduced.

## Validation Performed

- Architecture boundary probes on ChEMBL normalization profiles:
  - no forbidden layer imports found
  - no direct I/O/parsing/network calls found
- Targeted audit suites:
  - `uv run pytest -q tests/integration/config/test_chembl_enum_parity.py tests/integration/config/test_chembl_dq_catalog_sync.py tests/integration/config/test_chembl_observed_value_fixtures.py tests/integration/config/test_chembl_bronze_observed_value_inventory_snapshot.py tests/integration/normalization/test_chembl_edge_observed_values.py tests/contract/test_chembl_enum_normalization_policy.py tests/contract/test_chembl_ontology_bundle_policy.py tests/contract/test_chembl_derived_vocabulary_contracts.py tests/architecture/test_chembl_derived_vocabulary_policy.py`
  - `uv run pytest -q tests/unit/application/core/test_chembl_normalization_hash_golden.py tests/unit/domain/hash_policy/test_chembl_high_risk_hash_golden.py tests/integration/test_cross_pipeline_normalization.py tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py -k chembl`
- Evidence anchors reviewed:
  - `docs/00-project/RULES.md`
  - `docs/02-architecture/decisions/ADR-014-deterministic-writes.md`
  - `docs/02-architecture/decisions/ADR-018-gold-strict-validation.md`
  - `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`
  - `docs/02-architecture/decisions/ADR-035-json-field-typing-policy.md`
  - `docs/02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md`
  - `docs/02-architecture/decisions/ADR-038-enum-externalization.md`

## Verdict

Current `main` is ready for strict enum-aware unified ChEMBL normalization within the repo-bounded evidence universe.

- The common normalization registry is real and active.
- The high-risk residual defects previously identified for ChEMBL are now closed in current source artifacts.
- No new cross-pipeline normalization defect was confirmed.
- Remaining work is evidence-depth maintenance, not semantic remediation.
