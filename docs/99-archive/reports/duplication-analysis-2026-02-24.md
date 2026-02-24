# Отчёт: Анализ дублирования кода BioETL

**Дата**: 2026-02-24
**Ветка**: main (локальный HEAD)

## Executive Summary

- Проанализировано: `546` Python-модулей в `src/bioetl` (domain:190, application:133, infrastructure:138, composition:54, interfaces:29).
- Углублённо проверено: трансформеры `application/pipelines/*`, базовые трансформеры `application/core/*`, адаптеры DOI-нормализации в `infrastructure/adapters/*`.
- Найдено категорий потенциального дублирования: **3**.
- Из них:
  - **P2 (умеренно полезно)**: 1 категория (константные override-методы в publication-transformers).
  - **P3/P4 (низкий ROI)**: 2 категории (pass-through `__init__`, локальные DOI-normalize helper-методы с разной семантикой).
- Оценка потенциального сокращения: ~35–70 LOC без изменения поведения.
- Вывод: архитектура уже использует Template Method / base classes; крупного структурного дублирования, требующего немедленного выноса в новые parent objects, не обнаружено.

______________________________________________________________________

## 1. Карты зависимостей

### 1.1 Кандидат A — константные методы `_get_primary_id_field()` / `_get_entity_class()`

#### Карта зависимостей для `BasePublicationTransformer`

**Импортёры**

- `src/bioetl/application/pipelines/openalex/transformer.py`: `from bioetl.application.pipelines.common import BasePublicationTransformer`
- `src/bioetl/application/pipelines/semanticscholar/transformer.py`: `from bioetl.application.pipelines.common import BasePublicationTransformer`
- `src/bioetl/application/pipelines/crossref/transformer.py`: `from bioetl.application.pipelines.common import BasePublicationTransformer`
- `src/bioetl/application/pipelines/pubmed/transformer.py`: `from bioetl.application.pipelines.common import BasePublicationTransformer`

**Пользователи**

- `src/bioetl/application/pipelines/common/base_publication_transformer.py:202`: использование `_get_primary_id_field()` в общей transform-flow.
- `src/bioetl/application/pipelines/common/base_publication_transformer.py:235`: использование `_get_entity_class()` для `_create_entity()`.

**Тесты**

- `tests/unit/application/pipelines/common/test_base_publication_transformer.py`: тесты контрактов `_get_primary_id_field` и `_get_entity_class`.
- Интеграционные и unit-тесты провайдеров publication-трансформеров (`openalex`, `crossref`, `pubmed`, `semanticscholar`) через вызовы `transform()`.

**Порядок миграции (если делать рефакторинг)**

1. Добавить в `BasePublicationTransformer` class attributes:
   - `PRIMARY_ID_FIELD: ClassVar[str]`
   - `ENTITY_CLASS: ClassVar[type[BaseEntity]]`
1. Временный backward-compatible bridge: методы `_get_primary_id_field`/`_get_entity_class` оставить как fallback, читающий class attrs.
1. Перевести 4 publication-transformer на class attrs.
1. Обновить `test_base_publication_transformer.py` и провайдерные тесты.
1. Удалить deprecated методы после переходного периода.

______________________________________________________________________

### 1.2 Кандидат B — повторяемые pass-through `__init__` в наследниках `BaseTransformer`

#### Карта зависимостей для `BaseTransformer.__init__`

**Импортёры / наследники с похожими `__init__`**

- `src/bioetl/application/pipelines/openalex/transformer.py`
- `src/bioetl/application/pipelines/semanticscholar/transformer.py`
- `src/bioetl/application/pipelines/crossref/transformer.py`
- `src/bioetl/application/pipelines/pubmed/transformer.py`
- `src/bioetl/application/pipelines/pubchem/transformer.py`
- `src/bioetl/application/pipelines/uniprot/transformer.py`
- `src/bioetl/application/pipelines/uniprot/idmapping_transformer.py`
- `src/bioetl/application/pipelines/chembl/publication_transformer.py`

**Пользователи**

- Все pipeline factories / DI wiring, создающие transformer через конструктор.

**Тесты**

- Unit/integration-тесты трансформеров, где конструкторы вызываются напрямую с дефолтами или частичными DI аргументами.

**Порядок миграции (если делать рефакторинг)**

1. Ввести единый builder/factory helper в `composition` (без изменения сигнатур публичных классов).
1. Перевести фабрики на helper.
1. Оставить текущие `__init__` как API-compat слой.

______________________________________________________________________

### 1.3 Кандидат C — `_normalize_doi` helper-методы в OpenAlex/SemanticScholar adapters

#### Карта зависимостей для DOI normalization helpers

**Импортёры**

- Внутренние статические методы:
  - `OpenAlexAdapter._normalize_doi`
  - `SemanticScholarAdapter._normalize_doi`

**Пользователи**

- Внутри соответствующих adapter batch/search методов при подготовке DOI ID-list.

**Тесты**

- Интеграционные тесты cross-provider DOI normalization.

**Порядок миграции (если делать рефакторинг)**

1. Сравнить требуемую семантику нормализации по провайдерам (case-sensitive vs case-insensitive, пустые строки).
1. Если семантика совпадает — вынести в `infrastructure/adapters/common/doi.py`.
1. Иначе оставить как-is и задокументировать намеренное расхождение.

