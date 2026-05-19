______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: Architecture / Domain
Reviewers:

- BioETL Team
  Last verified: '2026-04-22'

______________________________________________________________________

# Normalization Plan P0-P6

## Purpose

This document is the canonical engineering plan for deterministic normalization
across:

- `RunManifest`
- `RunLedger`
- canonical execution identity used by manifest and checkpoint persistence
- degraded runtime-anchor compatibility helpers used only for legacy resume paths
- record-level normalization and `content_hash`
- shipped normalization profiles and generated field-matrix artifacts
- composite join-key normalization policies and adapters

It is the source of requirements for `P0`-`P6` and the matching test program
`T1`-`T3`.

## Scope

The plan covers:

- control-plane normalization in the domain layer
- canonical serialization before hashing or persistence
- fingerprint and content-hash determinism
- field-rule and profile contracts
- generated normalization matrix artifacts from code

The plan does not cover:

- retroactive rewrite of historical manifests / ledgers
- silent backward-incompatible hash migrations
- ad hoc normalization outside sanctioned seams

## Determinism Invariants

These rules are mandatory for all phases.

1. Normalize before hashing and before persistence.
1. Canonical JSON is the only byte representation allowed before hashing.
1. Canonical JSON uses `sort_keys=True` and `separators=(",", ":")`.
1. Control-plane datetimes normalize to UTC ISO-8601 with trailing `Z`.
1. SHA-256 fingerprints and content hashes serialize as lowercase hex strings.
1. UUID values normalize to canonical string form.
1. Domain normalization code remains pure: no I/O, no pandas, no HTTP, no hidden clock access.
1. Order-sensitive lists preserve order by default.
1. Only fields explicitly marked `set_like` are permutation-invariant for hashing.
1. Technical meta fields do not participate in `content_hash`.

## 2026-04-21 Data Normalization Audit Closure

Issues `#3011`-`#3025` turn the normalization audit into explicit code
guardrails. The active implementation policy is:

- `RecordNormalizationProcessor.compute_content_hash()` always hashes with
  `exclude_none=True` and passes profile `set_like_fields` to the domain hash
  identity seam.
- DOI, PMID, and PMC identifiers are normalized through domain identifier
  helpers from every shipped publication profile.
- ChEMBL strict enum fields are centralized in `configs/enums/chembl.yaml`,
  mirrored by `domain/schemas/constants.py`, applied by normalization profiles,
  and guarded by Pandera `isin`/pattern checks where schemas expose the field.
- Shared profile rule families cover boolean-like values, binary flags,
  comparison operators, units, pseudo-null collapse, canonical JSON strings,
  and set-like JSON/list hash behavior.
- ChEMBL ontology identifiers are normalized in profiles for BAO, BTO, CALOHA,
  CLO, EFO, UBERON, UO, and related prefixed IDs instead of transformer-local
  one-offs.
- Composite join keys must have an explicit policy in
  `JOIN_KEY_NORMALIZATION_POLICIES`; configuration coverage is enforced by unit
  tests over `configs/composites/*.yaml`.

## 2026-04-23 Enum, Publication, and Observed-Value Governance Closure

Issues `#3031`-`#3040` extend the normalization audit closure from
`chembl_activity` and generic profile semantics into family-wide vocabulary,
publication, and evidence governance.

The active implementation policy is:

- ChEMBL enum SSOT remains `configs/enums/chembl.yaml`; domain constants,
  Pandera schemas, normalization profiles, DQ configs, and extraction/filter
  subsets are checked by `test_constants_yaml.py` and
  `test_chembl_enum_parity.py`.
- Finite-vocabulary governance is intentionally split into four categories:
  strict externalized enums use YAML-backed SSOT and mechanical parity checks;
  controlled vocabularies use shared canonicalizers without claiming exhaustive
  closed sets; derived taxonomies preserve raw provider values and materialize
  normalized classification fields separately; free-text fields keep text/title
  semantics and must not silently acquire enum behavior.
- `chembl_assay_parameters` owns parameter canonicalization in its shipped
  profile for `type`, `relation`, `units`, `standard_type`,
  `standard_relation`, and `standard_units`; the transformer maps provider
  payloads without owning business canonicalization for those fields.
- ChEMBL assay structured fields such as `assay_classifications`,
  `assay_parameters`, and `variant_sequence_json` use explicit canonical JSON
  profile semantics; `bao_format` and `bao_label` retain code/label semantics
  instead of collapsing ontology provenance.
- Publication pipelines preserve raw provider publication-type values and derive
  `publication_type_unified`, `publication_subclass`, and `publication_class`
  through the unified taxonomy in
  `configs/enums/publication_type_classification.csv`.
