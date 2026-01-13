# Отчёт: Анализ интерфейсов пайплайнов BioETL

**Дата**: 2026-01-13
**Версия документации**: RULES.md v5.10
**Протокол**: Двойная верификация (CLAUDE.md §0)

---

## Резюме

| Метрика | Значение |
|---------|----------|
| Всего пайплайнов | 19 |
| Всего трансформеров | 18 |
| Выявлено расхождений | 1 |
| - Critical (P0) | 0 |
| - Major (P1) | 0 |
| - Minor (P3) | 1 |

**Вывод**: Архитектура интерфейсов соответствует DI-контракту (REQ-ARCH-DI-007). Выявлено одно незначительное расхождение в сигнатурах трансформеров, не влияющее на функциональность.

---

## Фаза 1: Верифицированные данные

### 1.1. Иерархия пайплайнов

```
BasePipeline (application/core/base.py:27)
├── GenericPipeline (application/pipelines/generic.py:33)
└── [19 provider-specific pipelines - пустые shell-классы]
    ├── ChEMBLActivityPipeline
    ├── ChEMBLAssayPipeline
    ├── ChEMBLMoleculePipeline
    ├── ... (12 ChEMBL)
    ├── PubChemCompoundPipeline
    ├── UniProtProteinPipeline
    ├── PubMedPublicationsPipeline
    ├── CrossRefPipeline (через GenericPipeline)
    ├── OpenAlexPipeline (через GenericPipeline)
    └── SemanticScholarPipeline (через GenericPipeline)
```

### 1.2. Иерархия трансформеров

```
BaseTransformer (application/core/base_transformer.py:63)
├── BaseChemblTransformer (application/pipelines/chembl/base_chembl_transformer.py:29)
│   ├── ActivityTransformer
│   ├── AssayTransformer
│   ├── AssayParametersTransformer
│   ├── CellLineTransformer
│   ├── CompoundRecordTransformer
│   ├── DocumentTransformer (+data_normalizer)
│   ├── DocumentSimilarityTransformer
│   ├── DocumentTermTransformer
│   ├── MoleculeTransformer
│   ├── ProteinClassTransformer
│   ├── TargetTransformer
│   └── TargetComponentTransformer
├── BasePublicationTransformer (application/pipelines/common/base_publication_transformer.py:27)
│   ├── PubMedPublicationTransformer (+data_normalizer)
│   ├── CrossRefPublicationTransformer (+data_normalizer)
│   ├── OpenAlexPublicationTransformer (+data_normalizer)
│   └── SemanticScholarPublicationTransformer (+data_normalizer)
├── UniProtProteinTransformer
├── PubChemCompoundTransformer
└── IDMappingTransformer
```

---

## Фаза 2: Матрицы сигнатур

### 2.1. Сигнатуры конструкторов пайплайнов

| Класс | Параметры `__init__` | Источник |
|-------|---------------------|----------|
| **BasePipeline** | `config, runtime, services, run_id, transformer=None` | `base.py:66-96` |
| GenericPipeline | Наследует от BasePipeline | `generic.py:33` |
| ChEMBLActivityPipeline | Наследует от BasePipeline | `activity.py:17` |
| ... (все остальные) | Наследует от BasePipeline | — |

**Вывод**: Все пайплайны используют единую сигнатуру из BasePipeline. Расхождений нет.

### 2.2. Сигнатуры конструкторов трансформеров

#### Стандартные параметры BaseTransformer (`base_transformer.py:92-126`)

| Параметр | Тип | Default |
|----------|-----|---------|
| `provider` | `str` | (required) |
| `entity_type` | `str \| None` | `None` |
| `tracer` | `TracingPort \| None` | `None` |
| `metrics` | `MetricsPort \| None` | `None` |
| `gold_filters` | `GoldFilterConfig \| None` | `None` |
| `identity_service` | `IdentityService \| None` | `None` |
| `pii_hasher` | `PiiHasherPort \| None` | `None` |

#### Матрица параметров трансформеров

