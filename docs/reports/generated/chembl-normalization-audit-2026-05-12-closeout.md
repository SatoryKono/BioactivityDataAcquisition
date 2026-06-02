# BioETL: ChEMBL normalization audit closeout on current `main`

Дата генерации: 2026-05-12  
Режим: архитектурно-строгий static audit по current repository state после ChEMBL normalization remediation wave.  
Ограничения: live ChEMBL API не вызывался; использованы registry/configs/contracts/tests/fixtures/VCR-derived artifacts и generated matrix/inventory surfaces из репозитория.

## 1. Executive summary

### Установленные факты

- Все 14 `chembl_*` entity pipelines зарегистрированы в canonical registry manifest
  ([src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py)).
- Все 14 имеют tracked Bronze fixture coverage; observed-value inventory для ChEMBL строится из этих tracked fixtures и сейчас содержит `14` fixtures / `191` field rows
  ([configs/base/bronze_fixture_manifest.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/base/bronze_fixture_manifest.yaml),
  [docs/reports/generated/chembl_observed_value_inventory.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/chembl_observed_value_inventory.md)).
- Active Gold contract coverage и registry/fixture parity для ChEMBL закрыты тестами
  ([configs/base/contract_registry.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/base/contract_registry.yaml),
  [tests/integration/config/test_chembl_registry_fixture_contract_parity.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_chembl_registry_fixture_contract_parity.py),
  [tests/integration/config/test_chembl_contract_registry_coverage.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_chembl_contract_registry_coverage.py)).
- Unified ChEMBL normalization layer существует и опирается на shared policy/enum/reference registries, а не на ad-hoc filesystem parsing внутри domain:
  [chembl_policy_registry.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/chembl_policy_registry.py),
  [\_chembl_vocab.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/_chembl_vocab.py),
  [\_chembl_reference_identifier_rules.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/_chembl_reference_identifier_rules.py),
  [configs/enums/chembl.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/enums/chembl.yaml),
  [configs/vocab/chembl_controlled.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/chembl_controlled.yaml),
  [configs/vocab/chembl_ontology.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/chembl_ontology.yaml).
- Enum/DQ/catalog sync, ontology companion policy, derived vocabulary policy и high-risk hash determinism уже защищены contract/integration/unit tests
  ([tests/integration/config/test_chembl_enum_parity.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_chembl_enum_parity.py),
  [tests/integration/config/test_chembl_dq_catalog_sync.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_chembl_dq_catalog_sync.py),
  [tests/contract/test_chembl_ontology_bundle_policy.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/contract/test_chembl_ontology_bundle_policy.py),
  [tests/contract/test_chembl_derived_vocabulary_contracts.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/contract/test_chembl_derived_vocabulary_contracts.py),
  [tests/unit/application/core/test_chembl_normalization_hash_golden.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/application/core/test_chembl_normalization_hash_golden.py),
  [tests/unit/domain/hash_policy/test_chembl_high_risk_hash_golden.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/domain/hash_policy/test_chembl_high_risk_hash_golden.py)).

### Вывод

По current `main` ChEMBL family находится в состоянии `pass / no newly confirmed defects`.

- `Layer correctness`: pass
- `Determinism / content_hash readiness`: pass
- `Silver/Gold/DQ alignment`: pass
- `Enum-aware unified normalization`: pass for current repo-observed ChEMBL scope
- `Cross-family consistency`: pass

### Ограничение аудита

Observed sets по-прежнему repo-bounded: audit опирается на tracked fixtures, edge fixtures, VCR-derived evidence и generated matrix, а не на full live ChEMBL universe. Это ограничение уверенности, а не подтверждённый дефект.

## 2. Fact base

