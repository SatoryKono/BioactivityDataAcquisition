# Testing Report

**Дата**: 2026-01-06
**RULES.md**: v5.9
**Stage**: 3/5 (Production Release Preparation)

## Сводка тестов

Все категории тестов прошли успешно. Skipped тесты имеют явное обоснование.

| Категория | Всего | Passed | Failed | Skipped | Время |
|-----------|-------|--------|--------|---------|-------|
| Unit | 4384 | 4384 | 0 | 0 | 69.47s |
| Integration | 216 | 212 | 0 | 4 | 23.25s |
| Architecture | 395 | 394 | 0 | 1 | 34.67s |
| Contract | 30 | 0 | 0 | 30 | 0.18s |
| E2E | 180 | 180 | 0 | 0 | 38.26s |
| Smoke | 17 | 17 | 0 | 0 | 3.52s |
| **Итого** | **5222** | **5187** | **0** | **35** | **~284s** |

### Причины пропуска тестов (Skipped)

| Категория | Количество | Причина |
|-----------|------------|---------|
| Integration | 4 | VCR cassette not yet recorded (UniProt ID Mapping) |
| Architecture | 1 | No allowed files in composition layer (expected) |
| Contract | 30 | Live API tests disabled (BIOETL_LIVE_API_TESTS=false) |

## Покрытие кода

**Total Coverage: 89.77%** ✓ (Требуется ≥80%)

### Покрытие по слоям

| Слой | Файлов | Покрытие | Статус |
|------|--------|----------|--------|
| domain/ | 40+ | ~95% | ✓ |
| application/ | 60+ | ~88% | ✓ |
| infrastructure/ | 80+ | ~87% | ✓ |
| interfaces/ | 20+ | ~98% | ✓ |

### Модули с покрытием ниже 80% (требуют внимания)

| Модуль | Coverage | Комментарий |
|--------|----------|-------------|
| `infrastructure/adapters/pubchem/client.py` | 54.72% | PubChem sync adapter, редко используется |
| `infrastructure/adapters/pubchem/fetch_strategies.py` | 44.35% | Альтернативные стратегии |
| `infrastructure/adapters/input/csv_filter_reader.py` | 47.47% | Опциональный CSV input |
| `infrastructure/adapters/pubmed/pubmed_client.py` | 59.39% | XML parsing edge cases |
| `application/core/filtered_data_source.py` | 57.33% | Filter-based data source |
| `application/core/idmapping_data_source.py` | 17.24% | UniProt ID mapping (недокументированное API) |
| `application/core/batch_executor.py` | 70.00% | Batch execution edge cases |
| `application/core/executor.py` | 0.00% | Deprecated, подлежит удалению |
| `application/core/protocols.py` | 0.00% | Protocol definitions (no runtime code) |
| `interfaces/cli/__main__.py` | 0.00% | Entry point only |

### Критичные модули (domain/) - все ≥80%

| Модуль | Coverage |
|--------|----------|
| domain/services/activity_aggregator.py | 85.11% |
| domain/services/normalization_service.py | 89.84% |
| domain/transformations.py | 96.64% |
| domain/value_objects/activity.py | 95.24% |
| domain/value_objects/identifiers.py | 97.50% |

## VCR кассеты

- **Всего кассет**: 80 (79 в tests/fixtures/vcr/ + 1 в vcr_cassettes/)
- **Старше 90 дней**: 0 ✓
- **Требуют обновления**: Нет

### Провайдеры с VCR кассетами

| Провайдер | Кассет |
|-----------|--------|
| ChEMBL | 35+ |
| UniProt | 8 |
| PubChem | 6 |
| PubMed | 6 |
| OpenAlex | 10+ |
| SemanticScholar | 5+ |
| Crossref | 5+ |

## Smoke-тест пайплайна

```bash
$ python -m bioetl run --pipeline chembl_activity --dry-run --limit 10
```

**Результат**: SUCCESS ✓

```json
{"run_id": "36e104e8-0700-4b26-ba6b-e2370bcc03cf", "pipeline": "chembl_activity", "run_type": "incremental", "dry_run": true, "limit": 10, "stage": "init", "event": "Starting pipeline run"}
{"run_id": "36e104e8-0700-4b26-ba6b-e2370bcc03cf", "pipeline": "chembl_activity", "stage": "init", "event": "Dry-run mode: no execution performed"}
Dry-run completed (no changes made)
```

## Тестовые fixtures

| Директория | Файлов | Статус |
|------------|--------|--------|
| tests/fixtures/vcr/ | 79 | ✓ Актуальны |
| tests/fixtures/vcr_cassettes/ | 1 | ✓ Актуальна |
| tests/fixtures/input/ | 2 | ✓ Актуальны |

## Блокеры релиза

**Нет блокеров** ✓

Все критические требования выполнены:
- [x] Coverage ≥80% (достигнуто 89.77%)
- [x] Unit тесты без сетевых вызовов (4384 passed)
- [x] Integration тесты с VCR кассетами (212 passed)
- [x] Architecture тесты прошли (394 passed)
- [x] E2E тесты прошли (180 passed)
- [x] Smoke-тест успешен
- [x] VCR кассеты актуальны (0 старше 90 дней)

## Рекомендации

### Низкий приоритет (не блокеры)

1. **Увеличить покрытие PubChem адаптеров** (~55%)
   - Модули используются редко, но стоит добавить тесты для основных сценариев

2. **Записать VCR кассеты для UniProt ID Mapping**
   - 4 теста пропущены из-за отсутствия кассет
   - Команда: `pytest tests/integration/adapters/test_uniprot_idmapping.py --vcr-record=new_episodes`

3. **Удалить deprecated модуль executor.py**
   - 0% покрытия, помечен как deprecated

4. **Рассмотреть удаление Contract тестов из CI**
   - 30 тестов всегда skipped в CI (требуют Live API)
   - Альтернатива: отдельный CI job для contract testing

## Версия тестового окружения

```
pytest==9.0.2
pytest-asyncio==1.3.0
pytest-cov==7.0.0
pytest-vcr==1.0.2
pytest-xdist==3.8.0
hypothesis==6.149.1
Python==3.11.14
```

---

*Отчёт сгенерирован автоматически 2026-01-06*