- ChEMBL observed-value governance is offline and deterministic:
  `tests/fixtures/normalization/chembl_observed_values.yaml` contains
  representative observed values, and
  `test_chembl_observed_value_fixtures.py` checks them against SSOT or approved
  derived vocabulary surfaces without live ChEMBL calls.
- The generated normalization matrix under
  `docs/reports/generated/pipeline_normalization_field_matrix/` is part of the
  release evidence bundle and must be regenerated after profile, schema, DQ, or
  publication-classification changes.

Rollout notes:

- Raw publication-type behavior is DQ-affecting: downstream consumers should
  read `publication_type_unified`, `publication_subclass`, and
  `publication_class` for canonical cross-provider semantics.
- Changes to normalized field casing, units, operators, or derived publication
  classification can affect `content_hash`; run dry-run/shadow comparison
  before rebuilding persisted Silver/Gold outputs.
- `#3040` documentation closure is complete only when ADR-038, this plan,
  generated matrix artifacts, and `CHANGELOG.md` describe the same policy
  state.

## 2026-05-02 Non-ChEMBL Governance Publication Closure

Issues `#3498`, `#3500`, `#3503`, `#3504`, `#3505`, `#3506`, and `#3507` close the
remaining documentation gap between current non-ChEMBL normalization code and
the published reference surface.

The active publication rule is:

- the generated matrix and reviewed fixtures remain the evidence source for raw
  provider values, identifier families, structured payload sidecars, and
  composite impact
- published docs under `docs/04-reference/normalization/` summarize the current
  governance boundary without redefining code-owned behavior
- semantic-sensitive structured payload sidecars remain additive compatibility
  fields during the dual-read window; canonical JSON fields keep the persisted
  contract while `*_raw_json` and `*_canonical_json` preserve raw-provider and
  semantic-ready evidence for future migrations
- raw publication provider types and ontology/reference identifiers must remain
  explicitly documented as non-enum surfaces
- composite docs must describe upstream-inherited non-key semantics rather than
  implying a second composite-local normalization pass

## 2026-04-28 ChEMBL Family Semantic-Alignment Closure

Issues `#3259`-`#3268` tighten family-level semantics for shipped `chembl_*`
profiles without changing the profile-driven architecture.

The active implementation policy is:

- `chembl_activity.standard_units` now uses the same canonical unit seam as
  `units` and `chembl_assay_parameters.standard_units`; unit-like fields must
  not diverge between intra-pipeline and cross-pipeline normalization paths.
- `chembl_molecule` flag-like provider-code fields are explicitly split from
  plain integer families: reviewed tri-state codes such as
  `first_in_class`, `inorganic_flag`, `natural_product`, and `prodrug`
  normalize through a reviewed flag-code seam instead of generic integer
  coercion.
- Unknown-preserving controlled vocabularies may retain raw provider lexemes in
  explicit sidecars such as `assay_subcellular_fraction_raw`, `type_raw`, and
  `subcellular_fraction_raw`; canonical analytical fields remain separately
  normalized.
- Publication compatibility identifiers and metadata sidecars such as
  `publication_type_raw`, `publication_doi`, `publication_pmid`,
  `publication_pmc_id`, and `oa_status` must remain domain-schema visible so
  normalization, schema, and matrix evidence describe the same contract.
- Set-like JSON arrays with element-wise controlled-vocabulary semantics, such
  as `chembl_target.component_types` and
  `chembl_target.component_relationships`, must canonicalize through explicit
  JSON-string normalizer families and remain permutation-invariant only when
  the profile marks them `set_like`.
- Cross-field ontology bundle expectations belong in published config and
  generated governance evidence: when a mapped BAO/UO/QUDT identifier exists,
  companion status and derived ontology metadata must remain consistent with
  the profile bundle semantics.

## Canonical Hash and Serialization Rules

### Canonical JSON

Canonical serialization is the shared lexical contract before hashing.

- sort keys lexically
- use compact separators `(",", ":")`
- do not allow unordered mapping traversal to affect bytes on disk

Current main seams:

- [json.py](../../src/bioetl/domain/normalization/json.py)
- [serialization.py](../../src/bioetl/domain/serialization.py)

### Datetime

Control-plane timestamps must normalize to UTC ISO-8601 `Z` form.

Example:

- input: `2026-04-08T12:15:30+03:00`
- canonical: `2026-04-08T09:15:30Z`

Current main seam:

- [control_plane.py](../../src/bioetl/domain/normalization/control_plane.py)

### SHA-256

Two distinct hash families exist and must not be conflated.

- `execution_fingerprint`: lowercase 64-char hex
- `content_hash`: lowercase 64-char hex

