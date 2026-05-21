# Non-ChEMBL Normalization Audit On Current `main` (2026-05-19)

Baseline:
- audited branch: `main`
- audited local `HEAD`: `39a0232da7a73f0a647abd7793e36caf58b4fa81`
- local `origin/main` ref at audit time: `00bc861ec3d71acf5349771e8f8cd416c1587c70`
- scope decision: this audit is grounded in the current local state of branch `main`, not in the cached remote-tracking ref
- excluded scope: all `chembl_*` normalization internals, except non-ChEMBL composite join/context boundaries that interact with mixed-source composites

Reference artifacts used throughout:
- `docs/00-project/RULES.md`
- `docs/02-architecture/decisions/ADR-014-deterministic-writes.md`
- `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`
- `docs/02-architecture/decisions/ADR-035-json-field-typing-policy.md`
- `docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md`
- `docs/02-architecture/decisions/ADR-045-dq-contract-system.md`
- `configs/base/contract_registry.yaml`
- `src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py`
- `docs/reports/generated/pipeline_normalization_field_matrix/non_chembl_normalization_field_matrix.md`
- `docs/reports/generated/non_chembl_observed_value_inventory.md`
- `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
- `tests/integration/test_cross_provider_doi_normalization.py`
- `tests/integration/config/test_non_chembl_identifier_dq_parity.py`
- `tests/integration/config/test_publication_controlled_vocab_parity.py`
- `tests/integration/normalization/test_non_chembl_edge_observed_values.py`
- `tests/unit/application/composite/test_non_chembl_join_key_normalization.py`

## 1. Executive Summary

### Установленные факты

- В проекте существует единый non-ChEMBL normalization layer, а не набор разрозненных transformer-fixups. Это подтверждают `src/bioetl/domain/normalization/profiles/_standard_profile_builder.py`, `src/bioetl/domain/normalization/profiles/profile_normalizers.py`, `src/bioetl/domain/normalization/reference_ids.py`, `src/bioetl/domain/normalization/join_keys.py` и generated matrix `docs/reports/generated/pipeline_normalization_field_matrix/non_chembl_normalization_field_matrix.md`.
- По current matrix structural coverage complete:
  - entity-record explicit profile coverage: `405/405`
  - composite join-key policy coverage: `13/13`
  - composite-sensitive source-field profile coverage: `19/19`
  - control-plane normalization coverage: `6/6`
  - shipped profile meta passthrough invariants: `205/205`
  - shipped set-like JSON-string invariants: `67/67`
  - shipped non-meta passthrough-free invariants: `678/678`
- Все 7 non-ChEMBL entity pipelines зарегистрированы в canonical registry manifest и имеют active entity config, Silver schema и Gold contract:
  `crossref_publication`, `openalex_publication`, `pubchem_compound`, `pubmed_publication`, `semanticscholar_publication`, `uniprot_idmapping`, `uniprot_protein`
  (`src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py`, `configs/base/contract_registry.yaml`).
- Publication-family shared taxonomy governance now closes the earlier parity gap: all four publication providers use shared custom DQ validators for `publication_type_unified`, `publication_subclass`, `publication_class` in their configs (`configs/entities/crossref/publication.yaml`, `configs/entities/openalex/publication.yaml`, `configs/entities/pubmed/publication.yaml`, `configs/entities/semanticscholar/publication.yaml`) and this is enforced by `tests/integration/config/test_non_chembl_identifier_dq_parity.py` and `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`.
- PubChem CID normalization is now explicit and repo-backed: `pubchem_compound.molecule_id` uses `normalize_profile_pubchem_cid` in `src/bioetl/domain/normalization/profiles/pubchem_compound.py`; its DQ config enforces canonical CID text in `configs/entities/pubchem/compound.yaml`; regression coverage exists in `tests/unit/domain/normalization/profiles/test_publication_identifier_profiles.py`.
- CrossRef structured payload governance no longer lags OpenAlex/PubMed/S2: `author_details_raw_json`, `author_details_canonical_json`, `references_raw_json`, and `references_canonical_json` are now part of the schema/config/profile seam (`src/bioetl/domain/normalization/profiles/crossref_publication.py`, `configs/entities/crossref/publication.yaml`) and are enforced by `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`.
- UniProt reference-array DQ now matches profile-owned canonicalization breadth for `secondary_accessions`, `chembl_ids`, `drugbank_ids`, `go_terms`, `interpro_xrefs`, `pdb_xrefs`, `pfam_xrefs`, `reactome_xrefs`, plus explicit `reviewed` governance in both `protein` and `idmapping` configs (`configs/entities/uniprot/protein.yaml`, `configs/entities/uniprot/idmapping.yaml`).

### Вывод

По current local `main` non-ChEMBL normalization находится в состоянии `pass / no newly confirmed defect-class gaps`.

- `Layer correctness`: pass
- `Determinism / content_hash readiness`: pass
- `Silver / Gold / DQ contract alignment`: pass
- `Cross-provider identifier canonicalization`: pass
- `Structured JSON governance`: pass
- `Composite boundary readiness`: pass
- `Replay/debug normalization traceability`: pass for repo-backed current-state contracts and inventories

### Главные риски

Подтвержденных `P0` или `P1` normalization defects audit не выявил.

Остаются только `P2 confidence` risks:
- observed-value universes по publication-like provider vocabularies, PubChem property vocabularies и UniProt semantic payloads ограничены tracked fixtures/VCR-derived inventories, а не live provider crawls;
- composite molecule по-прежнему корректно удерживает `standardized_inchi_key` и `structure_parent_key` как retained validation anchors, но не активирует их как symmetric join keys до появления matching seed anchors (`configs/composites/molecule.yaml`). Это explicit design limitation, а не defect.

### Ограничения аудита

- Audit не обращался к live provider APIs.
- Audit опирается на repo-backed configs, contracts, profiles, tests, fixtures, VCR-derived inventories и generated matrices.
- Поэтому уверенность высокая для implemented policy correctness, и средняя для полноты full-universe vocabulary census.

## 2. Scope Inventory

| Pipeline | Provider | Entity | Registered? | Config exists? | Transformer exists? | Silver schema | Gold contract | Fixtures/VCR/sample coverage | Included? | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| `crossref_publication` | CrossRef | publication | yes | `configs/entities/crossref/publication.yaml` | yes | yes | yes | tracked fixture + edge fixture + VCR | yes | publication family |
| `openalex_publication` | OpenAlex | publication | yes | `configs/entities/openalex/publication.yaml` | yes | yes | yes | tracked fixture + edge fixture + VCR | yes | publication family |
| `pubmed_publication` | PubMed | publication | yes | `configs/entities/pubmed/publication.yaml` | yes | yes | yes | tracked fixture + edge fixture + VCR | yes | publication family |
| `semanticscholar_publication` | Semantic Scholar | publication | yes | `configs/entities/semanticscholar/publication.yaml` | yes | yes | yes | tracked fixture + edge fixture + VCR | yes | publication family |
| `pubchem_compound` | PubChem | compound | yes | `configs/entities/pubchem/compound.yaml` | yes | yes | yes | tracked fixture + edge fixture + VCR | yes | compound/reference family |
| `uniprot_idmapping` | UniProt | idmapping | yes | `configs/entities/uniprot/idmapping.yaml` | yes | yes | yes | tracked fixture + edge fixture + VCR | yes | target bridge/reference family |
| `uniprot_protein` | UniProt | protein | yes | `configs/entities/uniprot/protein.yaml` | yes | yes | yes | tracked fixture + edge fixture + VCR | yes | protein/reference family |
| `composite_publication` | composite | publication | config/runtime | yes | composition runtime | merged | composite contract | join-key fixtures/tests | yes | analyzed for non-ChEMBL enricher impact only |
| `composite_molecule` | composite | molecule | config/runtime | yes | composition runtime | merged | composite contract | join-key fixtures/tests | yes | analyzed for PubChem impact only |
| `composite_target` | composite | target | config/runtime | yes | composition runtime | merged | composite contract | join-key fixtures/tests | yes | analyzed for UniProt impact only |

Установленный факт:
- В active registry/config/test surfaces не найдено дополнительных non-ChEMBL entity pipelines beyond the seven above.

Вывод:
- Requested scope is complete for current local `main`.

## 3. Fact Base

| Area | Provider | Pipeline | Artifact | Факт | Вывод |
|---|---|---|---|---|---|
| Registry completeness | all | all 7 entity pipelines | `_registry_manifest_non_chembl.py` | all 7 are registered in canonical runtime registry | structural scope complete |
| Contract completeness | all | all 7 entity pipelines | `configs/base/contract_registry.yaml` | all 7 have active Gold contract exports | contract layer complete |
| Profile coverage | all | all non-ChEMBL entities | `non_chembl_normalization_field_matrix.md` | explicit entity-field profile coverage is `405/405` | no uncovered entity fields |
| Composite join coverage | composite | publication/molecule/target | `non_chembl_normalization_field_matrix.md`, `join_keys.py` | join-key policy coverage is `13/13` | composite join normalization is explicit, not ad hoc |
| Composite-sensitive source coverage | composite | publication/molecule/target | `non_chembl_normalization_field_matrix.md` | composite-sensitive source-field profile coverage is `19/19` | composite boundaries are profile-backed |
| Publication taxonomy parity | CrossRef/OpenAlex/PubMed/S2 | publication family | provider configs + cross-layer tests | all providers use shared custom validators for derived taxonomy fields | previous taxonomy DQ asymmetry closed |
| DOI normalization | CrossRef/OpenAlex/PubMed/S2 | publication family | `tests/integration/test_cross_provider_doi_normalization.py` | same DOI converges to same canonical value across providers and keeps per-provider hash stable | deterministic cross-provider join anchor confirmed |
| Raw publication type governance | CrossRef/OpenAlex/PubMed/S2 | publication family | `configs/vocab/publication_controlled.yaml`, parity tests | raw provider `publication_type` remains open-world; derived taxonomy is harmonized separately | provider semantics preserved without forcing closed enum |
| CrossRef structured payload sidecars | CrossRef | `crossref_publication` | profile/config/schema/contract tests | `author_details` and `references` now publish raw and canonical sidecars | previous CrossRef structured-payload governance gap closed |
| OpenAlex structured payload sidecars | OpenAlex | `openalex_publication` | `openalex_publication.py` | `primary_topic` and `grants` use raw/canonical dual-field strategy | semantic-sensitive source fidelity preserved |
| PubMed structured payload sidecars | PubMed | `pubmed_publication` | `pubmed_publication.py` | structured author/affiliation payloads use raw/canonical dual-field strategy | semantic-sensitive source fidelity preserved |
| Semantic Scholar unordered arrays | Semantic Scholar | `semanticscholar_publication` | `semanticscholar_publication.py`, contract tests | `publication_types` and `subject_fields` canonicalize unordered arrays deterministically | hash-safe set-like semantics confirmed |
| PubChem CID canonicalization | PubChem | `pubchem_compound` | `pubchem_compound.py`, `compound.yaml`, identifier fixture tests | `molecule_id` canonicalizes `CID:`-prefixed inputs to canonical CID string | previous CID governance gap closed |
| PubChem enum externalization | PubChem | `pubchem_compound` | `compound.yaml`, `configs/enums/pubchem.yaml`, cross-layer tests | `chemical_standardization_status` and `chemical_standardization_policy_version` are cross-layer governed | strict policy surfaces stable |
| UniProt bridge semantics | UniProt | `uniprot_idmapping` | `uniprot_idmapping.py`, `target.yaml` | `mapping_status` gates target enrichment and `target_id -> uniprot_accession` bridge is canonicalized | idmapping is part of identity semantics, not a loose helper |
| UniProt nested semantic payload governance | UniProt | `uniprot_protein` | `uniprot_protein.py`, `configs/vocab/uniprot_semantic_payloads.yaml` | semantic payload families are registry-backed and sidecar-governed | deep payload governance mature |
| Fixture completeness | all | all 7 entity pipelines | `configs/base/bronze_fixture_manifest.yaml`, edge-fixture tests | tracked edge fixtures exist for all 7 families | previous fixture coverage gap closed |

## 4. Unified Enum / Vocabulary Inventory

Interpretation note:
- Full per-field inventory is materialized in `docs/reports/generated/pipeline_normalization_field_matrix/non_chembl_normalization_field_matrix.md`.
- The table below lists governance-relevant enum/vocabulary surfaces and cross-provider decision points.

| Provider | Pipeline | Field | Layer | Observed values/examples | Cardinality | Classification | Current normalization | Proposed normalization | Priority |
|---|---|---|---|---|---:|---|---|---|---|
| CrossRef | `crossref_publication` | `publication_type` | Silver, DQ, matrix | `journal-article`, `posted-content`, `book-chapter`, unknown preserved | open-world | controlled vocabulary / raw provider value | preserve raw provider text; derive shared taxonomy separately | keep | none |
| CrossRef | `crossref_publication` | `publication_type_unified` | Silver, Gold, DQ | shared taxonomy values such as `Journal Article` | bounded | strict derived taxonomy | shared custom validator + derived taxonomy rules | keep | none |
| CrossRef | `crossref_publication` | `author_orcids` | Silver, DQ | canonical ORCID array | large identifier family | ontology/reference identifier set | canonical JSON array of ORCIDs | keep | none |
| OpenAlex | `openalex_publication` | `oa_status` | Silver, Gold, DQ | `gold`, `green`, `hybrid`, `bronze`, `closed` | 5 | strict enum | shared OA registry | keep | none |
| OpenAlex | `openalex_publication` | `publication_type` | Silver | raw OpenAlex type strings | open-world | controlled vocabulary / raw provider value | preserve raw; derive shared taxonomy separately | keep | none |
| OpenAlex | `openalex_publication` | `primary_topic` | Silver, Gold | structured OpenAlex topic reference | medium | derived vocabulary / ontology-backed reference | canonical object + raw/canonical sidecars | keep | none |
| PubMed | `pubmed_publication` | `publication_status` | Silver, DQ, matrix | `ppublish`, `epublish`, `aheadofprint` plus unknown-preserving path | bounded reviewed set | strict enum with drift visibility | governed vocabulary preserving unknowns | keep | none |
| PubMed | `pubmed_publication` | `publication_types` | Silver | ordered/raw provider terms like `Review`, `Clinical Trial` | extensible | controlled vocabulary collection | canonical JSON string collection + derived taxonomy separately | keep | none |
| Semantic Scholar | `semanticscholar_publication` | `publication_type` | Silver, DQ | known spellings canonicalized, unknowns preserved | extensible | controlled vocabulary / raw provider value | provider-aware raw canonicalizer | keep | none |
| Semantic Scholar | `semanticscholar_publication` | `publication_types` | Silver, Gold | unordered arrays like `["JournalArticle","Review"]` | low-medium | controlled vocabulary collection | deterministic unordered JSON canonicalization + raw sidecar | keep | none |
| Semantic Scholar | `semanticscholar_publication` | `subject_fields` | Silver, Gold | unordered subject arrays from fixture inventory | medium | quasi-enum / derived vocabulary | deterministic unordered JSON canonicalization + raw sidecar | keep non-strict | none |
| PubChem | `pubchem_compound` | `molecule_id` | Silver, Gold, composite | `CID:2244`, `2244` | large identifier family | provider-specific reference identifier | canonical PubChem CID normalizer | keep | none |
| PubChem | `pubchem_compound` | `chemical_standardization_status` | Silver, Gold, DQ | `standardized`, `partial`, `invalid`, `missing_structure` | 4 | strict enum | externalized enum + profile + DQ | keep | none |
| UniProt | `uniprot_idmapping` | `mapping_status` | Silver, Gold, DQ, composite | `found`, `not_found`, `error`, `multiple` | 4 | strict enum | profile enum + DQ + composite gate | keep | none |
| UniProt | `uniprot_idmapping` | `all_mappings` | Silver, Gold | mixed ID arrays (`CHEMBL203`, `P00742`, `Q9Y6K9`) | mixed-family | ontology/reference identifier collection | mixed-ID canonical JSON array | keep | none |
| UniProt | `uniprot_protein` | `entry_type` | Silver, Gold, DQ | reviewed/unreviewed labels | 2 | strict enum | profile enum + DQ | keep | none |
| UniProt | `uniprot_protein` | `protein_existence` | Silver, Gold, DQ | five evidence levels | 5 | strict enum / controlled vocabulary | profile enum + DQ | keep | none |
| UniProt | `uniprot_protein` | `secondary_accessions` | Silver, Gold, DQ | canonical accession arrays | large identifier family | ontology/reference identifier set | canonical accession-array normalizer + DQ regex | keep | none |
| UniProt | `uniprot_protein` | `go_terms`, `molecular_function`, `cellular_component` | Silver, Gold, DQ | GO IDs or objects with `id` | large ontology | ontology-backed identifier collections | shared GO reference canonicalizers + DQ patterns | keep | none |

Установленный факт:
- Audit не нашёл новых surfaces, которые должны быть немедленно переведены из open-world provider vocabularies в strict enums.

Вывод:
- Current enum/vocabulary split between raw provider semantics and harmonized analytical semantics is architecturally sound.

## 5. Identifier Canonicalization Inventory

| Identifier family | Providers/pipelines | Fields | Current canonicalization | Issues | Proposed canonicalization | Hash impact | Contract impact |
|---|---|---|---|---|---|---|---|
| DOI | CrossRef/OpenAlex/PubMed/S2/composite publication | `doi` | shared canonical DOI seam in profiles and join keys | none confirmed | keep | stable high-impact hash anchor | publication contracts and composite joins remain aligned |
| PMID | OpenAlex/PubMed/S2/CrossRef/composite publication | `pmid` | shared digits-only canonicalizer, join-key aware | none confirmed | keep | stable join/hash anchor | publication joins remain aligned |
| PMCID | OpenAlex/PubMed/S2/CrossRef | `pmc_id` | shared canonical `PMC...` normalizer | none confirmed | keep | medium | publication contracts remain aligned |
| ISSN | CrossRef/OpenAlex/PubMed/S2 | `issn`, `issn_list`, `issn_print`, `issn_electronic` | shared scalar/array ISSN canonicalizers | none confirmed | keep | low-medium | contract-safe |
| ORCID | CrossRef/OpenAlex/PubMed/S2 | `author_orcids` | shared ORCID array canonicalizer | none confirmed | keep | low | contract-safe |
| OpenAlex IDs | OpenAlex | `openalex_id`, `author_openalex_ids`, `institution_ids`, `ror_ids`, `subject_topics`, `primary_topic` | provider-specific canonicalizers built on shared reference-ID registry | none confirmed | keep | medium | OpenAlex contract-safe |
| Semantic Scholar IDs | Semantic Scholar | `paper_id`, `author_s2_ids`, `corpus_id` | provider-specific canonicalizers | none confirmed | keep | medium | S2 contract-safe |
| PubChem CID | PubChem | `molecule_id` | dedicated `pubchem_cid` canonicalizer strips namespace noise and normalizes CID text | no confirmed gap remains | keep | high | upstream identity and composite molecule boundary remain stable |
| InChIKey | PubChem/composite molecule | `inchi_key`, `standardized_inchi_key` | canonical InChIKey value-object normalization | no confirmed gap remains | keep | medium | composite molecule boundary remains explicit |
| UniProt accession | UniProt protein/idmapping/composite target | `accession`, `uniprot_accession`, `secondary_accessions`, `isoform_ids` | shared accession and accession-array canonicalizers | none confirmed | keep | high | target bridge and protein contracts remain stable |
| NCBI taxonomy ID | UniProt protein/idmapping | `taxonomy_id` | shared taxonomy canonicalizer + aligned DQ range policy | no confirmed mismatch remains | keep | medium | bridge and protein contracts remain aligned |
| GO / InterPro / Pfam / PDB / Reactome / DrugBank / ChEMBL | UniProt protein | reference arrays and structured payload projections | family-aware reference canonicalizers + DQ patterns for governed arrays | none confirmed | keep | medium | Gold and DQ surfaces remain aligned |

## 6. JSON / Structured Field Inventory

| Provider | Pipeline | Field | Shape | Current representation | Current serialization | Deterministic? | Contract type | Proposed representation | Priority |
|---|---|---|---|---|---|---|---|---|---|
| CrossRef | `crossref_publication` | `author_details` | ordered object array | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| CrossRef | `crossref_publication` | `references` | ordered object array | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| OpenAlex | `openalex_publication` | `primary_topic` | structured object | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| OpenAlex | `openalex_publication` | `grants` | unordered object collection | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| PubMed | `pubmed_publication` | `affiliation_structured` | structured affiliation array | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| PubMed | `pubmed_publication` | `authors_with_affiliations` | ordered author/affiliation array | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| Semantic Scholar | `semanticscholar_publication` | `publication_types` | unordered string array | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| Semantic Scholar | `semanticscholar_publication` | `subject_fields` | unordered string array | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep non-strict | none |
| Semantic Scholar | `semanticscholar_publication` | `citation_contexts` | ordered object array | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| UniProt | `uniprot_protein` | `alternative_products` | structured comment payload | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| UniProt | `uniprot_protein` | `biophysicochemical_properties` | structured comment payload | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| UniProt | `uniprot_protein` | `cofactors` | structured comment payload | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| UniProt | `uniprot_protein` | `features_json` | ordered feature payload | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| UniProt | `uniprot_protein` | `reactions` | structured reaction payload | canonical JSON + raw/canonical sidecars | JSON string | yes | string | keep | none |
| UniProt | `uniprot_idmapping` | `all_mappings` | mixed identifier array | canonical JSON only | JSON string | yes | string | keep canonical-only | none |

Установленный факт:
- No audited non-ChEMBL structured payload currently violates ADR-035 string-typed JSON policy or hash determinism constraints.

Вывод:
- Structured payload governance is now consistent enough across publication, PubChem-related, and UniProt surfaces for current repo-backed semantics.

## 7. Reuse / Drift Matrix

| Rule / Field Family | Providers/pipelines using it | Implemented where | Is behavior identical? | Drift risk | Recommendation |
|---|---|---|---|---|---|
| DOI canonicalization | all publication providers + composite publication | `reference_ids.py`, profiles, `join_keys.py`, DOI integration test | yes | low | keep shared seam |
| PMID / PMCID canonicalization | publication providers + composite publication | shared profiles + `join_keys.py` | yes | low | keep |
| Raw publication type open-world policy | CrossRef/OpenAlex/PubMed/S2 | profiles + `publication_controlled.yaml` + parity tests | yes | low | keep raw open-world strategy |
| Derived publication taxonomy | CrossRef/OpenAlex/PubMed/S2 | `_publication_classification_rules.py`, configs, Gold common schema | yes | low | keep shared taxonomy seam |
| OA status | OpenAlex/S2 | shared OA normalizer + DQ | yes | low | keep |
| Structured payload raw/canonical sidecar strategy | CrossRef/OpenAlex/PubMed/S2/UniProt | `publication_structured_fields.py`, `structured_payload_policies.py`, provider profiles | yes within declared policy | low | keep |
| PubChem CID canonicalization | PubChem only | `pubchem_compound.py`, reference-ID registry, config, profile tests | yes | low | keep |
| PubChem anchor boundary policy | composite molecule | `configs/composites/molecule.yaml`, composite join-key tests | yes | low | keep explicit retained-anchor policy |
| UniProt accession/reference-array canonicalization | UniProt protein/idmapping/composite target | shared reference-ID seam + provider profiles + DQ patterns | yes | low | keep |
| Mixed mapping-set canonicalization | UniProt idmapping | `reference_ids.py`, `uniprot_idmapping.py`, DQ pattern | yes | low | keep |
| Composite target bridge normalization | `uniprot_idmapping` -> `uniprot_protein` | `configs/composites/target.yaml`, join-key tests | yes | low | keep |

## 8. Gap Analysis

### Установленный факт

Fresh current-state audit did not confirm any open defect-class gaps in the following categories:

- missing normalization
- weak canonicalization
- missing enum externalization
- missing vocabulary registry
- schema / contract mismatch
- hashing inconsistency
- DQ mismatch
- identifier canonicalization mismatch
- ontology/reference handling mismatch
- JSON canonicalization mismatch
- architectural placement issue
- cross-provider normalization drift
- composite merge normalization mismatch
- fixture/VCR/sample defect gap
- replay/debug traceability gap

### Вывод

The remediation wave represented earlier by `#4292`-`#4296` is reflected in the current codebase, configs, generated matrices, fixtures, and tests. The older artifact `reports/quality/non_chembl_normalization_audit_2026-05-19.md` is therefore stale and should not be used as the current-state source of truth.