______________________________________________________________________

## 2. Верифицированные дублирования

### 2.1 [P2] Константные override-методы в publication transformers

**Наблюдение**

- Во всех 4 publication transformers повторяется однотипный шаблон:
  - `_get_primary_id_field()` → `return <constant>`
  - `_get_entity_class()` → `return <EntityClass>`

**Файлы (пример)**

- `openalex/transformer.py` — `return "openalex_id"`, `return OpenAlexPublicationEntity`
- `semanticscholar/transformer.py` — `return "paper_id"`, `return SemanticScholarPublicationEntity`
- `crossref/transformer.py` — `return "doi"`, `return CrossRefPublicationEntity`
- `pubmed/transformer.py` — `return "pmid"`, `return PubMedPublicationEntity`

**Почему это дублирование**

- Повторяется идентичная структурная логика (константные методы без дополнительного поведения).
- Используется в единой Template Method-цепочке базового класса.

**Рекомендация**

- Перейти на class attributes в `BasePublicationTransformer` с backward-compatible fallback.
- Ожидаемый выигрыш: ~20–30 LOC + меньше boilerplate при добавлении нового publication provider.

**Риск**: низкий (при сохранении совместимости).

______________________________________________________________________

### 2.2 [P3] Pass-through `__init__` в трансформерах

**Наблюдение**

- В нескольких наследниках `BaseTransformer` конструктор дублирует сигнатуру и почти полностью делегирует в `super().__init__(...)`.

**Автоматическая проверка similarity**

- `OpenAlexPublicationTransformer.__init__` ↔ `CrossRefPublicationTransformer.__init__`: ~0.94
- `OpenAlexPublicationTransformer.__init__` ↔ `SemanticScholarPublicationTransformer.__init__`: ~0.90
- Аналогичные значения для `PubMed`, `UniProt`, `PubChem`.

**Почему это НЕ критично**

- Текущая форма улучшает discoverability DI-параметров в конкретных классах.
- Переход на новый parent object может ухудшить явность API и потребует широких изменений тестов/фабрик.

**Рекомендация**

- Считать допустимым шаблонным повтором (Template inheritance boilerplate).
- Опционально сократить через фабрики/builder в `composition`, не ломая public constructors.

______________________________________________________________________

### 2.3 [P4] `_normalize_doi` в adapter-слое

**Наблюдение**

- Есть похожие методы `_normalize_doi` в `openalex/client.py` и `semanticscholar/adapter.py`.

**Почему не выносить автоматически**

- Семантика различается (обработка `None`, регистра, набор префиксов, возвращаемый тип).
- В domain уже есть `normalize_doi()`, но он выполняет другую задачу (общая нормализация строки), не полностью заменяет adapter-specific preprocessing.

**Рекомендация**

- Оставить как-is, либо сначала унифицировать контракт adapter-level DOI preprocessing.

______________________________________________________________________

## 3. Паттерны, НЕ являющиеся дублированием

1. `_extract_business_data()` в разных трансформерах — provider-specific логика, корректный hook Template Method.
1. Наличие больших base-файлов (`BaseTransformer`, `BatchExecutor`) само по себе не признак god object; требуется проверка делегирования/ответственностей.
1. Provider-specific pre-validation (например, обязательный DOI в CrossRef) — корректная вариативность, не дублирование.

______________________________________________________________________

## 4. Матрица приоритизации

| #   | Категория                                               | Impact     | Complexity | LOC    | Приоритет |
| --- | ------------------------------------------------------- | ---------- | ---------- | ------ | --------- |
| 1   | Константные `_get_primary_id_field`/`_get_entity_class` | Medium     | Low        | ~20-30 | **P2**    |
| 2   | Pass-through `__init__` в наследниках BaseTransformer   | Low-Medium | Medium     | ~15-25 | **P3**    |
| 3   | `_normalize_doi` helper в adapter-слое                  | Low        | Medium     | ~10-15 | **P4**    |

______________________________________________________________________

## 5. Чеклист валидации

- [ ] `uv run python -m pytest tests/ -v --tb=short` (не запускался: анализ без изменения runtime-кода)
- [ ] `uv run python -m mypy --strict src/bioetl/` (не запускался: анализ без изменения typing/runtime-кода)
- [ ] Coverage >80% (не пересчитывался в рамках документального аудита)

______________________________________________________________________

## 6. Verification Log (команды)

```bash
# Инвентаризация структуры
python - <<'PY'
from pathlib import Path
root=Path('src/bioetl')
for layer in ['domain','application','infrastructure','composition','interfaces']:
    print(layer, sum(1 for _ in (root/layer).rglob('*.py')))
print('total', sum(1 for _ in root.rglob('*.py')))
PY

# Размеры transformer-файлов
find src/bioetl/application -name '*transformer*.py' -exec wc -l {} + | sort -rn | head -30

# Количество base classes и mixins
rg -n '^class Base' src/bioetl | wc -l
rg -n 'class .*Mixin' src/bioetl --glob '*.py'

# Поиск потенциальных дубликатов методов publication-transformers
rg -n '_get_primary_id_field|_get_entity_class' src tests --glob '*.py'

# Similarity check для одноимённых методов (внутренний AST + difflib скрипт)
python - <<'PY'
# (скрипт из анализа)
PY
```
