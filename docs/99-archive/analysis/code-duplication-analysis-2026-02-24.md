# Отчёт: Анализ дублирования кода BioETL

**Дата**: 2026-02-24
**Ветка**: `main` (локальный анализ рабочего дерева)

## Executive Summary

- Проанализировано: трансформеры и адаптеры по слоям `application/` + `infrastructure/` с фокусом на повторяемые приватные методы и шаблоны валидации.
- Автоматический скрининг выявил повторяющиеся сигнатуры (`_extract_business_data`, `_transform_impl`, `__init__`) и mixin-иерархию, что в основном соответствует Template Method, а не copy-paste.
- Верифицировано **2 реальные категории минорного дублирования (P3/P4)**:
  1. локальная нормализация DOI в двух адаптерах, при наличии доменной функции нормализации;
  1. повтор валидации `entity_type in ("work", "publication")` внутри publication-адаптеров.
- Оценка потенциального сокращения: **~25–40 LOC** без изменения бизнес-поведения.
- Итог: архитектурно кодовая база остаётся консистентной; найденные дублирования — low-priority и безопасны для отложенного рефакторинга.

______________________________________________________________________

## 1. Карты зависимостей

### 1.1 Кандидат: унификация нормализации DOI в адаптерах публикаций

Целевой модуль (потенциальный): `bioetl.domain.normalization.normalize_doi`.

#### Импортёры

- `src/bioetl/infrastructure/adapters/crossref/client.py`: импортирует `normalize_doi`.
- `src/bioetl/infrastructure/adapters/crossref/batch.py`: импортирует `normalize_doi`.

#### Пользователи

- `src/bioetl/infrastructure/adapters/crossref/batch.py`: нормализация DOI перед batch-обработкой.
- `src/bioetl/infrastructure/adapters/openalex/client.py`: используется локальный `_normalize_doi()`.
- `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py`: используется локальный `_normalize_doi()`.

#### Тесты

- `tests/unit/domain/test_normalization.py`
- `tests/unit/domain/services/test_data_normalization_service.py`
- `tests/unit/infrastructure/adapters/openalex/test_adapter.py` (тесты staticmethod `_normalize_doi`)
- `tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py` (тесты `_normalize_doi`)

#### Re-exports

- Явных re-export для `normalize_doi` через `domain/__init__.py` не найдено в текущем анализе.

#### Порядок миграции

1. Обновить тесты OpenAlex/SemanticScholar на проверку поведения через доменную нормализацию (или через публичный метод, если helper удаляется).
1. Перевести `OpenAlexAdapter` на `domain.normalization.normalize_doi`.
1. Перевести `SemanticScholarAdapter` на тот же helper и сохранить специфику `DOI:` префикса в вызывающем коде.
1. Прогнать unit + architecture tests.

______________________________________________________________________

### 1.2 Кандидат: общая валидация `entity_type` для publication-adapters

Целевой модуль (потенциальный): небольшой helper в `infrastructure/adapters/common/` либо protected method в общем base для publication adapters.

#### Импортёры

- Прямых импортёров нет (логика инлайн в классах адаптеров).

#### Пользователи

- `src/bioetl/infrastructure/adapters/openalex/client.py` — повторяющаяся проверка в нескольких методах.
- `src/bioetl/infrastructure/adapters/crossref/client.py` — повторяющаяся проверка в нескольких методах.

#### Тесты

- `tests/unit/infrastructure/adapters/openalex/test_adapter.py` (invalid entity type)
- `tests/unit/infrastructure/adapters/crossref/test_client.py` (валидаторы entity type/ошибки)

#### Re-exports

- Не применимо.

#### Порядок миграции

1. Добавить helper-функцию `_validate_publication_entity_type(entity_type: str, provider: str) -> None`.
1. Покрыть helper unit-тестом.
1. Заменить дубли в OpenAlex/CrossRef.
1. Прогнать соответствующие adapter tests.

______________________________________________________________________

## 2. Верифицированные дублирования

## [Informational P3] Локальные реализации нормализации DOI при наличии доменного helper

**Локации**:

- `src/bioetl/infrastructure/adapters/openalex/client.py` — `OpenAlexAdapter._normalize_doi`.
- `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py` — `SemanticScholarAdapter._normalize_doi`.
- `src/bioetl/domain/normalization.py` — `normalize_doi` (уже существующий общий helper).

**Доказательство (факты):**

- В OpenAlex helper удаляет URL/prefix и допускает пустые значения.
- В SemanticScholar helper делает почти то же самое + отдельная ветка для `DOI:`.
- В домене уже есть `normalize_doi`, который используется CrossRef-адаптером.

**Impact:**

- Повышенная стоимость сопровождения: изменения правил нормализации нужно вносить минимум в 3 местах.
- Риск семантического дрейфа (разные edge-cases по регистру/пустым строкам).

