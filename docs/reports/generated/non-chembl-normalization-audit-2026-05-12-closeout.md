# BioETL: non-ChEMBL normalization audit closeout on current `main`

Дата генерации: 2026-05-12  
Режим: архитектурно-строгий static audit по current repository state после remediation wave по non-ChEMBL normalization.  
Ограничения: live provider APIs не вызывались; использованы только registry/configs/contracts/tests/fixtures/VCR-derived artifacts и generated matrices из репозитория.

## 1. Executive summary

### Установленные факты

- Все 7 non-ChEMBL entity pipelines зарегистрированы в отдельном registry manifest и имеют entity config, Silver schema и active Gold contract:
  `pubchem_compound`, `uniprot_protein`, `uniprot_idmapping`, `pubmed_publication`, `crossref_publication`, `openalex_publication`, `semanticscholar_publication`
  ([src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py),
  [configs/base/contract_registry.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/base/contract_registry.yaml)).
- Tracked Bronze fixture coverage есть у всех 7 entity pipelines; tracked edge fixtures теперь есть и у `crossref/publication`, и у `uniprot/protein`
  ([configs/base/bronze_fixture_manifest.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/base/bronze_fixture_manifest.yaml),
  [tests/integration/fixtures/test_non_chembl_edge_fixture_manifest.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/fixtures/test_non_chembl_edge_fixture_manifest.py)).
- Publication-family raw provider vocabularies и derived harmonized taxonomy разведены и проверяются parity gate-ами
  ([configs/vocab/publication_controlled.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/publication_controlled.yaml),
  [tests/integration/config/test_publication_controlled_vocab_parity.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_publication_controlled_vocab_parity.py)).
- Shared identifier canonicalization layer для non-ChEMBL pipelines остаётся domain-pure и покрывает DOI, PMID, PMCID, ORCID, ISSN, OpenAlex IDs, PubChem CID, UniProt accessions, DrugBank, ChEMBL, GO, InterPro, Pfam, Reactome и mixed UniProt mapping sets
  ([src/bioetl/domain/normalization/reference_ids.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/reference_ids.py),
  [src/bioetl/domain/normalization/_reference_id_registry.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/_reference_id_registry.py)).
- Structured/JSON payload governance теперь explicit и repo-backed для Publication, UniProt и CrossRef semantic-sensitive surfaces
  ([src/bioetl/domain/normalization/publication_structured_fields.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/publication_structured_fields.py),
  [src/bioetl/domain/normalization/structured_payload_policies.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/structured_payload_policies.py),
  [configs/vocab/crossref_structured_payloads.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/crossref_structured_payloads.yaml),
  [configs/vocab/uniprot_semantic_payloads.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/uniprot_semantic_payloads.yaml),
  [configs/vocab/pubchem_semantic_payloads.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/pubchem_semantic_payloads.yaml)).
- Composite join-key normalization для non-ChEMBL boundaries зафиксирован golden tests и current config contracts
  ([tests/unit/application/composite/test_non_chembl_join_key_normalization.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/application/composite/test_non_chembl_join_key_normalization.py),
  [configs/composites/publication.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/composites/publication.yaml),
  [configs/composites/molecule.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/composites/molecule.yaml),
  [configs/composites/target.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/composites/target.yaml)).

### Вывод

По current `main` после remediation wave non-ChEMBL normalization находится в состоянии `pass / no newly confirmed defects`.

- `Layer correctness`: pass
- `Determinism / content_hash readiness`: pass
- `Silver/Gold/DQ contract alignment`: pass
- `Cross-provider identifier canonicalization`: pass
- `Unified enum-aware governance`: pass for current repo-observed scope
- `Composite-readiness`: pass

### Ограничение аудита

Неполнота live provider universes остаётся только confidence limitation, а не подтверждённой дефектной зоной: audit опирается на tracked fixtures, edge fixtures, VCR-derived observed inventory и generated matrix, а не на live API crawls.

## 2. Scope inventory