Execution-identity and degraded runtime-anchor fields such as
`effective_config_hash` are also hash-like and must compare in lowercase form;
validation strictness is part of `P2`.

### UUID

UUID-like values normalize through canonical string conversion.

- lowercase text
- standard hyphenated string form
- blank optional UUIDs collapse to `None`

## Current Main Seams

| Concern                            | Current seam                                                                                                          | Current behavior on `main`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Control-plane domain normalization | [control_plane.py](../../src/bioetl/domain/normalization/control_plane.py)                                            | Pure helpers for manifest specs, ledger payloads, UUIDs, datetimes, set-like collections, canonical execution identity, and degraded runtime anchors                                                                                                                                                                                                                                                                                                                                                                                    |
| Hash-identity domain normalization | [hash_identity.py](../../src/bioetl/domain/normalization/hash_identity.py)                                            | Pure helpers for `content_hash` and content-aware dedup identity, including the current date-only datetime contract                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Manifest fingerprint               | [run_manifest_service.py](../../src/bioetl/application/services/control_plane/run_manifest_service.py)                | Calls `normalize_run_manifest_spec()`, then canonical JSON, then SHA-256                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Ledger persist payload             | [run_ledger_service.py](../../src/bioetl/application/services/control_plane/run_ledger_service.py)                    | Calls `normalize_run_ledger_payload()` before append                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Record-level normalization         | [record_normalization_processor.py](../../src/bioetl/application/core/record_normalization_processor.py)              | Uses `NormalizationProfile` when available, otherwise falls back to legacy heuristics                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Profile framework                  | [base.py](../../src/bioetl/domain/normalization/profiles/base.py)                                                     | Defines `FieldRule` and `NormalizationProfile` with `include_in_hash` and `set_like`                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Shipped profile registry           | [registry.py](../../src/bioetl/domain/normalization/profiles/registry.py)                                             | Registers shipped profiles for `chembl.activity`, `chembl.assay`, `chembl.assay_parameters`, `chembl.cell_line`, `chembl.compound_record`, `chembl.molecule`, `chembl.protein_class`, `chembl.publication`, `chembl.publication_similarity`, `chembl.publication_term`, `chembl.subcellular_fraction`, `chembl.target`, `chembl.target_component`, `chembl.tissue`, `crossref.publication`, `openalex.publication`, `pubchem.compound`, `pubmed.publication`, `semanticscholar.publication`, `uniprot.idmapping`, and `uniprot.protein` |
| Join-key domain policies           | [join_keys.py](../../src/bioetl/domain/normalization/join_keys.py)                                                    | Pure scalar join-key policies for canonical trim/casing behavior                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Join-key application adapters      | [join_key_normalization.py](../../src/bioetl/application/composite/join_key_normalization.py)                         | Applies canonical join-key policies to composite runtime/config and DataFrame-oriented flows                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Matrix generation                  | [generate_pipeline_normalization_field_matrix.py](../../scripts/docs/generate_pipeline_normalization_field_matrix.py) | Deterministically emits multi-pipeline CSV and MD artifacts from schemas, profiles, fallback rules, and join-key seams                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Fallback inventory                 | [report_normalization_fallback_inventory.py](../../scripts/engineering/qa/report_normalization_fallback_inventory.py) | Reports `fallback_business` vs `fallback_technical_passthrough` debt from the published matrix for governance and ratchets                                                                                                                                                                                                                                                                                                                                                                                                              |

## Hash Boundaries

### Where `execution_fingerprint` is computed

Canonical manifest path:

- [run_manifest_service.py](../../src/bioetl/application/services/control_plane/run_manifest_service.py)

Current algorithm on `main`:

1. build primitive manifest payload
1. call `normalize_run_manifest_spec(...)`
1. call `serialize_json_canonical(...)`
1. compute `hashlib.sha256(...).hexdigest()`

Current payload scope includes:

- `schema_version`
- `run_type`
- `pipeline_name`
- `provider`
- `entity`
- `launch_context`
- `runtime_config`
- `resolved_config`
- normalized `code_provenance`
- normalized `source_refs`
- normalized `planned_artifacts`

Current payload scope excludes:

- `manifest_id`
- `created_at`
- `entry_id`
- `occurred_at`
- other persist-only fields

Important note:

- `main` also has a checkpoint-resident canonical execution-identity fallback used when a full persisted manifest fingerprint is unavailable.
- `main` also retains an explicitly degraded runtime-anchor helper for legacy resume compatibility when neither full nor checkpoint-canonical identity is available.
- Those two fallback surfaces must not be conflated.

### Where `content_hash` is computed

Canonical record path:

- [hash_identity.py](../../src/bioetl/domain/normalization/hash_identity.py)
- [record_normalization_processor.py](../../src/bioetl/application/core/record_normalization_processor.py)
- [hashing.py](../../src/bioetl/domain/transformations/hashing.py)
- [retention.py](../../src/bioetl/infrastructure/storage/support/retention.py)
- [validation_operations.py](../../src/bioetl/infrastructure/storage/silver/validation_operations.py)

Current algorithm on `main`:

1. normalize record through profile or fallback rules
1. resolve include/exclude policy
1. pass `set_like_fields` from the profile when present
1. normalize hash identity through the explicit domain seam in `hash_identity.py`
1. canonicalize record for hashing through the same hash-identity contract
1. compute `sha256(provider + canonical_json(normalized_record)).hexdigest()`

Hash-identity note:

- `content_hash` and content-aware dedup now share one explicit contract.
- This contract is intentionally distinct from control-plane datetime normalization.
- `datetime` currently collapses to `date().isoformat()` inside hash identity to preserve historical `content_hash` stability until a deliberate migration is approved.
- 2026-04 evaluation outcome: keep this split in place; any convergence toward
  UTC ISO-8601 `Z` datetime semantics must be treated as a separate
  breaking-change migration with explicit versioning and validation.

Fields that currently participate in `content_hash`:

- `profile.hash_included_fields` when a profile is active
- or version-policy `include_fields` override when configured
- otherwise the active fallback inclusion policy

Fields currently excluded from `content_hash`:

- profile fields with `include_in_hash=False`
- explicit `content_hash_exclude_fields`
- `entity_id`
- `content_hash`
- `_content_hashes_by_version`
- technical meta fields from `META_FIELDS`
- underscore-prefixed technical fields by the hash policy

## Field-Matrix Source of Truth

The field matrix must be generated from code, not from spreadsheets.

Current deterministic generator on `main`:

- [generate_pipeline_normalization_field_matrix.py](../../scripts/docs/generate_pipeline_normalization_field_matrix.py)

Current inputs:

- silver schema registry for shipped entity pipelines
- canonical profile registry in [registry.py](../../src/bioetl/domain/normalization/profiles/registry.py)
- canonical fallback field families from [normalization_fallbacks.py](../../src/bioetl/application/core/normalization_fallbacks.py)
- composite join-key policy seams from [join_keys.py](../../src/bioetl/domain/normalization/join_keys.py) and [join_key_normalization.py](../../src/bioetl/application/composite/join_key_normalization.py)

Current deterministic outputs:

- CSV: required
- MD: shipped
- DOCX/PDF: optional best-effort exports

The generated artifact family is multi-pipeline and must not regress to a
ChemBL-only source of truth.

## Generated Evidence Governance

Normalization evidence is a governed artifact bundle, not a loose collection of
docs.

Current evidence bundle on `main`:

- canonical plan: [normalization_plan_P0_P6.md](normalization_plan_P0_P6.md)
- shipped multi-pipeline matrix: [pipeline_normalization_field_matrix.md](../reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md)
- fallback inventory report: [report_normalization_fallback_inventory.py](../../scripts/engineering/qa/report_normalization_fallback_inventory.py)
- published normalization reference entrypoint: [non-chembl-normalization-overview.md](../04-reference/normalization/non-chembl-normalization-overview.md)
- join-key policy seams: [join_keys.py](../../src/bioetl/domain/normalization/join_keys.py) and [join_key_normalization.py](../../src/bioetl/application/composite/join_key_normalization.py)
- non-ChEMBL identifier and collection fixtures: [non_chembl_identifier_cases.yaml](../../tests/fixtures/normalization/non_chembl_identifier_cases.yaml)
- non-ChEMBL observed-value fixtures: [non_chembl_observed_values.yaml](../../tests/fixtures/normalization/non_chembl_observed_values.yaml)

Governance rules:

- the canonical plan must describe the currently shipped profile registry
- the published matrix must be reproducible from code
- fallback inventory must classify business debt separately from technical passthrough
- normalization governance must publish surface-scoped KPIs instead of one blended headline:
  `explicit_profile_coverage_pct` for entity-record coverage,
  `composite_join_key_policy_coverage_pct` for composite join-key coverage, and
  `control_plane_normalization_coverage_pct` for control-plane / reproducibility coverage
- checkpoint governance consumers must import anchor helpers through the
  sanctioned package facade `bioetl.application.composite.checkpoint`
- join-key policies must remain part of the same normalization evidence story as entity profiles
- drift between plan, registry, matrix, and fallback inventory is a governance defect

## 2026-04-22 Final Profile/DQ/Schema Reconciliation

Issue `#3018` closes the normalization audit by making profile, schema, DQ,
and reference visibility explicit in the generated matrix instead of relying on
manual provider prose.