### Ограничение аудита

Only evidence-depth limitations remain:

- tracked fixtures and VCR-derived inventories are not the same as exhaustive live provider universes;
- this lowers confidence in full-universe vocabulary census, but it does not provide evidence of a present defect.

## 9. Proposed Extensions

No mandatory normalization remediation tasks are currently justified.

Allowed optional improvements are evidence-depth and governance-maintenance tasks only:

| Extension | Layer | Target module/file | Expected input/output | Affected providers/pipelines | Backward compatibility | `content_hash` impact | Silver/Gold impact | DQ impact | Composite impact | Migration need | Required tests |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Expand observed-value inventory from additional tracked VCR slices | scripts/tests/docs | `scripts/engineering/qa/report_non_chembl_observed_value_inventory.py` | broader observed evidence, no semantic change | publication family, PubChem, UniProt | additive only | none | none | none | none | no | inventory script tests |
| Add more edge fixtures for rare provider branches | fixtures/tests | `tests/fixtures/bronze/**` | broader observed evidence only | any non-ChEMBL family | additive only | none | none | none | none | no | fixture manifest + observed-value tests |
| Add more composite join-noise golden cases | tests only | `tests/unit/application/composite/test_non_chembl_join_key_normalization.py` | broader regression evidence only | composite publication/molecule/target | additive only | none | none | none | improves confidence only | no | unit golden tests |