**Recommendation:**

- Использовать `domain.normalization.normalize_doi` как единый источник истины.
- Сохранить provider-specific форматирование (`DOI:`) в вызывающем коде, не в helper.

**Verification commands:**

- `rg -n "def _normalize_doi|normalize_doi\(" src/bioetl/infrastructure/adapters/openalex/client.py src/bioetl/infrastructure/adapters/semanticscholar/adapter.py src/bioetl/domain/normalization.py src/bioetl/infrastructure/adapters/crossref/client.py src/bioetl/infrastructure/adapters/crossref/batch.py`
- `rg -n "normalize_doi\(" tests/unit/infrastructure/adapters/openalex/test_adapter.py tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py tests/unit/domain/test_normalization.py`

______________________________________________________________________

## [Informational P3] Повтор валидации `entity_type` в publication-адаптерах

**Локации**:

- `src/bioetl/infrastructure/adapters/openalex/client.py` — одинаковый guard в нескольких методах.
- `src/bioetl/infrastructure/adapters/crossref/client.py` — аналогичный guard в нескольких методах.

**Доказательство (факты):**

- Повторяется условие `if entity_type not in ("work", "publication"):` с provider-specific текстом ошибки.

**Impact:**

- Лёгкое функциональное дублирование (правило одно и то же).
- Небольшой риск расхождения error messages и будущих supported types.

**Recommendation:**

- Вынести guard в helper/mixin уровня infrastructure.
- Оставить provider name параметром для сообщений об ошибках.

**Verification command:**

- `rg -n "entity_type not in \(\"work\", \"publication\"\)|supports 'work' or 'publication'" src/bioetl/infrastructure/adapters/openalex/client.py src/bioetl/infrastructure/adapters/crossref/client.py`

______________________________________________________________________

## 3. Паттерны, НЕ являющиеся дублированием

1. `_extract_business_data()` в ChEMBL-трансформерах — ожидаемая вариативность hook-метода Template Method.
1. `_transform_impl()` в конкретных transformer-классах — это часть контракта `BaseTransformer`, а не copy-paste.
1. Схожие `__init__`/`__post_init__` в адаптерах с `super()` и метриками — инфраструктурный стандарт инициализации.
1. Наличие крупных базовых классов само по себе не является нарушением: по текущему анализу `base_transformer.py` содержит существенное делегирование через `self._*` методы.

______________________________________________________________________

## 4. Матрица приоритизации

| #   | Категория                                                 | Impact         | Complexity                                | LOC    | Приоритет              |
| --- | --------------------------------------------------------- | -------------- | ----------------------------------------- | ------ | ---------------------- |
| 1   | DOI normalization helper unification                      | Низкий/средний | Низкая                                    | ~15-20 | P3                     |
| 2   | entity_type validation guard unification                  | Низкий         | Низкая                                    | ~10-20 | P3                     |
| 3   | Header builders (`_build_headers`) в publication adapters | Низкий         | Средняя (разные semantics/API key/mailto) | ~0-10  | P4 (оставить как есть) |

______________________________________________________________________

## 5. Чеклист валидации

- [ ] `uv run python -m pytest tests/ -v --tb=short`
- [ ] `uv run python -m mypy --strict src/bioetl/`
- [ ] Coverage >80% (CI)

> Для данного задания выполнен аналитический аудит без изменения runtime-кода; полный прогон всего набора тестов и mypy рекомендуется запускать в CI перед реализацией рефакторинга.

______________________________________________________________________

## 6. Лог выполненных команд (аудит)

```bash
find src/bioetl/application -name "*transformer*.py" -exec wc -l {} + | sort -rn | head -20
rg "class Base" src/bioetl | wc -l
rg -c "self\._" src/bioetl/application/core/base_transformer.py
grep -h "def _" src/bioetl/application/pipelines/*/*.py | sort | uniq -c | sort -rn | head -30
rg "class .*Mixin" src/bioetl --glob '*.py'
rg -n "def _normalize_doi|normalize_doi\(" src/bioetl/infrastructure/adapters/openalex/client.py src/bioetl/infrastructure/adapters/semanticscholar/adapter.py src/bioetl/domain/normalization.py src/bioetl/infrastructure/adapters/crossref/client.py src/bioetl/infrastructure/adapters/crossref/batch.py
rg -n "entity_type not in \(\"work\", \"publication\"\)|supports 'work' or 'publication'" src/bioetl/infrastructure/adapters/openalex/client.py src/bioetl/infrastructure/adapters/crossref/client.py
rg -n "normalize_doi\(" tests/unit/infrastructure/adapters/openalex/test_adapter.py tests/unit/infrastructure/adapters/semanticscholar/test_adapter.py tests/unit/domain/test_normalization.py
```