| Area | Pipeline | Artifact | Факт | Вывод |
|---|---|---|---|---|
| Registry completeness | all `chembl_*` | `_registry_manifest_chembl.py` | manifest содержит 14 ChEMBL pipelines | structural scope complete |
| Fixture completeness | all `chembl_*` | `bronze_fixture_manifest.yaml`, `chembl_observed_value_inventory.md` | tracked CI fixtures есть у всех 14; inventory built from 14 fixtures | observed-value governance complete for repo-backed scope |
| Contract completeness | all `chembl_*` | `contract_registry.yaml`, parity tests | Gold-enabled ChEMBL entities have active contract entries | Gold governance complete |
| Enum parity | activity/assay/molecule/target/publication families | `test_chembl_enum_parity.py` | config surfaces are subset/equality-governed against `configs/enums/chembl.yaml` | prior enum drift surface is closed |
| DQ catalog sync | high-risk enum fields | `test_chembl_dq_catalog_sync.py` | DQ allowed sets stay aligned with enum/controlled registries | no confirmed DQ-vs-registry mismatch |
| Derived vocabulary contracts | `publication_term`, `subcellular_fraction`, `assay_parameters` | `test_chembl_derived_vocabulary_contracts.py`, `test_chembl_derived_vocabulary_policy.py` | derived vocab surfaces have explicit contract/policy guards | no confirmed semantic drift in derived layers |
| Ontology companion bundles | activity / target_component / cell_line / tissue | `test_chembl_ontology_bundle_policy.py`, `test_chembl_ontology_edge_fixtures.py` | ontology companion mapping statuses and edge fixtures are governed | no confirmed ontology-handling mismatch |
| Hash determinism | activity/molecule/target/target_component/publication | high-risk hash golden tests | canonical JSON / policy-backed hash behavior is stable | no confirmed high-risk hash drift |
| Matrix completeness | all `chembl_*` | `pipeline_normalization_field_matrix.md` | matrix exposes field-level classifications and policy sources across ChEMBL family | full field inventory already materialized |

## 3. Unified enum inventory

Полный per-field inventory уже materialized в:
[pipeline_normalization_field_matrix.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md)
и
[chembl_observed_value_inventory.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/chembl_observed_value_inventory.md).

Критические семейства полей по текущему состоянию:

| Pipeline | Field | Layer | Observed values/examples | Cardinality | Classification | Current normalization | Proposed normalization | Priority |
|---|---|---|---|---:|---|---|---|---|
| `chembl_activity` | `standard_relation` | Silver/Gold/DQ | `=`, `>`, `>=`, `<`, `<=`, `~` | bounded reviewed set | strict operator | canonical ASCII operator enum via `configs/enums/chembl.yaml` | keep as-is | none |
| `chembl_activity` | `standard_type` | Silver/Gold/DQ | `IC50`, `EC50`, `Ki`, `Kd`, ... repo-observed subset | provider-bounded reviewed subset | strict enum / controlled boundary | enum-backed normalization with parity guards | keep as-is | none |
| `chembl_activity` | `standard_units` | Silver/Gold/DQ | `nM`, `uM`, `%`, `mg.kg-1`, ... | controlled term family | controlled vocabulary | alias collapse + governed controlled vocab | keep as-is | none |
| `chembl_activity` | `bao_*`, `uo_*`, `qudt_*` ids/statuses | Silver/Gold | ontology ids + mapping statuses | namespace-backed | ontology-backed identifiers / strict mapping metadata | companion-bundle normalization | keep as-is | none |
| `chembl_assay` | `assay_type` | Silver/Gold/DQ | `B`, `F`, `A`, `T`, ... | bounded reviewed set | strict enum | uppercase enum normalization | keep as-is | none |
| `chembl_assay` | `assay_test_type`, `assay_category`, `relationship_type` | Silver/Gold/DQ | governed subsets | provider-bounded | controlled vocabulary / strict enum mix | registry-backed normalization | keep as-is | none |
| `chembl_molecule` | `molecule_type`, `structure_type` | Silver/Gold/DQ | ChEMBL type families | bounded reviewed set | strict enum / controlled vocabulary | config+profile parity | keep as-is | none |
| `chembl_molecule` | `max_phase` | Silver/Gold/DQ | `-1`, `0`, `0.5`, `1`, `2`, `3`, `4` | 7 | quasi-enum numeric | numeric quasi-enum normalization | keep as-is | none |
| `chembl_molecule` | `ro3_pass`, review flags | Silver/Gold/DQ | `Y/N`, reviewed flag codes | low-cardinality reviewed sets | boolean-like / flag-like | explicit flag policy | keep as-is | none |
| `chembl_target` | `target_type` | Silver/Gold/DQ | 14 ChEMBL target types | bounded reviewed set | controlled vocabulary | registry-backed normalization | keep as-is | none |
| `chembl_target_component` | `component_type` | Silver/Gold/DQ | `PROTEIN`, `DNA`, `RNA` | 3 | strict enum | profile-backed normalization | keep as-is | none |
| `chembl_cell_line` | `clo_id`, `efo_id`, `cellosaurus_id`, `taxonomy_id` | Silver/Gold | namespace identifiers | namespace-backed | ontology/reference identifiers | shared ontology/reference canonicalization | keep as-is | none |
| `chembl_tissue` | `bto_id`, `caloha_id`, `efo_id`, `uberon_id` | Silver/Gold | namespace identifiers | namespace-backed | ontology/reference identifiers | shared ontology/reference canonicalization | keep as-is | none |
| `chembl_assay_parameters` | `type`, `standard_type`, `standard_relation`, `standard_units` | Silver/Gold/DQ | parameter vocab and operator/unit families | provider-bounded | controlled vocabulary / strict operator | profile-backed raw+canonical strategy | keep as-is | none |
| `chembl_publication` | `publication_type` | Silver/Gold/DQ | source-specific ChEMBL publication types | provider-bounded | controlled vocabulary | source-specific governed subset | keep as-is | none |
| `chembl_publication_term` | `term_type` | Silver/Gold/DQ | `MESH_HEADING`, `MESH_QUALIFIER`, `KEYWORD` | 3 | strict enum | strict enum normalization with parity guards | keep as-is | none |
| `chembl_subcellular_fraction` | `subcellular_fraction` | Silver/Gold/Derived | assay-derived labels | provider-expandable | derived vocabulary | controlled extraction / derived contract | keep as-is | none |

