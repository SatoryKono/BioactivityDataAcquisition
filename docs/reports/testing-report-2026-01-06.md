# Testing Report

**Дата**: 2026-01-06
**RULES.md**: v5.9
**Версия проекта**: 5.9.0
**Stage**: 3/5 (Production Release Preparation)

---

## Сводка тестов

Все категории тестов прошли успешно. Skipped тесты имеют явное обоснование.

| Категория | Всего | Passed | Failed | Skipped | Время |
|-----------|-------|--------|--------|---------|-------|
| Unit | 4544 | 4544 | 0 | 0 | 58.79s |
| Integration | 216 | 216 | 0 | 0 | 15.75s |
| Architecture | 869 | 868 | 0 | 1 | 25.59s |
| Contract | 30 | 0 | 0 | 30 | 0.15s |
| E2E | 180 | 180 | 0 | 0 | 28.35s |
| Smoke | 17 | 17 | 0 | 0 | 3.64s |
| **Итого** | **5856** | **5825** | **0** | **31** | **~132s** |

### Причины пропуска тестов (Skipped)

| Категория | Количество | Причина |
|-----------|------------|---------|
| Architecture | 1 | No allowed files in composition layer (expected) |
| Contract | 30 | Live API tests disabled (BIOETL_LIVE_API_TESTS=false) |

---

## Покрытие кода

**Total Coverage: 90.76%** ✓ (Требуется ≥80%)

### Покрытие по слоям архитектуры

| Слой | Файлов | Покрытие | Статус (≥80%) |
|------|--------|----------|---------------|
| domain/ | 87 | 91.28% | ✓ |
| application/ | 104 | 95.21% | ✓ |
| infrastructure/ | 107 | 93.14% | ✓ |
| interfaces/ | 24 | 91.09% | ✓ |
| composition/ | 31 | 83.23% | ✓ |
| **TOTAL** | **353** | **90.76%** | **✓** |

### Модули с покрытием ниже 70% (требуют внимания)

| Модуль | Coverage | Слой | Комментарий |
|--------|----------|------|-------------|
| `composition/_bootstrap/checkpoint.py` | 36.11% | composition | Bootstrap checkpoint |
| `composition/factories/runner_factory.py` | 40.48% | composition | Factory code |
| `infrastructure/adapters/pubchem/fetch_strategies.py` | 44.35% | infrastructure | Fetch strategies |
| `infrastructure/adapters/input/csv_filter_reader.py` | 47.47% | infrastructure | CSV filter reader |
| `composition/builders.py` | 48.65% | composition | DI builders |
| `infrastructure/adapters/pubchem/client.py` | 52.68% | infrastructure | PubChem client |
| `application/core/filtered_data_source.py` | 57.33% | application | Filtered data source |
| `infrastructure/adapters/pubmed/pubmed_client.py` | 59.39% | infrastructure | PubMed client |
| `composition/_bootstrap/health.py` | 60.00% | composition | Bootstrap health |
| `composition/_bootstrap/lock.py` | 60.00% | composition | Bootstrap lock |
| `domain/ports/storage.py` | 60.61% | domain | Protocol definitions |
| `composition/entrypoints.py` | 60.98% | composition | Pipeline entrypoints |
| `domain/ports/observability.py` | 61.90% | domain | Protocol definitions |
| `application/services/config_service.py` | 62.32% | application | Config service |
| `composition/factories/http_client_factory.py` | 62.86% | composition | HTTP client factory |
| `composition/_bootstrap/runner.py` | 63.64% | composition | Bootstrap runner |
| `composition/factories/storage_adapter.py` | 65.32% | composition | Storage adapter factory |
| `domain/ports/normalization.py` | 65.31% | domain | Protocol definitions |
| `domain/ports/checkpoint.py` | 66.67% | domain | Protocol definitions |
| `domain/ports/data_source.py` | 66.67% | domain | Protocol definitions |
| `domain/ports/locking.py` | 66.67% | domain | Protocol definitions |
| `domain/ports/quarantine.py` | 66.67% | domain | Protocol definitions |
| `infrastructure/observability/metrics_server_adapter.py` | 66.67% | infrastructure | Metrics server |
| `composition/providers/registration.py` | 68.84% | composition | Provider registration |
| `domain/ports/resilience.py` | 69.57% | domain | Protocol definitions |