| Трансформер | provider default | entity_type default | +data_normalizer |
|-------------|------------------|---------------------|------------------|
| **BaseChemblTransformer** | `"chembl"` | `None` (from entity_class) | ✗ |
| ActivityTransformer | Наследует | Наследует | ✗ |
| AssayTransformer | Наследует | Наследует | ✗ |
| MoleculeTransformer | Наследует | Наследует | ✗ |
| TargetTransformer | Наследует | Наследует | ✗ |
| **DocumentTransformer** | Наследует | Наследует | **✓** (line 104) |
| ... (7 остальных ChEMBL) | Наследует | Наследует | ✗ |
| **BasePublicationTransformer** | (нет своего `__init__`) | — | — |
| **PubMedPublicationTransformer** | `"pubmed"` | `"publication"` | **✓** (line 65) |
| **CrossRefPublicationTransformer** | `"crossref"` | `"publication"` | **✓** (line 66) |
| **OpenAlexPublicationTransformer** | `"openalex"` | `"publication"` | **✓** (line 77) |
| **SemanticScholarPublicationTransformer** | `"semanticscholar"` | `"publication"` | **✓** (line 80) |
| UniProtProteinTransformer | `"uniprot"` | `"protein"` | ✗ |
| PubChemCompoundTransformer | `"pubchem"` | `"compound"` | ✗ |
| IDMappingTransformer | `"uniprot"` | `"idmapping"` | ✗ |

---

## Фаза 3: Анализ расхождений

### 3.1. DI-контракт (REQ-ARCH-DI-007) — ВЫПОЛНЕН

**Проверка 1**: BasePipeline не создаёт трансформеры внутри

```python
# base.py:91-92
# Transformer MUST be injected via DI - no fallback creation
self._transformer = transformer
```

**Верификация**: `grep -n "Transformer()" src/bioetl/application/core/base.py` → 0 matches

**Проверка 2**: Пайплайны не имеют `default_transformer_class`

**Верификация**: `grep -rn "default_transformer_class" src/bioetl/application/pipelines/` → 0 matches

**Проверка 3**: Фабрики передают transformer через DI

```python
# pipeline_factory.py:411-420
if transformer_class is not None:
    transformer = transformer_class(
        provider=provider,
        entity_type=_extract_entity_type(pipeline_name),
        tracer=tracer,
        metrics=metrics,
        gold_filters=domain_config.gold_filters,
    )
```

**Вывод**: ✅ DI-контракт полностью соблюдён.

### 3.2. Template Method Pattern — ВЫПОЛНЕН

**Проверка**: Трансформеры не переопределяют `transform()`

**Верификация**: Архитектурный тест `test_transformer_signatures.py:259-276` проверяет это.

**Вывод**: ✅ Template Method корректно реализован.

### 3.3. Расхождение: параметр `data_normalizer`

#### Описание

5 трансформеров имеют дополнительный параметр `data_normalizer: DataNormalizationPort | None = None`, отсутствующий в базовых классах:

| Файл | Строка |
|------|--------|
| `chembl/document_transformer.py` | 104 |
| `pubmed/transformer.py` | 65 |
| `crossref/transformer.py` | 66 |
| `openalex/transformer.py` | 77 |
| `semanticscholar/transformer.py` | 80 |

#### Поведение

```python
# Все 5 трансформеров:
self._data_normalizer = data_normalizer or DataNormalizationService()
```

#### Использование в фабриках

```python
# pipeline_factory.py:411-420 - НЕ передаёт data_normalizer
transformer = transformer_class(
    provider=provider,
    entity_type=...,
    tracer=tracer,
    metrics=metrics,
    gold_filters=...,
    # data_normalizer НЕ передаётся!
)
```

#### Анализ влияния

| Аспект | Оценка |
|--------|--------|
| **Функциональность** | ✅ Не нарушена — default работает корректно |
| **Тестируемость** | ✅ Параметр позволяет мокировать в тестах |
| **Консистентность** | ⚠️ Нарушена — 5 из 18 трансформеров отличаются |
| **DI-паттерн** | ⚠️ Partial — параметр есть, но не используется в production |

#### Причина существования параметра

`DataNormalizationService` используется для:
- Нормализации DOI (lowercase, strip)
- Удаления HTML-тегов из abstract
- Парсинга авторов в list

Параметр нужен для **тестируемости** — возможность подставить mock в unit-тестах.

---

## Фаза 4: Выявленные расхождения

### [P3-001] data_normalizer не унифицирован в BaseTransformer

**Компоненты**: DocumentTransformer, PubMedPublicationTransformer, CrossRefPublicationTransformer, OpenAlexPublicationTransformer, SemanticScholarPublicationTransformer

