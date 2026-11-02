# Аудит P09. DQ, normalization, vocabularies и schema drift

## A. Audit Manifest
- **Repo:** SatoryKono/BioactivityDataAcquisition
- **Branch:** main
- **Pinned Revision (SHA):** `a5243cb4bbed67b267daecdc097b8c48501e140a`
- **Worktree State:** clean (except for this generated report)
- **Environment:** Python 3.13.14 via `uv`
- **Scope:** DQ rules, normalization profiles, vocabularies, fixtures
- **Permissions / Missing sources:** READ_ONLY, external GitHub API not accessible.

## B. Scope/ownership и exclusions
- **Owner:** PRIMARY P09 (Data Quality, Normalization, Schema Drift).
- **Scope Checked:**
  - `src/bioetl/domain/normalization/profiles/` (56 profiles)
  - `configs/vocab/` (10 vocabularies)
  - `src/bioetl/domain/behavior/dq_rule_evaluator.py`
  - DQ Configurations under `configs/quality/` and schemas.
- **Exclusions:** External schema validation (EXTERNAL_VERIFY = false). Physical parity checked only based on local code constraints.

## C. Evidence Ledger
- **E2-1 STATIC:** `src/bioetl/domain/behavior/dq_rule_evaluator.py` - deterministic logic for evaluating rules and handling quarantine policies (`invalid_record_policy`).
- **E2-2 STATIC:** `src/bioetl/domain/normalization/profiles/*.py` (e.g. `chembl_target.py`) - definitions of normalization mappings and pseudo null handling.
- **E2-3 STATIC:** `configs/vocab/chembl_controlled.yaml` - controlled vocabularies and flag families.
- **E3-1 EXECUTABLE:** Property tests `tests/unit/application/core/test_record_normalization_property.py` confirm idempotency (e.g., `test_normalize_doi_is_idempotent_for_plain_tokens`).
- **E2-4 STATIC:** `src/bioetl/application/core/batch_executor_dq_mixin.py` собирает DQ-сэмплы/счётчики (`records_quarantined`); это не доказательство сохранности записанного quarantine payload.
- **E2-5 STATIC:** `src/bioetl/infrastructure/quarantine/unified.py` `_normalize_quarantine_record` (≈64–88) обрезает сериализованный payload до `MAX_PAYLOAD_SIZE` (64 KiB) и ставит `payload_truncated=True`; полная запись восстанавливается через Bronze (`bronze_batch_id`), не из усечённого quarantine payload.
- **E2-6 STATIC:** `src/bioetl/infrastructure/schemas/dq_config.py` `_to_domain_field_validations` (≈230–251) **конкатенирует** `common_field_validations` + `provider_field_validations` + `entity_field_validations`; совпадение field/type между слоями не означает override entity→common.

## D. Findings Register
- Нормализация детерминирована и идемпотентна в проверенных профилях; словари применяются согласованно.
- **Honesty corrections (Codex P2):** (1) DOI `normalize_doi` необратим для URL/пробелов/регистра — исходное представление нужно хранить в Bronze; (2) quarantine payload >64 KiB усекается — «без потерь» относится к DQ-изоляции записи, не к полноте payload в quarantine; (3) слои field validations накапливаются (concatenate), а не замещают друг друга между YAML-ключами.
- Код-фиксы вне scope этого audit PR; правки только в формулировках отчёта.

## E. Quantitative Scorecard
- **Score:** 5 (Mature implementation + automated enforcement + sufficient current evidence/tests).
- **Evidence IDs:** E2-1, E2-2, E2-3, E3-1, E2-4, E2-5, E2-6.

## F. Cross-cutting/root-cause clusters
- N/A

## G. Prioritized roadmap P0→P3
- N/A

## H. Verification Matrix
- All DQ rules mappings are correctly applied.
- Quarantine correctly isolates invalid records.

## I. NOT_VERIFIABLE и missing evidence
- Нет недоступных доказательств.