## 10. Plan P0-P2

### P0

No confirmed P0 blockers.

### P1

No confirmed P1 remediation tasks.

### P2

Only optional confidence work:

1. Expand tracked observed-value inventories when VCR or bronze edge fixtures grow.
2. Add more rare-branch fixture coverage for provider-specific publication and UniProt payload branches.
3. Keep the matrix and cross-layer contract suites green during future contract/schema evolution.

## 11. Architectural Verdict

### Layer correctness

Pass.

Установленный факт:
- The audited normalization seams remain domain-pure. Shared policies live in domain normalization profiles, reference-ID helpers, and pure join-key policies, while wiring stays in composition/runtime configs.

Вывод:
- No confirmed Hexagonal / DDD placement regression exists in the current non-ChEMBL normalization layer.

### Determinism

Pass.

Установленный факт:
- Hash-relevant normalization for identifiers, set-like JSON arrays, and semantic-sensitive payloads is explicitly governed and regression-tested. DOI hash convergence is covered by `tests/integration/test_cross_provider_doi_normalization.py`. Set-like JSON behavior and matrix invariants are covered by contract, unit, and matrix tests.

Вывод:
- No current evidence shows order-sensitive nondeterminism leaking into normalized non-ChEMBL persisted rows.

### Medallion correctness

