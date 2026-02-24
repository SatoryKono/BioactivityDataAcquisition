# Отчёт: Анализ дублирования кода BioETL

**Дата**: 2026-02-24
**Ветка**: main

## Executive Summary

- Проанализировано: 25 transformer-модулей в `src/bioetl/application` (по паттерну `*transformer*.py`) и mixin/base-компоненты в `src/bioetl/infrastructure/adapters`.
- Обнаружено категорий потенциального дублирования: **2** (обе — низкий приоритет, P3/P4).
- Оценка потенциального сокращения: **~55-75 LOC** без изменения бизнес-семантики.
- Критических (MUST) нарушений архитектуры не обнаружено: дублирование локализовано в «шаблонном» glue-коде поверх уже существующих базовых классов.

## 1. Карты зависимостей

## Карта зависимостей для publication transformer constructors (`__init__` passthrough)

### Импортёры

- `src/bioetl/composition/factories/pipeline_factories.py`: импортирует все 4 publication transformers для регистрации пайплайнов.
- `src/bioetl/composition/factories/transformer_factory.py`: импортирует те же классы для DI-фабрики.
- `src/bioetl/application/pipelines/{openalex,crossref,pubmed,semanticscholar}/__init__.py`: re-export классов.

### Пользователи

- DI-регистрация через `transformer_class=...` в `pipeline_factories.py`.
- Архитектурные тесты сигнатур в `tests/architecture/test_transformer_signatures.py`.

### Тесты

- `tests/unit/application/pipelines/openalex/test_transformer.py`
- `tests/unit/application/pipelines/semanticscholar/test_transformer.py`
- `tests/unit/pipelines/pubmed/test_pubmed_transformer.py`
- `tests/integration/test_cross_provider_doi_normalization.py`
- `tests/architecture/test_transformer_signatures.py`

### Порядок миграции

1. Сначала обновить `BasePublicationTransformer` (ввести class-level defaults для provider/entity).
1. Затем упростить `__init__` в OpenAlex/CrossRef/S2 (PubMed оставить отдельным из-за stateful init).
1. Затем обновить архитектурные тесты сигнатур (если меняется конструктор).
1. Затем прогнать unit/integration тесты публикационных трансформеров.

______________________________________________________________________

## Карта зависимостей для selector-методов (`_get_primary_id_field`, `_get_entity_class`)

### Импортёры

- Непрямо используются через наследование в `BasePublicationTransformer._transform_impl()`.

### Пользователи

- `src/bioetl/application/pipelines/common/base_publication_transformer.py` вызывает оба selector-hook метода в общем потоке трансформации.

### Тесты

- `tests/unit/application/pipelines/common/test_base_publication_transformer.py`
- `tests/architecture/test_transformer_signatures.py`

### Порядок миграции

1. Ввести class attrs (например `PRIMARY_ID_FIELD`, `ENTITY_CLASS`) в `BasePublicationTransformer`.
1. Перевести 4 publication transformers на декларативные атрибуты.
1. Удалить однотипные hook-методы там, где это не ломает typing/mypy.
1. Прогнать unit-тесты base/publication и архитектурные проверки.

## 2. Верифицированные дублирования

### 2.1 Повторяющиеся passthrough-конструкторы в publication transformers

**Наблюдение:** в `OpenAlexPublicationTransformer`, `CrossRefPublicationTransformer`, `SemanticScholarPublicationTransformer` конструкторы практически идентичны: одинаковые параметры DI и прямой `super().__init__(...)` без добавления состояния.

**Доказательства (файлы):**

- `openalex/transformer.py` — `__init__` только проксирует параметры в `super()`.
- `crossref/transformer.py` — тот же паттерн.
- `semanticscholar/transformer.py` — тот же паттерн.
- Контрпример: `pubmed/transformer.py` после `super()` добавляет состояние (`_cached_xml_root`, extractors), поэтому это **не** дублирование.

**Оценка объёма:** ~18-24 LOC на класс × 3 класса = ~54-72 LOC.

