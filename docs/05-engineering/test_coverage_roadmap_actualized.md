# Test Coverage Roadmap - Актуализированный план на основе текущего кода

## Текущее состояние P0 модулей

### Domain Aggregates (цель: ≥95%)

| Модуль | Текущее coverage | Цель | Gap | Приоритет |
|--------|-----------------|------|-----|----------|
| _batch_aggregate | 48.4% (15/31) | 95% | -46.6% | P0 |
| _batch_lifecycle | 43.3% (13/30) | 95% | -51.7% | P0 |
| _batch_mixins | 61.6% (61/99) | 95% | -33.4% | P0 |
| _batch_record | 75% (15/20) | 95% | -20% | P0 |
| _batch_status | 93.75% (15/16) | 95% | -1.25% | P0 |
| _pipeline_run_mixins | 31.1% (19/61) | 95% | -63.9% | P0 |
| _pipeline_run_read_model_mixin | 66.2% (49/74) | 95% | -28.8% | P0 |
| _quarantine_aggregate | 37.8% (14/37) | 95% | -57.2% | P0 |
| _quarantine_entry_properties_mixin | 72.6% (45/62) | 95% | -22.4% | P0 |
| _quarantine_entry_transitions_mixin | 42.6% (20/47) | 95% | -52.4% | P0 |
| _quarantine_value_objects | 77.8% (28/36) | 95% | -17.2% | P0 |
| batch.py | 100% (5/5) | 95% | +5% | P0 ✓ |
| events.py | 95.1% (77/81) | 95% | +0.1% | P0 ✓ |
| pipeline_run.py | 67.7% (21/31) | 95% | -27.3% | P0 |
| pipeline_run_stage_result | 57.5% (23/40) | 95% | -37.5% | P0 |
| pipeline_run_state | 94.1% (16/17) | 95% | -0.9% | P0 |
| quarantine_entry.py | 100% (4/4) | 95% | +5% | P0 ✓ |

**Среднее coverage:** ~65%
**Наибольшие gaps:** _pipeline_run_mixins (-63.9%), _quarantine_aggregate (-57.2%), _batch_lifecycle (-51.7%)

### Domain Contracts/Gold (цель: ≥95%)

| Модуль | Текущее coverage | Цель | Gap | Приоритет |
|--------|-----------------|------|-----|----------|
| _base | 100% (3/3) | 95% | +5% | P0 ✓ |
| _chembl_activity_assay_schemas | 100% (139/139) | 95% | +5% | P0 ✓ |
| _chembl_molecule_protein_schemas | 100% (73/73) | 95% | +5% | P0 ✓ |
| _chembl_molecule_target_schemas | 100% (4/4) | 95% | +5% | P0 ✓ |
| _chembl_reference_publication_schemas | 100% (77/77) | 95% | +5% | P0 ✓ |
| _chembl_target_lookup_schemas | 100% (88/88) | 95% | +5% | P0 ✓ |
| _composite_gold_common_schema | 100% (18/18) | 95% | +5% | P0 ✓ |
| _publication_common_schema | 100%* (50/50) | 95% | +5% | P0 ✓ |
| _strict_gold_contract_schema | 100% (10/10) | 95% | +5% | P0 ✓ |
| chembl.py | 100% (5/5) | 95% | +5% | P0 ✓ |
| composite.py | 100% (5/5) | 95% | +5% | P0 ✓ |
| composite_bioassay.py | 100% (29/29) | 95% | +5% | P0 ✓ |
| composite_molecule.py | 100% (11/11) | 95% | +5% | P0 ✓ |
| composite_publication.py | 100% (12/12) | 95% | +5% | P0 ✓ |
| pubchem.py | 100% (42/42) | 95% | +5% | P0 ✓ |
| publications.py | 100% (6/6) | 95% | +5% | P0 ✓ |
| publications_crossref.py | 100% (33/33) | 95% | +5% | P0 ✓ |
| publications_openalex.py | 100% (33/33) | 95% | +5% | P0 ✓ |
| publications_pubmed.py | 100% (46/46) | 95% | +5% | P0 ✓ |
| publications_semanticscholar.py | 100% (33/33) | 95% | +5% | P0 ✓ |
| uniprot.py | 100% (117/117) | 95% | +5% | P0 ✓ |

**Среднее coverage:** ~99%
**Статус:** Code/test scope завершён. Все gold contracts достигли целевого порога; `*` означает локальную line-trace verification на 2026-06-03, пока committed inventory ждёт следующего healthy canonical coverage lane.

### Composition Public APIs (цель: ≥90%)

| Модуль | Текущее coverage | Цель | Gap | Приоритет |
|--------|-----------------|------|-----|----------|
| control_plane_api | 0% (0/19) | 90% | -90% | P0 |
| execution_api | 0% (0/23) | 90% | -90% | P0 |
| health_api | 0% (0/35) | 90% | -90% | P0 |
| maintenance_api | 0% (0/24) | 90% | -90% | P0 |
| registry_api | 93.3% (14/15) | 90% | +3.3% | P0 ✓ |
| resources_api | 0% (0/16) | 90% | -90% | P0 |
| services_api | 0% (0/12) | 90% | -90% | P0 |
| _pipeline_execution | 0% (0/84) | 90% | -90% | P0 |