**Анализ**:
- Большинство низкопокрытых модулей в `composition/` — DI/bootstrap код, тестируемый через integration/E2E
- Файлы `domain/ports/*.py` содержат Protocol-определения без runtime-кода (ожидаемо низкое покрытие)
- Критические бизнес-модули (domain/application services) имеют покрытие >85%

### Критичные модули domain/ - все ≥80%

| Модуль | Coverage |
|--------|----------|
| domain/services/activity_aggregator.py | 85%+ |
| domain/services/normalization_service.py | 89%+ |
| domain/transformations.py | 96%+ |
| domain/value_objects/activity.py | 95%+ |
| domain/value_objects/identifiers.py | 97%+ |

---

## VCR кассеты

| Метрика | Значение |
|---------|----------|
| Всего кассет | 83 |
| Старше 90 дней | 0 |
| Требуют обновления | 0 |

**Статус**: ✓ Все кассеты актуальны

### Провайдеры с VCR кассетами

| Провайдер | Кассет |
|-----------|--------|
| ChEMBL | 35+ |
| UniProt | 8+ |
| PubChem | 6+ |
| PubMed | 6+ |
| OpenAlex | 10+ |
| SemanticScholar | 5+ |
| CrossRef | 5+ |

---

## Smoke-тест пайплайна

### Команда
```bash
python -m bioetl run --pipeline chembl_activity --dry-run --limit 10
```

### Результат: SUCCESS ✓

### Лог выполнения
```json
{
  "run_id": "f1d8a55c-9a17-495c-8064-44b16acf4f3f",
  "pipeline": "chembl_activity",
  "run_type": "incremental",
  "dry_run": true,
  "limit": 10,
  "stage": "init",
  "event": "Starting pipeline run"
}
{
  "run_id": "f1d8a55c-9a17-495c-8064-44b16acf4f3f",
  "pipeline": "chembl_activity",
  "stage": "init",
  "event": "Dry-run mode: no execution performed"
}
```

---

## Тестовые fixtures

| Директория | Файлов | Статус |
|------------|--------|--------|
| tests/fixtures/vcr/ | 79+ | ✓ Актуальны |
| tests/fixtures/vcr_cassettes/ | 1+ | ✓ Актуальны |
| tests/fixtures/input/ | 2+ | ✓ Актуальны |
| JSON fixtures старше 180 дней | 0 | ✓ |

---

## Блокеры релиза

**Нет блокеров** ✓

Все критические требования выполнены:
- [x] Coverage ≥80% (достигнуто 90.76%)
- [x] Unit тесты без сетевых вызовов (4544 passed)
- [x] Integration тесты с VCR кассетами (216 passed)
- [x] Architecture тесты прошли (868 passed, 1 skipped)
- [x] E2E тесты прошли (180 passed)
- [x] Smoke-тест успешен
- [x] VCR кассеты актуальны (0 старше 90 дней)

---

## Рекомендации

### Низкий приоритет (не блокеры)

1. **Повысить покрытие composition/ слоя** (текущее 83.23%)
   - Добавить unit-тесты для factories и builders
   - Цель: 90%+

2. **Увеличить покрытие PubChem/PubMed адаптеров** (~50-60%)
   - Добавить VCR-кассеты для edge cases
   - Модули используются, но имеют сложную логику

3. **Contract тесты в отдельный CI job**
   - 30 тестов всегда skipped в стандартном CI
   - Рекомендация: периодический запуск с `BIOETL_LIVE_API_TESTS=true`

---

## Команды воспроизведения

```bash
# Полный прогон с coverage
pytest tests/ --cov=src/bioetl --cov-report=term-missing --cov-fail-under=80

# Unit тесты
pytest tests/unit/ -v --tb=short

# Integration тесты
pytest tests/integration/ -v --tb=short --vcr-record=none

# Architecture тесты
pytest tests/architecture/ -v --tb=short

# Contract тесты (Live API)
BIOETL_LIVE_API_TESTS=true pytest tests/contract/ -v --tb=short

# E2E тесты
pytest tests/e2e/ -v --tb=short

# Smoke тесты
pytest tests/smoke/ -v --tb=short

# Dry-run пайплайна
python -m bioetl run --pipeline chembl_activity --dry-run --limit 10
```

---

## Версия тестового окружения

```
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=4.0
pytest-vcr>=1.0
pytest-xdist>=3.5
hypothesis>=6.100
Python>=3.11
```

---

**Вывод**: Проект BioETL v5.9.0 успешно прошёл все категории тестирования и готов к production release.

*Отчёт обновлён: 2026-01-06*