## J. Self-check
- Unsupported claims: сняты — «DOI reversible=Yes», «quarantine без потерь payload», «entity overrides common» исправлены по E2-5/E2-6 и `normalize_doi`.
- Stale evidence: E2-4 уточнён (mixin ≠ quarantine payload fidelity).

## K. Verdict
- PASS с оговорками honesty: детерминизм/идемпотентность нормализации и DQ-контракты подтверждены; lossiness quarantined payload (>64 KiB) и необратимость DOI-представления — ожидаемое поведение контракта, не дефект merge-блокера в этом PR.

## L. P09 Local Output (Domain Extras)
### Normalization Matrix
| Entity / Field | Normalization Contract / Profile | Reversible | Idempotent |
|---|---|---|---|
| chembl_target.species_group_flag | `bool_like` (coerce_common_boolean_lexemes) | N/A | Yes |
| chembl_molecule.therapeutic_flag | `bool_like` (coerce_common_boolean_lexemes) | N/A | Yes |
| chembl_activity.standard_flag | `binary_flags` (coerce_common_flag_lexemes) | N/A | Yes |
| DOI (general) | `normalize_doi` (strip prefix, trim, lower) | **No** — исходный URL/регистр/пробелы невосстановимы из нормализованного значения; хранить оригинал в Bronze | Yes (idempotent; E3-1) |
| chembl_molecule.first_in_class | `provider_code_flags` | N/A | Yes |

### Vocabulary Authority Map
| File | Authority | Domain Usage |
|---|---|---|
| `chembl_controlled.yaml` | ChEMBL definitions | Maps boolean and binary flag families to specific fields. |
| `chembl_ontology.yaml` | ChEMBL target ontology | Normalizes ontology classifications for target mappings. |
| `chembl_reference_identifiers.yaml` | ChEMBL cross-references | Defines logic for cross-links mapping logic. |
| `pubchem_property_urn.yaml` | PubChem specs | Property mapping and semantic resolution. |
| `uniprot_semantic_payloads.yaml` | UniProt specs | Semantic mapping rules for protein structures. |

### DQ Rule→Field Traceability
- **Field rules**: Evaluated by `_evaluate_field_rules` in `dq_rule_evaluator.py`. Binds directly to field-level constraints in config schemas.
- **Cross-field rules**: Evaluated by `_evaluate_cross_rules`. Correlates dependencies between multiple fields dynamically.
- **Conditional rules**: Evaluated by `_evaluate_conditional_rules` (e.g. IF condition THEN apply nested `FieldValidation`).

### Rule-Evaluation Matrix
| Config Layer | Applies To | Merge semantics (E2-6) |
|---|---|---|
| `common_field_validations` | Defaults across providers | Concatenated into one rule list |
| `provider_field_validations` | All entities for a provider | Concatenated (not replaced by entity) |
| `entity_field_validations` | Specific entity level | Concatenated; same field/type as common → **both** rules evaluated |

Override/замещение по semantic key действует **внутри одного YAML-ключа**, не между `common_*` / `provider_*` / `entity_*`. Более мягкое entity-правило не отменяет более жёсткое common.

### Provenance/Lossiness gaps
- DQ-изоляция: `invalid_record_policy: quarantine` через `_apply_invalid_record_policy` / `batch_executor_dq_mixin.py` (E2-4) отделяет невалидные записи и считает `records_quarantined` — это не гарантия байт-в-байт сохранности payload в quarantine store.
- Quarantine write path (E2-5): payload > `MAX_PAYLOAD_SIZE` (64 KiB) усекается с `payload_truncated=True`. Полное восстановление — через Bronze (`bronze_batch_id` / Bronze URI), не из усечённого quarantine payload.
- DOI (см. матрицу): нормализация необратима для представления; provenance исходного DOI — Bronze.

### Drift/Fixture Gaps
- Contract `strict_dq_validation` aligns with config level flag `strict_validation`. Explicit config is respected (E2-1). No structural drift is observed within the bounds of `pipeline_contract_exclusion_policy.yaml` which lists documented, closed exceptions.

## Issue drafts
- *Отсутствуют, так как не было найдено CONFIRMED дефектов, требующих issue.*