Generated inventory contract:

- source inputs are shipped entity configs, Silver Arrow schemas, domain Pandera
  schemas, active normalization profiles, DQ configs, and composite join-key
  configs
- each field row publishes `provider`, `pipeline_name`, `entity`, `field_name`,
  `normalizer`, `controlled_vocabulary_source`, `policy_scope`,
  `include_in_content_hash`, `set_like`, `hash_ordering`, `strictness`,
  `schema_coverage`, and `dq_coverage`
- `controlled_vocabulary_source` points to `configs/enums/chembl.yaml`,
  `configs/enums/pubchem.yaml`, `configs/enums/uniprot.yaml`, or the explicit
  profile/domain vocabulary seam
  when a field is not backed by a provider YAML enum file
- `policy_scope` distinguishes the full provider enum universe from narrower
  project subsets or canonical projections when DQ and operational filters do
  not ship the whole upstream vocabulary surface
- `schema_coverage` reports both Silver Arrow presence and domain schema
  presence/nullability/check visibility
- `dq_coverage` reports configured DQ validation type and effective severity,
  or `not_configured` when invalid values are intentionally handled only by
  normalization/schema behavior

Governed field-family visibility:

| Family                                     | Profile source                                                                               | Schema/DQ visibility                                                                                                                                                          | Hash/migration note                                                                                                                                   |
| ------------------------------------------ | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| ChEMBL strict enum and operator fields     | `enum_fields`, special enum/operator rules, and `configs/enums/chembl.yaml`                  | `tests/contract/test_chembl_enum_normalization_policy.py` verifies profile/schema/DQ/filter alignment for strict ChEMBL enum fields                                           | Invalid values collapse before `content_hash`; canonical enum casing may change hashes for previously dirty values                                    |
| Derived publication term enums             | `PUBLICATION_TERM_TYPES`, `configs/enums/chembl.yaml`, and `CHEMBL_PUBLICATION_TERM_PROFILE` | `tests/unit/domain/normalization/profiles/test_chembl_publication_term.py` verifies valid/lowercase/whitespace/invalid `term_type`; matrix rows expose schema and DQ coverage | `term_type` casing and invalid-value collapse can change hashes for previously dirty derived publication-term rows                                    |
| ChEMBL activity flags                      | `flag_fields` on `chembl.activity`                                                           | `tests/contract/test_chembl_activity_flag_policy.py` verifies profile/schema/DQ range alignment for `standard_flag`, `potential_duplicate`, and `manual_curation_flag`        | Persisted canonical values are integer `0`/`1`; molecule binary-like fields remain separately governed by their current profile/schema contracts      |
| DOI/PMID/PMC identifiers                   | `doi_fields`, `pmid_fields`, and `pmc_id_fields`                                             | `tests/contract/test_normalization_cross_layer_contracts.py` verifies helper, value-object, schema, profile, and processor convergence for publication identifiers            | Canonical identifier cleanup can change hashes for dirty casing, URL prefixes, leading zeros, or PMC prefix variants                                  |
| Non-ChEMBL identifier arrays               | `domain.normalization.reference_ids` plus publication/UniProt profile special rules           | `tests/unit/domain/normalization/profiles/test_additional_profiles.py` and `tests/fixtures/normalization/non_chembl_identifier_cases.yaml` verify ORCID, ISSN, OpenAlex, S2, UniProt, ChEMBL, and DrugBank canonicalization | Set-like identifier arrays are sorted/deduplicated before persisted canonical JSON and before `content_hash`                                          |
| Non-ChEMBL raw publication governance      | `configs/vocab/publication_controlled.yaml`, publication raw-type profiles, OA-status registry, and `publication_structured_fields.py` | `tests/fixtures/normalization/non_chembl_identifier_cases.yaml`, `test_additional_profiles.py`, and `test_generate_pipeline_normalization_field_matrix.py` verify unknown-preserving raw types, OA-status fail-closed behavior, and structured raw sidecars | Raw provider type lexemes are preserved for review; canonical cross-provider semantics remain in derived taxonomy fields                              |
| Semantic-sensitive structured payloads     | `structured_payload_policies.py`                                                             | `tests/unit/domain/normalization/test_structured_payload_policies.py`, `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`, and `tests/fixtures/normalization/non_chembl_observed_values.yaml` verify raw sidecar, canonical sidecar, and ordered/set/object semantics for `features_json`, `alternative_products`, `biophysicochemical_properties`, `cofactors`, `reactions`, `grants`, `primary_topic`, `authors_with_affiliations`, `affiliation_structured`, and Semantic Scholar `author_h_indices`/`citation_contexts`/`publication_types`/`subject_fields` | Persisted canonical JSON is not a raw-provider substitute; sidecar companions now ship as `*_raw_json` and `*_canonical_json` fields before any future semantic replacement or derivation |
| JSON/list canonicalization                 | `json_string_fields` plus `set_like_fields`                                                  | Matrix `hash_ordering` exposes `set_like` versus `order_sensitive`; cross-layer tests verify set-like hash invariance                                                         | Only explicit `set_like` fields are permutation-invariant; order-sensitive lists continue to affect `content_hash`                                    |
| Reviewed ChEMBL JSON ordering              | `chembl_json_ordering_policy.py` plus profile `json_string_fields` and `set_like_fields`      | `tests/unit/domain/normalization/profiles/test_additional_profiles.py`, `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py`, `tests/integration/config/test_chembl_observed_value_fixtures.py`, and `tests/architecture/test_normalization_surface_coverage_ratchet.py` verify policy/profile/matrix/fixture alignment | `tests/fixtures/normalization/chembl_observed_values.yaml` carries representative set-like and order-sensitive cases; changing reviewed ordering semantics is hash-affecting |
| Boolean, flag, operator, and unit families | `boolean_fields`, `flag_fields`, `operator_fields`, and `unit_fields`                        | Matrix `strictness`, `schema_coverage`, and `dq_coverage` expose whether schema/DQ also validates the field                                                                   | Invalid operational values either collapse to `None` before hashing or are rejected by schema/DQ where configured                                     |
| Ontology identifiers and BAO fields        | `ontology_id_fields` plus BAO-specific profile rules                                         | Matrix rows expose `domain.normalization.ontology_id_prefixes` as the vocabulary seam                                                                                         | OBO IRIs, lowercase prefixes, BAO colon forms, and numeric suffix variants canonicalize before hashing                                                |
| Composite-sensitive source fields          | Composite matrix inventory and `COMPOSITE_SENSITIVE_SOURCE_FIELDS`                           | `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py` verifies join-key policy coverage and source-profile coverage for propagated control fields         | Composite outputs inherit source-profile canonical forms; source normalization changes can affect merged records and hashes for dirty upstream values |
| Pseudo-null collapse                       | provider pseudo-null field sets                                                              | Matrix `strictness=normalization_only` and field notes identify collapse-to-`None` behavior                                                                                   | Collapsing sentinel values to `None` changes hashes only for records that previously carried pseudo-null text                                         |