| Pipeline | Provider | Entity | Registered? | Config exists? | Transformer exists? | Silver schema | Gold contract | Fixtures/VCR/sample coverage | Included? | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| `pubchem_compound` | `pubchem` | `compound` | yes | yes | yes | yes | active | tracked CI + edge | yes | chemical reference |
| `uniprot_protein` | `uniprot` | `protein` | yes | yes | yes | yes | active | tracked CI + edge | yes | target bridge source |
| `uniprot_idmapping` | `uniprot` | `idmapping` | yes | yes | yes | yes | active | tracked CI + edge | yes | composite target gate |
| `pubmed_publication` | `pubmed` | `publication` | yes | yes | yes | yes | active | tracked CI + edge | yes | strongest MeSH/status coverage |
| `crossref_publication` | `crossref` | `publication` | yes | yes | yes | yes | active | tracked CI + edge | yes | `crossref.works` deprecated alias retained in contract registry |
| `openalex_publication` | `openalex` | `publication` | yes | yes | yes | yes | active | tracked CI + edge | yes | OA/topic/grant-rich |
| `semanticscholar_publication` | `semanticscholar` | `publication` | yes | yes | yes | yes | active | tracked CI + edge | yes | subject/citation context sidecars |
| `composite_publication` | `composite` | `publication` | config/runtime | yes | composite runtime | merged | composite contract surface | join-key fixtures/tests | yes | non-ChEMBL enrichers only |
| `composite_molecule` | `composite` | `molecule` | config/runtime | yes | composite runtime | merged | composite contract surface | join-key fixtures/tests | yes | PubChem boundary |
| `composite_target` | `composite` | `target` | config/runtime | yes | composite runtime | merged | composite contract surface | join-key fixtures/tests | yes | UniProt bridge boundary |

Source of truth for this inventory:
[src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py),
[configs/base/contract_registry.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/base/contract_registry.yaml),
[configs/base/bronze_fixture_manifest.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/base/bronze_fixture_manifest.yaml).

## 3. Fact base

| Area | Provider | Pipeline | Artifact | Факт | Вывод |
|---|---|---|---|---|---|
| Registry completeness | all non-ChEMBL | all entity pipelines | `_registry_manifest_non_chembl.py` | 7 entity pipelines зарегистрированы в canonical registry | structural scope complete |
| Contract completeness | all non-ChEMBL | all entity pipelines | `contract_registry.yaml` | у всех 7 entity pipelines active Gold contract entries | Gold governance complete |
| Fixture completeness | all non-ChEMBL | all entity pipelines | `bronze_fixture_manifest.yaml` | tracked CI fixtures есть у всех 7; edge fixtures есть у всех 7 | prior edge-fixture gap closed |
| Publication raw vocab governance | publication family | 4 publication pipelines | `publication_controlled.yaml`, parity test | raw provider values externalized and matrix-backed | raw provider types remain open-world by design |
| Publication derived taxonomy | publication family | 4 publication pipelines + composite | publication profiles/configs + matrix | `publication_type_unified` / `publication_class` / `publication_subclass` derived from raw provider type | cross-provider analytical taxonomy is stable |
| Identifier canonicalization | cross-provider | publications, pubchem, uniprot, composite boundaries | `reference_ids.py` | shared canonicalizers cover key identifier families plus mixed UniProt mapping sets | no provider-local identifier drift confirmed |
| CrossRef structured payload policy | crossref | `crossref_publication` | `crossref_structured_payloads.yaml`, governance test | `author_details` and `references` explicitly governed as canonical-only structured payloads | prior CrossRef governance asymmetry closed |
| UniProt semantic payload registry | uniprot | `uniprot_protein` | `uniprot_semantic_payloads.yaml`, registry test | registry now covers feature/comment/keyword semantic families and profile-backed field groups | prior deep-payload governance gap closed |
| PubChem semantic registry | pubchem | `pubchem_compound` | `pubchem_semantic_payloads.yaml`, registry test | semantic field groups and property URN axes are explicit | prior semantic-registry gap closed |
| Composite join-key hardening | composite | publication/molecule/target | join-key tests + composite configs | canonical join keys match fixture-based golden contracts | no currently confirmed composite normalization drift |

## 4. Unified enum/vocabulary inventory

Полный per-field inventory уже materialized в generated matrix:
[pipeline_normalization_field_matrix.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md)
и observed-value inventory:
[non_chembl_observed_value_inventory.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/non_chembl_observed_value_inventory.md).

Критические поля и их итоговая классификация:

| Provider | Pipeline | Field | Layer | Observed values/examples | Cardinality | Classification | Current normalization | Proposed normalization | Priority |
|---|---|---|---|---|---:|---|---|---|---|
| PubMed | `pubmed_publication` | `publication_status` | Silver/Gold/DQ | `published`, `ahead_of_print`, `retracted` repo-observed set | bounded reviewed set | strict enum | shared controlled vocab + DQ + matrix parity | keep as-is | none |
| CrossRef | `crossref_publication` | `publication_type` | Silver/Gold/Composite | `journal-article`, `posted-content`, `book-chapter` | provider-expandable | controlled vocabulary / raw provider value | open-world raw provider value + derived taxonomy | keep raw open-world | none |
| OpenAlex | `openalex_publication` | `source_type` | Silver/Gold | `journal`, `repository`, `conference` | provider-expandable | controlled vocabulary | publication controlled registry + profile | keep as-is | none |
| OpenAlex | `openalex_publication` | `oa_status` | Silver/Gold/DQ | reviewed OA status set | reviewed closed set | strict enum | shared OA status seam | keep as-is | none |
| Semantic Scholar | `semanticscholar_publication` | `publication_type` | Silver/Gold | `JournalArticle`, `Review`, unknown pass-through | provider-expandable | controlled vocabulary / raw provider value | raw provider value with known spellings canonicalized | keep raw open-world | none |
| PubChem | `pubchem_compound` | `chemical_standardization_status` | Silver/Gold/DQ | `standardized`, `partial`, `invalid`, `missing_structure` | 4 | strict enum | reviewed policy constant + config + contract | keep as-is | none |
| PubChem | `pubchem_compound` | `molecule_id` | Silver/Gold/Composite | `CID:2244`, `2244` | scalar namespace | ontology/reference identifier | canonical PubChem CID normalization | keep as-is | none |
| UniProt | `uniprot_protein` | `entry_type` | Silver/Gold/DQ | reviewed/unreviewed surface | 2 | strict enum | profile + config + contract | keep as-is | none |
| UniProt | `uniprot_protein` | `protein_existence` | Silver/Gold/DQ | evidence-level phrases | bounded reviewed set | controlled vocabulary | profile-backed normalized text | keep as-is | none |
| UniProt | `uniprot_idmapping` | `mapping_status` | Silver/Gold/DQ | `found`, `not_found`, `error`, `multiple` | 4 | strict enum | profile + DQ + composite target gate | keep as-is | none |
| UniProt | `uniprot_idmapping` | `all_mappings` | Silver/Gold | mixed UniProt/DrugBank/ChEMBL identifiers | mixed-family set | ontology/reference identifier set | mixed identifier canonicalizer into set-like canonical JSON | keep as-is | none |
| Composite | `composite_publication` | `doi`, `pmid`, `title` | Composite join-key | canonical DOI/PMID and whitespace-hardened title fallback | scalar | join-key contract fields | shared canonical identifier seam + join-key normalization | keep as-is | none |

## 5. Identifier canonicalization inventory

| Identifier family | Providers/pipelines | Fields | Current canonicalization | Issues | Proposed canonicalization | Hash impact | Contract impact |
|---|---|---|---|---|---|---|---|
| DOI | all publication providers + composite publication | `doi` | shared canonical DOI normalizer in `reference_ids.py` | none confirmed | keep | stable hash anchor | composite join-safe |
| PMID / PMCID | PubMed, OpenAlex, Semantic Scholar, composite publication | `pmid`, `pmcid` | shared PMID/PMCID normalizers | none confirmed | keep | stable hash anchor | join-safe |
| ORCID / ROR / ISSN | publication family | author/source/license-related identifier arrays | shared canonical registry + structured payload policies | none confirmed | keep | deterministic canonical JSON | contract-safe |
| PubChem CID | PubChem + composite molecule | `molecule_id` | strips namespace noise, canonical CID text | none confirmed | keep | stable upstream hash | composite-safe |
| UniProt accession | UniProt protein/idmapping + composite target | `accession`, `target_id`, `all_mappings` subset | canonical uppercase accession normalization | none confirmed | keep | stable bridge anchor | composite target-safe |
| GO / InterPro / Pfam / Reactome | UniProt protein | xref arrays | namespace canonicalizers | none confirmed | keep | deterministic unordered-set hash | contract-safe |
| Mixed mapping identifier set | UniProt idmapping | `all_mappings` | family-aware mixed identifier normalizer with set-like canonical JSON | none confirmed | keep | deterministic hash preserved | contract-safe for current string contract |