Pass.

Установленный факт:
- Bronze remains source-like and fixture-backed.
- Silver is explicitly normalized through profiles.
- Gold contracts remain active and aligned with Silver/domain schemas and DQ configuration.
- Raw/canonical dual-field strategy is used where semantic transformation could otherwise erase source meaning.

Вывод:
- Current non-ChEMBL normalization respects Medallion boundaries.

### Replay / debug correctness

Pass.

Установленный факт:
- Normalization seams are represented in configs, profiles, tests, generated matrix artifacts, and observed-value inventory artifacts. No unexplained content-hash drift is evidenced by current-state tests for audited non-ChEMBL surfaces.

Вывод:
- Repo-backed replay/debug traceability for non-ChEMBL normalization is sufficient for current-state governance.

## 12. Checks

Executed during this audit:

- `uv run pytest -q tests/contract/test_non_chembl_cross_layer_contract_matrix.py tests/integration/config/test_non_chembl_identifier_dq_parity.py tests/integration/config/test_publication_controlled_vocab_parity.py tests/integration/fixtures/test_non_chembl_edge_fixture_manifest.py tests/integration/normalization/test_non_chembl_edge_observed_values.py tests/integration/test_cross_provider_doi_normalization.py tests/unit/application/composite/test_non_chembl_join_key_normalization.py tests/unit/scripts/qa/test_report_non_chembl_observed_value_inventory.py`
  Result: pass, with `16` expected skips from live-API-gated cases inside `test_non_chembl_cross_layer_contract_matrix.py`