**Тип**: Сигнатура

**Серьёзность**: Minor (P3)

**Файлы**:
- `application/pipelines/chembl/document_transformer.py:104`
- `application/pipelines/pubmed/transformer.py:65`
- `application/pipelines/crossref/transformer.py:66`
- `application/pipelines/openalex/transformer.py:77`
- `application/pipelines/semanticscholar/transformer.py:80`

**Текущее состояние**:
```python
# 5 трансформеров имеют дополнительный параметр
def __init__(
    self,
    provider: str = "...",
    ...  # стандартные 6 параметров
    data_normalizer: DataNormalizationPort | None = None,  # +1
) -> None:
    super().__init__(...)
    self._data_normalizer = data_normalizer or DataNormalizationService()
```

**Ожидаемое состояние (Вариант A — статус-кво)**:
```python
# Текущее поведение приемлемо:
# - Параметр обеспечивает тестируемость
# - Default DataNormalizationService() корректен
# - Фабрики не обязаны передавать этот параметр
```

**Ожидаемое состояние (Вариант B — унификация)**:
```python
# BaseTransformer:
def __init__(
    self,
    provider: str,
    entity_type: str | None = None,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    gold_filters: GoldFilterConfig | None = None,
    identity_service: IdentityService | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,  # NEW
) -> None:
    ...
    self._data_normalizer = data_normalizer or DataNormalizationService()
```

**Рекомендация**: **Вариант A (статус-кво)**

Обоснование:
1. Не все трансформеры нуждаются в нормализации текста
2. ChEMBL-трансформеры (кроме DocumentTransformer) работают со структурированными данными
3. Добавление параметра в BaseTransformer увеличит сложность без пользы

---

## Фаза 5: План выравнивания

### Приоритизация

| ID | Задача | Приоритет | Статус |
|----|--------|-----------|--------|
| P3-001 | data_normalizer inconsistency | P3 Minor | Рекомендуется оставить как есть |

### Рекомендации

1. **Не требуется изменений** — текущая архитектура корректна
2. **Документировать** паттерн в CLAUDE.md §2.3 (уже частично сделано)
3. **Добавить тест** в `test_transformer_signatures.py` для проверки data_normalizer у publication-трансформеров (опционально)

---

## Архитектурные тесты

Существующие тесты покрывают контракты интерфейсов:

| Тест | Файл | Проверяет |
|------|------|-----------|
| `test_inherits_from_base_transformer` | `test_transformer_signatures.py:108` | Наследование от BaseTransformer |
| `test_has_provider_parameter` | `test_transformer_signatures.py:127` | Наличие provider |
| `test_has_tracer_parameter` | `test_transformer_signatures.py:157` | Наличие tracer |
| `test_has_metrics_parameter` | `test_transformer_signatures.py:172` | Наличие metrics |
| `test_has_gold_filters_parameter` | `test_transformer_signatures.py:187` | Наличие gold_filters |
| `test_has_identity_service_parameter` | `test_transformer_signatures.py:201` | Наличие identity_service |
| `test_has_pii_hasher_parameter` | `test_transformer_signatures.py:215` | Наличие pii_hasher |
| `test_implements_transform_impl` | `test_transformer_signatures.py:235` | Реализация _transform_impl |
| `test_does_not_override_transform` | `test_transformer_signatures.py:259` | Не переопределяет transform() |
| `test_no_default_transformer_class_in_basepipeline` | `test_no_transformer_fallback.py:35` | REQ-ARCH-DI-007 |

---

## Чек-лист верификации

- [x] Все команды Фазы 1 выполнены
- [x] Матрицы Фазы 2 заполнены полностью
- [x] DI-контракт (REQ-ARCH-DI-007) проверен
- [x] Template Method паттерн проверен
- [x] Расхождения документированы по шаблону
- [x] План приоритизирован
- [x] Рекомендации сформулированы

---

## Связанные документы

- `RULES.md` v5.10, §2.2 (Dependency Injection)
- `CLAUDE.md` §0 (Протокол Двойной Верификации)
- `ADR-020` BasePipeline Decomposition
- `tests/architecture/test_transformer_signatures.py`
- `tests/architecture/test_no_transformer_fallback.py`

---

**END OF REPORT**