**Рекомендуемый родительский объект:** расширить `BasePublicationTransformer` class-level defaults (`DEFAULT_PROVIDER`, `DEFAULT_ENTITY_TYPE`) и оставить возможность override через kwargs.

**Приоритет:** P3 (Informational).

______________________________________________________________________

### 2.2 Повторяющиеся selector-hook методы в publication transformers

**Наблюдение:** методы `_get_primary_id_field()` и `_get_entity_class()` в 4 publication transformers однотипны и часто являются константным `return`.

**Доказательства (файлы):**

- OpenAlex: `return "openalex_id"`, `return OpenAlexPublicationEntity`.
- CrossRef: `return "doi"`, `return CrossRefPublicationEntity`.
- PubMed: `return "pmid"`, `return PubMedPublicationEntity`.
- SemanticScholar: `return "paper_id"`, `return SemanticScholarPublicationEntity`.

**Оценка объёма:** ~4-6 LOC × 2 метода × 4 класса = ~32-48 LOC.

**Рекомендуемый родительский объект:** декларативная конфигурация в `BasePublicationTransformer` через class attrs:

- `PRIMARY_ID_FIELD: ClassVar[str]`
- `ENTITY_CLASS: ClassVar[type[BaseEntity]]`

**Приоритет:** P4 (низкий), так как выигрыш в LOC небольшой и текущая читаемость приемлемая.

## 3. Паттерны НЕ являющиеся дублированием

1. **`_extract_business_data()` в разных трансформерах** — валидный Template Method hook (provider-specific extraction).
1. **Большой `BaseTransformer`** не является признаком god object автоматически: это orchestration-ядро, а не business-логика провайдера.
1. **Health-check логика в адаптерах** уже централизована в `HealthCheckMixin`/`HealthCheckProviderMixin`; дополнительное «обобщение» здесь избыточно.
1. **PubMed `__init__`** отличается по семантике (локальный state + extractor instances), поэтому не должен быть механически слит с остальными.

## 4. Матрица приоритизации

| #   | Категория                                                     | Impact | Complexity                                  | LOC   | Приоритет |
| --- | ------------------------------------------------------------- | ------ | ------------------------------------------- | ----- | --------- |
| 1   | `__init__` passthrough в OpenAlex/CrossRef/S2                 | Низкий | Низкая/Средняя (влияние на signature tests) | 54-72 | P3        |
| 2   | Selector hooks (`_get_primary_id_field`, `_get_entity_class`) | Низкий | Низкая                                      | 32-48 | P4        |

## 5. Чеклист валидации

- [x] Инвентаризация transformer-файлов и base/mixin-иерархии.
- [x] Проверка повторяющихся hook/skeleton-паттернов.
- [x] Проверка зависимости через import/use/test search.
- [ ] `pytest tests/ -v` (не запускался полностью в рамках этого анализа).
- [ ] `mypy src/bioetl/ --strict` (не запускался полностью в рамках этого анализа).
- [ ] Coverage >80% (не пересчитывался в рамках этого анализа).

## 6. Verification Log (команды)

```bash
find src/bioetl/application -name '*transformer*.py' -exec wc -l {} + | sort -rn | head -30
rg "^class Base" src/bioetl | wc -l
rg "Mixin" src/bioetl --glob '*.py' | rg "class "
rg "^\s*def _[a-zA-Z0-9_]+" src/bioetl/application/pipelines -g '*.py' -o -r '$0' | sed -E 's/.*def /def /' | sort | uniq -c | sort -rn | head -40
rg "def _get_primary_id_field" src/bioetl/application/pipelines -n
rg "from bioetl\.application\.pipelines\.(openalex|crossref|semanticscholar|pubmed)\.transformer import|import bioetl\.application\.pipelines\.(openalex|crossref|semanticscholar|pubmed)\.transformer" src tests -n
uv run python -m pytest tests/architecture/test_transformer_signatures.py -q
```