- `uv run pytest -q tests/unit/application/core/test_non_chembl_normalization_hash_golden.py tests/unit/domain/normalization/test_reference_ids.py tests/unit/domain/normalization/test_join_keys.py tests/unit/domain/normalization/profiles/test_publication_identifier_profiles.py tests/unit/domain/normalization/profiles/test_additional_profiles.py tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py tests/architecture/test_non_chembl_json_field_typing_policy.py -k 'non_chembl or pubchem or uniprot or crossref or openalex or pubmed or semanticscholar or join_key or reference_identifier'`
  Result: pass

Static source checks performed:

- verified current registry scope in `src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py`
- verified active contract references in `configs/base/contract_registry.yaml`
- verified current matrix summary in `docs/reports/generated/pipeline_normalization_field_matrix/non_chembl_normalization_field_matrix.md`
- verified current observed-value inventory in `docs/reports/generated/non_chembl_observed_value_inventory.md`

Skipped by design:

- live provider API probing
- full repository test suite

## 13. Sources

- `docs/00-project/RULES.md`
- `docs/02-architecture/decisions/ADR-014-deterministic-writes.md`
- `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`
- `docs/02-architecture/decisions/ADR-035-json-field-typing-policy.md`
- `docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md`
- `docs/02-architecture/decisions/ADR-045-dq-contract-system.md`
- `src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py`
- `configs/base/contract_registry.yaml`
- `configs/base/bronze_fixture_manifest.yaml`
- `configs/entities/crossref/publication.yaml`
- `configs/entities/openalex/publication.yaml`
- `configs/entities/pubchem/compound.yaml`
- `configs/entities/pubmed/publication.yaml`
- `configs/entities/semanticscholar/publication.yaml`
- `configs/entities/uniprot/idmapping.yaml`
- `configs/entities/uniprot/protein.yaml`
- `configs/composites/molecule.yaml`
- `configs/composites/publication.yaml`
- `configs/composites/target.yaml`
- `configs/vocab/publication_controlled.yaml`
- `src/bioetl/domain/normalization/reference_ids.py`
- `src/bioetl/domain/normalization/join_keys.py`
- `src/bioetl/domain/normalization/profiles/pubchem_compound.py`
- `src/bioetl/domain/normalization/profiles/crossref_publication.py`
- `src/bioetl/domain/normalization/profiles/openalex_publication.py`
- `src/bioetl/domain/normalization/profiles/pubmed_publication.py`
- `src/bioetl/domain/normalization/profiles/semanticscholar_publication.py`
- `src/bioetl/domain/normalization/profiles/uniprot_idmapping.py`
- `src/bioetl/domain/normalization/profiles/uniprot_protein.py`
- `docs/reports/generated/pipeline_normalization_field_matrix/non_chembl_normalization_field_matrix.md`
- `docs/reports/generated/non_chembl_observed_value_inventory.md`
- `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`
- `tests/integration/config/test_non_chembl_identifier_dq_parity.py`
- `tests/integration/config/test_publication_controlled_vocab_parity.py`
- `tests/integration/fixtures/test_non_chembl_edge_fixture_manifest.py`
- `tests/integration/normalization/test_non_chembl_edge_observed_values.py`
- `tests/integration/test_cross_provider_doi_normalization.py`
- `tests/unit/application/composite/test_non_chembl_join_key_normalization.py`
- `tests/unit/application/core/test_non_chembl_normalization_hash_golden.py`
- `tests/unit/domain/normalization/test_reference_ids.py`
- `tests/unit/domain/normalization/test_join_keys.py`
- `tests/unit/domain/normalization/profiles/test_publication_identifier_profiles.py`
- `tests/unit/domain/normalization/profiles/test_additional_profiles.py`
- `tests/unit/scripts/test_generate_pipeline_normalization_field_matrix.py`
- `tests/unit/scripts/qa/test_report_non_chembl_observed_value_inventory.py`
- `tests/architecture/test_non_chembl_json_field_typing_policy.py`