## 4. Reuse / drift matrix

| Rule / Field Family | Pipelines using it | Implemented where | Is behavior identical? | Drift risk | Recommendation |
|---|---|---|---|---|---|
| ChEMBL enum catalog access | activity, assay, molecule, target, publication, publication_term, assay_parameters | `configs/enums/chembl.yaml`, `\_chembl_vocab.py`, profiles, parity tests | yes | low | keep shared seam |
| Controlled vocab registry access | activity, assay, publication, assay_parameters, molecule | `configs/vocab/chembl_controlled.yaml`, profiles, parity tests | yes | low | keep |
| Ontology/reference companion bundles | activity, target_component, cell_line, tissue | `chembl_ontology.yaml`, policy registry, ontology tests | yes | low | keep |
| Pseudo-null collapse | family-wide | `chembl_pseudo_nulls.py`, profile helpers, tests | yes | low | keep |
| Hash canonical JSON policy | activity, molecule, target, target_component, publication | `chembl_json_ordering_policy.py`, hash golden tests | yes | low | keep |
| Derived vocabulary contracts | publication_term, subcellular_fraction, assay_parameters | derived policy/contract tests | yes | low | keep |
| Reference identifier canonicalization | target/component/cell_line/tissue/publication/activity adjunct IDs | shared ChEMBL reference identifier rules | yes | low | keep |

## 5. Gap analysis

### Установленный факт

Fresh closeout-аудит не подтвердил новых открытых проблем в следующих классах:

- missing normalization
- weak canonicalization
- missing enum externalization
- schema / contract mismatch
- hashing inconsistency
- DQ mismatch
- ontology-handling mismatch
- JSON canonicalization mismatch
- architectural placement issue
- cross-pipeline normalization drift

### Вывод

Предыдущая remediation wave по ChEMBL закрыла подтверждённые structural gaps. Current `main` не требует нового defect backlog для `chembl_*` normalization.

### Ограничение аудита

Repo-observed inventory остаётся bounded fixtures evidence. Это влияет на полноту observed universe, но не даёт оснований утверждать о текущем дефекте normalization governance.

## 6. Предложение расширений нормализации

Новых обязательных расширений не требуется.

Допустимы только optional evidence-depth improvements без issue creation:

| Extension | Layer placement | Target module/file | Expected input/output | Backward compatibility | `content_hash` impact | Silver/Gold/DQ impact | Composite/derived impact |
|---|---|---|---|---|---|---|---|
| Expand edge Bronze fixtures for new provider branches | tests/fixtures | `tests/fixtures/bronze/chembl/**` | more observed evidence only | additive | none | confidence only | confidence only |
| Expand observed inventory snapshots | docs/scripts/tests | `report_chembl_observed_value_inventory.py` | broader observed sets | additive | none | confidence only | confidence only |
| Add more golden canonical JSON/hash cases for future complex fields | tests | hash golden suites | stronger regression coverage | additive | none unless behavior changes | confidence only | confidence only |