## 6. JSON / structured field inventory

| Provider | Pipeline | Field | Shape | Current representation | Current serialization | Deterministic? | Contract type | Proposed representation | Priority |
|---|---|---|---|---|---|---|---|---|---|
| PubMed | `pubmed_publication` | `mesh_terms_structured` | list of objects | canonical JSON + raw/canonical sidecars | governed unordered-set policy | yes | string | keep | none |
| PubMed | `pubmed_publication` | `affiliation_structured` | list of objects | canonical JSON + raw/canonical sidecars | governed unordered-set policy | yes | string | keep | none |
| CrossRef | `crossref_publication` | `author_details` | ordered object list | canonical JSON only | explicit canonical-only policy | yes | string | keep | none |
| CrossRef | `crossref_publication` | `references` | ordered object list | canonical JSON only | explicit canonical-only policy | yes | string | keep | none |
| OpenAlex | `openalex_publication` | `grants` | unordered object list | canonical JSON + sidecars | governed set-like policy | yes | string | keep | none |
| OpenAlex | `openalex_publication` | `primary_topic` | structured object | canonical JSON + sidecars | structured-object policy | yes | string | keep | none |
| Semantic Scholar | `semanticscholar_publication` | `publication_types` | unordered label list | canonical JSON + sidecars | governed set-like policy | yes | string | keep | none |
| Semantic Scholar | `semanticscholar_publication` | `citation_contexts` | ordered snippet list | canonical JSON + sidecars | governed ordered policy | yes | string | keep | none |
| UniProt | `uniprot_protein` | `features_json` | ordered feature list | canonical JSON + sidecars | semantic-sensitive ordered policy | yes | string | keep | none |
| UniProt | `uniprot_protein` | `alternative_products`, `cofactors`, `reactions` | list/object payloads | canonical JSON only | explicit canonical-only policy | yes | string | keep | none |
| UniProt | `uniprot_idmapping` | `all_mappings` | mixed identifier list | canonical JSON set | family-aware mixed-ID policy | yes | string | keep | none |

## 7. Reuse / drift matrix

| Rule / Field Family | Providers/pipelines using it | Implemented where | Is behavior identical? | Drift risk | Recommendation |
|---|---|---|---|---|---|
| DOI/PMID canonicalization | all publication providers + composite publication | `reference_ids.py`, profiles, matrix/tests | yes | low | keep shared seam |
| Raw publication type open-world policy | 4 publication pipelines | `publication_controlled.yaml`, profiles, parity tests | yes | low | keep shared parity gate |
| Derived publication taxonomy | 4 publication pipelines + composite publication | publication classification layer | yes | low | keep |
| Structured payload semantic sidecars | PubMed, OpenAlex, Semantic Scholar, UniProt, CrossRef canonical-only subset | `publication_structured_fields.py`, `structured_payload_policies.py` | yes within declared policy | low | keep |
| PubChem semantic field registry | PubChem only | `pubchem_semantic_payloads.yaml` | entity-specific | low | keep |
| UniProt nested semantic payload registry | UniProt protein only | `uniprot_semantic_payloads.yaml` | entity-specific | low | keep |
| Mixed identifier set normalization | UniProt idmapping only | `reference_ids.py`, profile, matrix | yes | low | keep |
| Composite join-key normalization | `composite_publication`, `composite_molecule`, `composite_target` | join-key layer + golden tests | yes | low | keep |

## 8. Gap analysis

### Установленный факт

Fresh audit не подтвердил ни одного нового открытого defect-class gap в следующих категориях:

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
- replay/debug traceability gap

### Вывод

Previous non-ChEMBL remediation wave закрыла подтверждённые P1/P2 governance gaps. Current repo state не требует нового GitHub issue backlog по этой теме.

### Ограничение аудита

Остаётся только evidence-depth limitation:

- audit строится по tracked fixtures, edge fixtures и generated inventories, а не по live provider universes;
- это влияет на confidence envelope, но не даёт оснований утверждать о текущем дефекте.

## 9. Предложение расширений нормализации

Новых обязательных расширений не требуется.

Допустимы только future optional improvements без открытия defect issue:

| Extension | Layer | Target module/file | Expected input/output | Affected pipelines | Backward compatibility | `content_hash` impact | Contract impact | DQ impact | Composite impact | Migration need | Required tests |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Expand observed inventories from additional VCR slices | docs/scripts/tests | `report_non_chembl_observed_value_inventory.py` | more observed evidence, no semantic change | publication/pubchem/uniprot | additive | none | none | none | none | no | script unit tests |
| Add more edge fixtures for rare provider branches | fixtures/tests | `tests/fixtures/bronze/**` | broader evidence only | any non-ChEMBL family | additive | none | none | none | none | no | fixture manifest + observed-value tests |
| Add more golden cases for composite join fallback noise | tests only | `test_non_chembl_join_key_normalization.py` | broader normalization evidence | composite publication/molecule/target | additive | none | none | none | improves confidence only | no | unit golden tests |

## 10. План P0-P2

### P0

Нет подтверждённых P0 blockers.

### P1

Нет подтверждённых P1 remediation tasks.

### P2

Только optional evidence-depth enhancements без issue creation:

1. Добавлять edge fixtures при появлении новых provider branches.
2. Расширять observed-value inventories при обновлении VCR.
3. Поддерживать matrix/check suites зелёными при эволюции contracts/configs.

## 11. Архитектурный вердикт

### Layer correctness

Pass. Во время closeout-аудита не подтверждено I/O inside domain normalization и не подтверждено infrastructure leakage в domain/application normalization surfaces. Shared registries остаются immutable и domain-pure.

### Determinism

Pass. Identifier canonicalization, structured payload policies, join-key normalization и matrix-backed normalization contracts задают детерминированное поведение для current repo-observed surfaces.

### Medallion correctness

Pass. Bronze fixture evidence остаётся source-like; Silver/Gold normalization and contract surfaces согласованы; derived harmonized vocabularies не подменяют raw provider semantics там, где сохранён dual-field strategy.

### Replay / debug correctness

Pass. Current normalization surfaces fully represented in configs, profiles, tests, matrix artifacts и observed inventories; unexplained content-hash drift по audited non-ChEMBL surfaces не подтверждён.

## 12. Sources

- [src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/pipeline/_registry_manifest_non_chembl.py)
- [configs/base/contract_registry.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/base/contract_registry.yaml)
- [configs/base/bronze_fixture_manifest.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/base/bronze_fixture_manifest.yaml)
- [configs/vocab/publication_controlled.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/publication_controlled.yaml)
- [configs/vocab/crossref_structured_payloads.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/crossref_structured_payloads.yaml)
- [configs/vocab/uniprot_semantic_payloads.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/uniprot_semantic_payloads.yaml)
- [configs/vocab/pubchem_semantic_payloads.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/pubchem_semantic_payloads.yaml)
- [src/bioetl/domain/normalization/reference_ids.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/reference_ids.py)
- [src/bioetl/domain/normalization/_reference_id_registry.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/_reference_id_registry.py)
- [src/bioetl/domain/normalization/publication_structured_fields.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/publication_structured_fields.py)
- [src/bioetl/domain/normalization/structured_payload_policies.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/structured_payload_policies.py)
- [tests/integration/config/test_publication_controlled_vocab_parity.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_publication_controlled_vocab_parity.py)
- [tests/integration/fixtures/test_non_chembl_edge_fixture_manifest.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/fixtures/test_non_chembl_edge_fixture_manifest.py)
- [tests/contract/test_non_chembl_cross_layer_contract_matrix.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/contract/test_non_chembl_cross_layer_contract_matrix.py)
- [tests/unit/domain/normalization/test_crossref_structured_payload_governance.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/domain/normalization/test_crossref_structured_payload_governance.py)
- [tests/unit/domain/normalization/test_uniprot_semantic_payload_registry.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/domain/normalization/test_uniprot_semantic_payload_registry.py)
- [tests/unit/domain/normalization/test_pubchem_semantic_payload_registry.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/domain/normalization/test_pubchem_semantic_payload_registry.py)
- [tests/unit/application/composite/test_non_chembl_join_key_normalization.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/application/composite/test_non_chembl_join_key_normalization.py)
- [tests/unit/scripts/qa/test_report_non_chembl_observed_value_inventory.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/scripts/qa/test_report_non_chembl_observed_value_inventory.py)
- [docs/reports/generated/non_chembl_observed_value_inventory.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/non_chembl_observed_value_inventory.md)
- [docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md)