**Среднее coverage:** ~12%
**Статус:** КРИТИЧНО! Большинство public APIs вообще не покрыты тестами.

---

## Актуализированный приоритетный план

### Фаза 1: Критические Public APIs (P0 - немедленно)

**Причина:** 0% coverage для public composition APIs - критический риск

**Модули:**
1. execution_api.py (0/23)
2. control_plane_api.py (0/19)
3. health_api.py (0/35)
4. maintenance_api.py (0/24)
5. resources_api.py (0/16)
6. _pipeline_execution.py (0/84)

**Действия:**
- Создать unit тесты для public API contracts
- Тестировать lazy exports, routing, dependency wiring
- Mock downstream dependencies (ledger, checkpoint store)
- Цель: достичь 90% coverage

**Ожидаемый эффект:** Покрытие critical public bootstrap surface

### Фаза 2: Domain Aggregates - Lifecycle & State (P0)

**Причина:** Наибольшие gaps в business-critical domain logic

**Модули (по убыванию gap):**
1. _pipeline_run_mixins (31.1% → 95%, gap: -63.9%)
2. _quarantine_aggregate (37.8% → 95%, gap: -57.2%)
3. _batch_lifecycle (43.3% → 95%, gap: -51.7%)
4. _quarantine_entry_transitions_mixin (42.6% → 95%, gap: -52.4%)
5. _pipeline_run_stage_result (57.5% → 95%, gap: -37.5%)
6. _pipeline_run (67.7% → 95%, gap: -27.3%)
7. _pipeline_run_read_model_mixin (66.2% → 95%, gap: -28.8%)

**Действия:**
- test_pipeline_run_lifecycle.py: start/complete/fail/shutdown, terminal mutation lock
- test_pipeline_run_events.py: доменные события и их payload
- test_quarantine_entry_invariants.py: payload immutability, status transitions
- test_batch_lifecycle.py: OPEN → SEALED → WRITING → COMMITTED, OPEN → SEALED → FAILED
- test_batch_determinism.py: hash determinism, index sequencing, replay stability

**Ожидаемый эффект:** Meaningful domain coverage, снижение риска ложного покрытия

### Фаза 3: Domain Aggregates - Remaining (P0)

**Модули:**
1. _quarantine_entry_properties_mixin (72.6% → 95%, gap: -22.4%)
2. _quarantine_value_objects (77.8% → 95%, gap: -17.2%)
3. _batch_record (75% → 95%, gap: -20%)
4. _batch_mixins (61.6% → 95%, gap: -33.4%)
5. _batch_aggregate (48.4% → 95%, gap: -46.6%)

**Действия:**
- Добавить тесты для uncovered путей в существующих тестовых файлах
- Или создать специализированные тесты для сложных сценариев

**Ожидаемый эффект:** Достижение 95% для всех domain aggregates

### Фаза 4: Domain Contracts/Gold - Final Polish (P0) ✓

**Модуль:**
1. _publication_common_schema (100%* (50/50), gap closed)

**Действия:**
- Расширить `tests/unit/domain/contracts/gold/test_publication_common_schema.py`
- Закрыть taxonomy edge cases, alias/value constraints и fallback branch при пустой taxonomy

**Ожидаемый эффект:** Достигнуто 95%+ для всех gold contracts

---

## Конкретные новые тестовые файлы (актуализировано)

### Фаза 1: Public APIs
1. tests/unit/composition/test_execution_api_contract.py
2. tests/unit/composition/test_control_plane_api_contract.py
3. tests/unit/composition/test_health_api_contract.py
4. tests/unit/composition/test_maintenance_api_contract.py
5. tests/unit/composition/test_resources_api_contract.py
6. tests/unit/composition/test_services_api_contract.py
7. tests/unit/composition/test_pipeline_execution_contract.py

### Фаза 2: Lifecycle & State
1. tests/unit/domain/aggregates/test_pipeline_run_lifecycle.py
2. tests/unit/domain/aggregates/test_pipeline_run_events.py
3. tests/unit/domain/aggregates/test_quarantine_entry_invariants.py
4. tests/unit/domain/aggregates/test_batch_lifecycle.py
5. tests/unit/domain/aggregates/test_batch_determinism.py

### Фаза 3: Remaining Aggregates
- Расширить существующие test files или добавить специализированные тесты

### Фаза 4: Gold Polish
- Расширить tests/unit/domain/contracts/gold/test_publication_common_schema.py

---

## Критерий завершения

Для каждого фазы:
1. Создать тестовые файлы согласно плану
2. Запустить coverage-verify lane
3. Обновить module-coverage-inventory.json
4. Проверить, что coverage >= target для всех модулей фазы

**Итоговая цель:**
- Global line coverage >= 85%
- Global branch coverage >= 80%
- Domain aggregates >= 95%
- Domain contracts/gold >= 95%
- Public composition APIs >= 90%