## 7. План исправлений P0-P2

### P0

Нет подтверждённых P0 blockers.

### P1

Нет подтверждённых P1 remediation tasks.

### P2

Только optional evidence-depth enhancements:

1. Расширять edge fixtures при появлении новых ChEMBL provider branches.
2. Поддерживать inventory/matrix parity suites зелёными.
3. Добавлять новые golden cases только при появлении новых structured/hash-sensitive surfaces.

## 8. Архитектурный вердикт

### Layer correctness

Pass. Domain normalization для ChEMBL использует shared immutable registries и profile helpers; I/O inside domain normalization и infrastructure leakage в audited surfaces не подтверждены.

### Determinism

Pass. Enum/operator/unit/ontology normalization, pseudo-null collapse и hash canonicalization стабилизированы тестами и generated matrix contracts.

### Medallion correctness

Pass. Bronze остаётся source-like; Silver normalizes governed fields; Gold contract surfaces align with config/schema/policy; derived/reference vocabularies имеют explicit contract seams.

## 9. Sources

- [src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/composition/factories/pipeline/_registry_manifest_chembl.py)
- [configs/base/bronze_fixture_manifest.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/base/bronze_fixture_manifest.yaml)
- [configs/base/contract_registry.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/base/contract_registry.yaml)
- [configs/enums/chembl.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/enums/chembl.yaml)
- [configs/vocab/chembl_controlled.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/chembl_controlled.yaml)
- [configs/vocab/chembl_ontology.yaml](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/configs/vocab/chembl_ontology.yaml)
- [src/bioetl/domain/normalization/profiles/chembl_policy_registry.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/chembl_policy_registry.py)
- [src/bioetl/domain/normalization/profiles/_chembl_vocab.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/_chembl_vocab.py)
- [src/bioetl/domain/normalization/profiles/_chembl_reference_identifier_rules.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/_chembl_reference_identifier_rules.py)
- [src/bioetl/domain/normalization/profiles/chembl_json_ordering_policy.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/bioetl/domain/normalization/profiles/chembl_json_ordering_policy.py)
- [docs/reports/generated/chembl_observed_value_inventory.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/chembl_observed_value_inventory.md)
- [docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/generated/pipeline_normalization_field_matrix/pipeline_normalization_field_matrix.md)
- [tests/integration/config/test_chembl_registry_fixture_contract_parity.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_chembl_registry_fixture_contract_parity.py)
- [tests/integration/config/test_chembl_contract_registry_coverage.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_chembl_contract_registry_coverage.py)
- [tests/integration/config/test_chembl_enum_parity.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_chembl_enum_parity.py)
- [tests/integration/config/test_chembl_dq_catalog_sync.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_chembl_dq_catalog_sync.py)
- [tests/integration/config/test_chembl_observed_value_fixtures.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_chembl_observed_value_fixtures.py)
- [tests/integration/config/test_chembl_bronze_observed_value_inventory_snapshot.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/config/test_chembl_bronze_observed_value_inventory_snapshot.py)
- [tests/integration/normalization/test_chembl_edge_observed_values.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/integration/normalization/test_chembl_edge_observed_values.py)
- [tests/contract/test_chembl_enum_normalization_policy.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/contract/test_chembl_enum_normalization_policy.py)
- [tests/contract/test_chembl_ontology_bundle_policy.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/contract/test_chembl_ontology_bundle_policy.py)
- [tests/contract/test_chembl_derived_vocabulary_contracts.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/contract/test_chembl_derived_vocabulary_contracts.py)
- [tests/architecture/test_chembl_derived_vocabulary_policy.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/architecture/test_chembl_derived_vocabulary_policy.py)
- [tests/unit/application/core/test_chembl_normalization_hash_golden.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/application/core/test_chembl_normalization_hash_golden.py)
- [tests/unit/domain/hash_policy/test_chembl_high_risk_hash_golden.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/domain/hash_policy/test_chembl_high_risk_hash_golden.py)
- [tests/unit/scripts/qa/test_report_chembl_observed_value_inventory.py](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/tests/unit/scripts/qa/test_report_chembl_observed_value_inventory.py)