Verification commands for this closure:

```bash
uv run pytest tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py tests/unit/scripts/test_generate_chembl_activity_field_matrix.py -q
uv run pytest tests/contract/test_normalization_cross_layer_contracts.py tests/contract/silver_schemas -q
uv run pytest tests/integration/config/test_chembl_observed_value_fixtures.py tests/architecture/test_normalization_surface_coverage_ratchet.py tests/architecture/test_normalization_evidence_governance.py -q
uv run pytest tests/integration/config/test_dq_config_loading.py -q
uv run pytest tests/unit/application/services/test_dq_report_service.py -q
uv run python -m scripts.docs build-site --strict --clean --site-dir /tmp/docs-site-strict
uv run ruff check src/bioetl tests
```

## P0 - Update and Publish the Plan

### Goal

Freeze vocabulary, invariants, and code seams in one canonical document.

### Required outcome

- this document is the source of requirements for `P0`-`P6`
- canonical JSON / datetime / SHA-256 / UUID rules are explicit
- current seams on `main` are linked directly to code

### Acceptance

- document exists at `docs/05-engineering/normalization_plan_P0_P6.md`
- document includes `P0`-`P6` and the invariants above
- document is linked from engineering docs, `RULES`, and policy docs

## P1 - Domain Normalization for Control Plane

### Goal

Keep `RunManifest` and `RunLedger` normalization pure and deterministic.

### Current state on `main`

- [control_plane.py](../../src/bioetl/domain/normalization/control_plane.py) already exists
- it normalizes UUIDs, datetimes, set-like collections, manifest payloads, and ledger payloads

### Requirements

- domain-only implementation
- no I/O
- no pandas
- no HTTP
- same input -> same output

### Acceptance

- control-plane functions remain pure
- UUID and datetime normalization are deterministic
- canonical list sorting for sanctioned set-like collections is stable

## P1 - Normalize Before `execution_fingerprint` in RunManifest

### Goal

`execution_fingerprint` must be computed only from normalized data.

### Current state on `main`

- [run_manifest_service.py](../../src/bioetl/application/services/control_plane/run_manifest_service.py) already normalizes payloads before hashing

### Requirements

- call `normalize_run_manifest_spec()`
- serialize only through canonical JSON
- list order must not affect the fingerprint for sanctioned set-like fields
- key order must never affect the fingerprint

### Acceptance

- semantically equivalent manifest payloads produce identical fingerprints

## P1 - Normalize RunLedger Before Persist

### Goal

Persist a deterministic ledger payload for equivalent lifecycle events.

### Current state on `main`

- [run_ledger_service.py](../../src/bioetl/application/services/control_plane/run_ledger_service.py) already calls `normalize_run_ledger_payload()`

### Requirements

- normalize before append
- `details` remain canonical
- `_diagnostic` envelope remains deterministic

### Acceptance

- equivalent events serialize identically
- key-order permutations do not change the stored JSON form

## P2 - Normalize `contract_ref`, Canonical Checkpoint Identity, and Degraded Anchors

### Goal

Stabilize checkpoint-resident execution identity and degraded runtime-anchor
helpers used for resume / compatibility checks.

### Current state on `main`

- `contract_ref` lowercases
- `contract_version` canonicalizes to semver-like `X.Y.Z`
- `effective_config_hash` lowercases
- canonical checkpoint execution identity reuses the same normalized payload
  family as manifest execution identity
- degraded runtime anchors remain narrower and must stay explicitly named

### Required target behavior

- `contract_ref` -> lowercase
- `contract_version` -> canonical semver string
- `effective_config_hash` -> lowercase
- invalid lexical forms fail validation early

### Acceptance

- checkpoint execution identity compares stably across runs
- degraded runtime anchors remain explicitly scoped to legacy fallback
- malformed anchor values are rejected instead of drifting into persisted state

## P3 - Normalization Profile Framework

### Goal

Replace heuristic drift with explicit field contracts.

### Current state on `main`

- [base.py](../../src/bioetl/domain/normalization/profiles/base.py) already defines:
  - `FieldRule`
  - `NormalizationProfile`
  - `include_in_hash`
  - `set_like`

### Requirements

- every schema field is covered explicitly
- normalization function is declared field by field
- hash participation is explicit per field
- standard profile families must distinguish:
  - pure textual normalization
  - explicitly declared JSON-bearing string normalization
  - meta-field passthrough outside `content_hash`

### Acceptance

- profile contracts fully describe normalization semantics for a covered schema

## P3 - Shipped Profile Registry

### Goal

Use explicit profiles as canonical contracts for covered pipeline schemas.

### Current state on `main`

- [registry.py](../../src/bioetl/domain/normalization/profiles/registry.py) already ships a canonical registry derived from one declarative shipped-profile table
- shipped profiles currently include:
  - `chembl.activity`
  - `chembl.assay`
  - `chembl.assay_parameters`
  - `chembl.cell_line`
  - `chembl.compound_record`
  - `chembl.molecule`
  - `chembl.protein_class`
  - `chembl.publication`
  - `chembl.publication_similarity`
  - `chembl.publication_term`
  - `chembl.subcellular_fraction`
  - `chembl.target`
  - `chembl.target_component`
  - `chembl.tissue`
  - `crossref.publication`
  - `openalex.publication`
  - `pubchem.compound`
    - canonical chemical standardization statuses are `standardized`,
      `partial`, `invalid`, and `missing_structure`; legacy fixture placeholders
      like `unchanged` / `failed` are retired from governed surfaces
  - `pubmed.publication`
  - `semanticscholar.publication`
  - `uniprot.idmapping`
  - `uniprot.protein`

### Requirements

- each covered schema field is described explicitly
- each profile field declares normalization behavior and hash participation
- profile lookup coordinates are canonicalized by provider/entity pair
- registry/module-path views must be derived from one canonical declaration rather than duplicated maps

### Acceptance

- shipped profiles resolve only through the canonical registry
- runtime registry and module-path registry cannot drift independently
- each shipped profile covers its target schema exactly
- covered fields do not depend on undocumented fallback heuristics

## P4 - Profile-Driven RecordNormalizationProcessor

### Goal

Make record-level normalization profile-aware while keeping compatibility
fallback explicit and bounded.

### Current state on `main`

- [record_normalization_processor.py](../../src/bioetl/application/core/record_normalization_processor.py) prefers a `NormalizationProfile`
- shipped profile-backed pipelines must fail loudly on unprofiled business fields by default
- compatibility fallback remains available only through explicit opt-in for bounded non-shipped or transitional paths

### Requirements

- if a shipped profile exists, use it and reject implicit fallback for uncovered business fields
- compatibility fallback must be enabled explicitly when transitional behavior is still required
- if no profile exists, keep fallback behavior
- hash semantics must be explainable by the active profile or explicit fallback policy

### Acceptance

- profile-driven shipped paths are active and fail on uncovered business fields
- fallback remains backward-compatible for uncovered entities and explicit compatibility mode only

## P4 - Composite Join-Key Normalization

### Goal

Keep composite join-key normalization deterministic without violating domain
purity or import boundaries.

### Current state on `main`

- [join_keys.py](../../src/bioetl/domain/normalization/join_keys.py) already ships pure scalar normalization policies
- [join_key_normalization.py](../../src/bioetl/application/composite/join_key_normalization.py) already applies those policies in application/composite flows

### Requirements

- pure scalar join-key policies stay in the domain layer
- DataFrame/runtime/config traversal stays in application/composite
- canonical trim/casing semantics for join-key text remain shared across composite runtime paths
- publication join-key identifiers must distinguish row-level canonical form from join-level canonical form:
  - row-level `pmid` stays digits-only
  - row-level `pmc_id` stays uppercase `PMC...`
  - join-level `pmid` must validate against the PMID contract before comparison
  - join-level `pmc_id` must validate against the PMC contract before lowercase comparison
  - wrong-family values must collapse before they participate in composite joins

### Acceptance

- domain join-key helpers remain dependency-free
- application adapters reuse the canonical domain policies rather than redefining them locally
- join-key behavior is documented as part of the normalization architecture
- composite publication joins cannot silently accept `pmc_id` payloads in `pmid` keys

## P4 - Stabilize Set-Like Lists

### Goal

Avoid hash drift from order-only changes in semantically unordered collections.

### Current state on `main`

- set-like fields are already carried from the active profile into `generate_content_hash(...)`

### Requirements

- only explicitly marked `set_like` fields get order-insensitive hashing
- ordering changes for non-`set_like` fields still affect the hash

### Acceptance

- permutations of set-like values do not change the hash
- order-sensitive lists still behave as order-sensitive

## P5 - Generate Field-Matrix Artifacts from Code

### Goal

Remove spreadsheet-like drift by generating the matrix from schemas, shipped
profiles, fallback seams, and composite join-key policies.

### Current state on `main`

- [generate_pipeline_normalization_field_matrix.py](../../scripts/docs/generate_pipeline_normalization_field_matrix.py) already generates deterministic multi-pipeline artifacts

### Requirements

- CSV is mandatory
- MD is first-class published artifact
- DOCX/PDF remain optional
- output order is deterministic
- the artifact reflects shipped profile coverage, fallback coverage, and join-key normalization seams
- the published matrix should surface the normalized coverage split across
  entity-record, composite join-key, and control-plane / reproducibility seams
  so maintainers can track each normalization surface without overstating repo-wide closure

### Acceptance

- two runs on unchanged code produce byte-identical CSV
- matrix content is derived from code, not edited manually

## P6 - Tests and Governance

### Goal

Enforce determinism through tests and reviewable policy changes.

### Required test families

- `T1`: `execution_fingerprint` determinism
- `T2`: `content_hash` determinism
- `T3`: generated artifact reproducibility

### Required governance rules

- domain normalization remains dependency-free
- hash/fingerprint changes require explicit reviewable updates
- docs remain linked to the canonical plan

### Acceptance

- CI-visible tests guard the determinism contract
- policy changes are explicit rather than accidental

## T1 - Fingerprint Tests

### Goal

Prove `RunManifest` fingerprint determinism.

### Required coverage

- golden tests
- permutation tests for sanctioned set-like collections
- key-order invariance checks

### Acceptance

- `execution_fingerprint` remains stable for equivalent manifest inputs

## T2 - Content Hash Tests

### Goal

Prove business-hash stability for equivalent normalized data.

### Required coverage

- canonical JSON shape
- DOI / PMID normalization
- set-like list permutation invariance
- profile include/exclude behavior

### Acceptance

- equivalent normalized records produce identical `content_hash`

## T3 - Artifact Reproducibility Tests

### Goal

Prove generated documentation is reproducible.

### Required coverage

- run generator twice
- compare CSV byte-for-byte
- optional artifact generation must not affect CSV determinism

### Acceptance

- generated CSV is byte-identical across repeated runs on unchanged code

## Recommended Validation Commands

```bash
rg -n '^## P[0-6]\b|^## T[1-3]\b' docs/05-engineering/normalization_plan_P0_P6.md
python3 -m scripts.docs verify --skip-build
python3 -m scripts.docs generate-pipeline-normalization-matrix --check
```

## Related Documents

- [RULES.md](../00-project/RULES.md)
- [Content Hash Identity Policy](../02-architecture/policies/content-hash-identity-policy.md)
- [ADR-014 Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-044 Run Manifest and Run Ledger](../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [Run Manifest Inspection](../05-operations/runbooks/run-manifest-inspection.md)
