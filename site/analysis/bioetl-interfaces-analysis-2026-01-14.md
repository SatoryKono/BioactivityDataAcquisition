# Отчёт: Анализ интерфейсов пайплайнов и трансформеров BioETL

**Дата**: 2026-01-14
**Версия документации**: RULES.md v5.14
**Методология**: Протокол Двойной Верификации (CLAUDE.md §0)

---

## Резюме

Проведён систематический анализ интерфейсов всех пайплайнов и трансформеров BioETL.

**Ключевые выводы:**
- **Пайплайны (12)**: Полностью унифицированы, соответствуют DI-паттерну (REQ-ARCH-DI-007)
- **Трансформеры (18)**: Стандартизированная сигнатура с 8 параметрами
- **Критических расхождений**: 0
- **Минорных несоответствий**: 1 оставшееся (MINOR-002), 1 исправлено (MINOR-001)

**Общая оценка**: Архитектура интерфейсов **соответствует** требованиям RULES.md и ADR.

> **Обновление**: MINOR-001 исправлено в commit acfd4c8 (2026-01-14)

---

## 1. Верифицированные данные

### 1.1. Иерархия классов пайплайнов

```
BasePipeline (application/core/base.py:27) - 207 строк
└── GenericPipeline (application/pipelines/generic.py:33) - 74 строки
└── ChEMBLActivityPipeline (chembl/activity.py:17) - 25 строк
└── ChEMBLAssayPipeline (chembl/assay.py:17) - 25 строк
└── ChEMBLMoleculePipeline (chembl/molecule.py:17) - 25 строк
└── ChEMBLTargetPipeline (chembl/target.py:17) - 25 строк
└── PubChemCompoundPipeline (pubchem/compound.py:11) - 18 строк
└── UniProtProteinPipeline (uniprot/protein.py:11) - 18 строк
└── PubMedPublicationsPipeline (pubmed/publications.py:12) - 19 строк
└── [и другие - все идентичной структуры]
```

### 1.2. Иерархия классов трансформеров

```
BaseTransformer (application/core/base_transformer.py:64) - 674 строки
├── BaseChemblTransformer (chembl/base_chembl_transformer.py:34) - 184 строки
│   ├── ActivityTransformer (chembl/activity_transformer.py:144) - без __init__
│   ├── AssayTransformer (chembl/assay_transformer.py:147) - без __init__
│   ├── MoleculeTransformer (chembl/molecule_transformer.py:138) - без __init__
│   ├── TargetTransformer (chembl/target_transformer.py:25) - без __init__
│   ├── PublicationTransformer (chembl/publication_transformer.py:97) - с __init__
│   └── [+6 других ChEMBL трансформеров]
├── BasePublicationTransformer (common/base_publication_transformer.py:27) - 202 строки
│   ├── PubMedPublicationTransformer (pubmed/transformer.py:40) - с __init__
│   ├── CrossRefPublicationTransformer (crossref/transformer.py:42) - с __init__
│   ├── OpenAlexPublicationTransformer (openalex/transformer.py:44) - с __init__
│   └── SemanticScholarPublicationTransformer (semanticscholar/transformer.py:38) - с __init__
├── PubChemCompoundTransformer (pubchem/transformer.py:32) - с __init__
├── UniProtProteinTransformer (uniprot/transformer.py:42) - с __init__
└── IDMappingTransformer (uniprot/idmapping_transformer.py:31) - с __init__
```

### 1.3. Матрица сигнатур конструкторов пайплайнов

| Класс | Собственный `__init__` | Параметры `create()` | Наследует от |
|-------|------------------------|---------------------|--------------|
| **BasePipeline** | ✓ (66-103) | run_id, runtime, services, config, transformer | ABC |
| GenericPipeline | ❌ (наследует) | (наследует) | BasePipeline |
| ChEMBLActivityPipeline | ❌ (наследует) | (наследует) | BasePipeline |
| ChEMBLAssayPipeline | ❌ (наследует) | (наследует) | BasePipeline |
| ChEMBLMoleculePipeline | ❌ (наследует) | (наследует) | BasePipeline |
| ChEMBLTargetPipeline | ❌ (наследует) | (наследует) | BasePipeline |
| PubChemCompoundPipeline | ❌ (наследует) | (наследует) | BasePipeline |
| UniProtProteinPipeline | ❌ (наследует) | (наследует) | BasePipeline |
| PubMedPublicationsPipeline | ❌ (наследует) | (наследует) | BasePipeline |

**Вывод**: Все пайплайны используют унифицированную сигнатуру BasePipeline.

### 1.4. Матрица сигнатур конструкторов трансформеров

| Класс | provider | entity_type | tracer | metrics | gold_filters | identity_service | pii_hasher | data_normalizer |
|-------|----------|-------------|--------|---------|--------------|------------------|------------|-----------------|
| **BaseTransformer** | str | str\|None | ✓ None | ✓ None | ✓ None | ✓ None | ✓ None | ✓ None |
| BaseChemblTransformer | ="chembl" | =None | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BasePublicationTransformer | (наследует) | (наследует) | (наследует) | (наследует) | (наследует) | (наследует) | (наследует) | (наследует) |
| PubChemCompoundTransformer | ="pubchem" | ="compound" | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ → super |
| UniProtProteinTransformer | ="uniprot" | ="protein" | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ → super |
| PubMedPublicationTransformer | ="pubmed" | ="publication" | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ → self |
| CrossRefPublicationTransformer | ="crossref" | ="publication" | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ → self |
| OpenAlexPublicationTransformer | ="openalex" | ="publication" | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ → self |
| SemanticScholarPublicationTransformer | ="semanticscholar" | ="publication" | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ → self |

**Легенда:**
- `✓ None` — параметр присутствует, default=None
- `→ super` — передаётся в `super().__init__()`
- `→ self` — сохраняется в `self._data_normalizer` после вызова super()

---

## 2. Анализ по чеклистам

### 2.1. Чеклист DI-контракта (REQ-ARCH-DI-007)

| Проверка | Статус | Верификация |
|----------|--------|-------------|
| Трансформер НЕ создаётся внутри конструктора пайплайна | ✅ | `base.py:91-92` — `self._transformer = transformer` |
| Трансформер передаётся через параметр `transformer` | ✅ | `base.py:72` — `transformer: BaseTransformer \| None = None` |
| При отсутствии трансформера `transform_bronze_to_silver()` выбрасывает NotImplementedError | ✅ | `base.py:201-206` — явная проверка и raise |
| Нет `default_transformer_class` в BasePipeline | ✅ | `grep -n "default_transformer_class" base.py` → 0 результатов |
| Нет `Transformer()` вызовов в пайплайнах | ✅ | Архитектурный тест `test_no_transformer_fallback.py` |

**Результат**: Полное соответствие DI-контракту.

### 2.2. Чеклист Template Method паттерна

| Проверка | Статус | Верификация |
|----------|--------|-------------|
| `transform()` в BaseTransformer — финальный (не переопределяется) | ✅ | Архитектурный тест `test_does_not_override_transform` |
| `_transform_impl()` — абстрактный в BaseTransformer | ✅ | `base_transformer.py:264` — `@abstractmethod` |
| Все конкретные трансформеры реализуют `_transform_impl()` | ✅ | Архитектурный тест `test_implements_transform_impl` |
| TransformationError корректно обрабатывается | ✅ | `base_transformer.py:214-224` |

**Результат**: Корректная реализация Template Method.

### 2.3. Чеклист унификации параметров

| Параметр | BaseTransformer | Ожидание | Статус |
|----------|-----------------|----------|--------|
| provider | str (required) | Имя провайдера | ✅ |
| entity_type | str\|None = None | Для метрик | ✅ |
| tracer | TracingPort\|None = None | NoOpTracing default | ✅ |
| metrics | MetricsPort\|None = None | NoOpMetrics default | ✅ |
| gold_filters | GoldFilterConfig\|None = None | None default | ✅ |
| identity_service | IdentityService\|None = None | Новый экземпляр | ✅ |
| pii_hasher | PiiHasherPort\|None = None | NoOpPiiHasher default | ✅ |
| data_normalizer | DataNormalizationPort\|None = None | DataNormalizationService | ✅ |

---

## 3. Выявленные расхождения

### 3.1. [MINOR-001] ~~Несогласованная обработка `data_normalizer`~~ — ИСПРАВЛЕНО

**Статус**: ✅ RESOLVED (commit acfd4c8)

**Компоненты**: PubMedPublicationTransformer, CrossRefPublicationTransformer, OpenAlexPublicationTransformer, SemanticScholarPublicationTransformer, ChEMBL PublicationTransformer

**Тип**: Поведение
**Серьёзность**: Minor (P4) — **ИСПРАВЛЕНО**

**Файлы**:
- `pubmed/transformer.py:80-90`
- `crossref/transformer.py:81-90`
- `openalex/transformer.py:92-101`
- `semanticscholar/transformer.py:96-105`
- `chembl/publication_transformer.py:125-134`

**Текущее состояние**:
```python
# Группа 1: Передают data_normalizer в super().__init__()
# uniprot/transformer.py:105, pubchem/transformer.py:73, base_chembl_transformer.py:100
super().__init__(..., data_normalizer=data_normalizer)

# Группа 2: Создают self._data_normalizer ПОСЛЕ super().__init__()
# Не передают в super(), создают собственный атрибут
super().__init__(...) # без data_normalizer
self._data_normalizer = data_normalizer or DataNormalizationService()
```

**Ожидаемое состояние**:
```python
# Единообразно передавать в super().__init__()
super().__init__(..., data_normalizer=data_normalizer)
# И использовать self._data_normalizer из BaseTransformer
```

**Обоснование**:
- BaseTransformer имеет параметр `data_normalizer` (base_transformer.py:102)
- BaseTransformer создаёт `self._data_normalizer` (base_transformer.py:131-135)
- Publication transformers дублируют эту логику, создавая теневой атрибут

**Влияние**: Минимальное — оба подхода функционально эквивалентны. Но нарушает DRY и затрудняет рефакторинг.

**План исправления** (опционально):
1. Изменить publication transformers для передачи `data_normalizer` в super()
2. Удалить строки `self._data_normalizer = ...` после super()

**Тесты для проверки**:
- Существующие тесты достаточны (функциональность не затронута)

---

### 3.2. [MINOR-002] Различия в типе `entity_type`

**Компоненты**: BaseChemblTransformer vs остальные трансформеры

**Тип**: Сигнатура
**Серьёзность**: Minor (P4)

**Файлы**:
- `base_chembl_transformer.py:64` — `entity_type: str | None = None`
- `pubchem/transformer.py:43` — `entity_type: str = "compound"`

**Текущее состояние**:
```python
# BaseChemblTransformer — nullable с автовыводом из entity_class
entity_type: str | None = None

# Остальные transformers — обязательный default
entity_type: str = "compound"  # или "publication", "protein"
```

**Обоснование**:
- BaseChemblTransformer выводит entity_type из `entity_class.__name__.lower()` (строки 88-90)
- Это валидный паттерн для ChEMBL, где все трансформеры имеют entity_class
- Остальные провайдеры используют явные defaults

**Влияние**: Нулевое — архитектурный тест `test_entity_type_is_set` проверяет, что entity_type != "unknown" для всех трансформеров.

**Рекомендация**: Оставить как есть. Оба подхода валидны и покрыты тестами.

---

## 4. Существующие архитектурные тесты

| Файл | Покрытие |
|------|----------|
| `test_transformer_signatures.py` | 561 строк, 18 тестовых классов, ~50 параметризованных тестов |
| `test_no_transformer_fallback.py` | 203 строки, проверка DI-контракта |
| `test_base_pipeline_purity.py` | 63 строки, проверка чистоты BasePipeline |

**Покрытые аспекты**:
- Наследование от BaseTransformer
- Наличие обязательных параметров (provider, tracer, metrics, gold_filters, identity_service, pii_hasher)
- Defaults для параметров (None)
- Реализация `_transform_impl()`
- Запрет переопределения `transform()`
- Инстанцирование с defaults
- Наличие атрибутов `_tracer`, `_metrics`, `entity_type`, `provider`
- Методы `should_write_gold`, `transform_for_gold`, `compute_content_hash`, `compute_entity_id`
- PII hashing методы
- DI-контракт (no default_transformer_class)

---

## 5. Рекомендации

### 5.1. Не требуется действий

| Область | Обоснование |
|---------|-------------|
| Пайплайны | Полностью унифицированы |
| Базовые классы | Соответствуют контрактам |
| Template Method | Корректно реализован |
| DI-контракт | Соблюдается |

### 5.2. Выполненные улучшения

| ID | Задача | Статус | Commit |
|----|--------|--------|--------|
| MINOR-001 | Унифицировать обработку data_normalizer в publication transformers | ✅ DONE | acfd4c8 |

### 5.3. Оставшиеся (опционально)

MINOR-002 (различия в типе entity_type) — оставлено как есть, оба подхода валидны и покрыты тестами.

---

## 6. Выводы

1. **Архитектура интерфейсов соответствует требованиям**
   - REQ-ARCH-DI-007: ✅ Соблюдается
   - Template Method pattern: ✅ Корректно реализован
   - Унификация сигнатур: ✅ Достигнута

2. **Тестовое покрытие адекватно**
   - 3 файла архитектурных тестов
   - ~50 параметризованных тестов для трансформеров
   - Все ключевые контракты проверяются

3. **Расхождения**
   - Выявлено 2 минорных несоответствия (P4)
   - MINOR-001: ✅ Исправлено (commit acfd4c8)
   - MINOR-002: Оставлено (валидный паттерн)

---

## Приложение A: Команды верификации

```bash
# Проверка DI-контракта
grep -rn "Transformer()" src/bioetl/application/pipelines/*/[!_]*.py | grep -v "transformer.py"
# Ожидаемый результат: пусто

# Проверка сигнатур трансформеров
grep -A 15 "def __init__" src/bioetl/application/pipelines/*/*transformer*.py

# Запуск архитектурных тестов
pytest tests/architecture/test_transformer_signatures.py -v
pytest tests/architecture/test_no_transformer_fallback.py -v
pytest tests/architecture/test_base_pipeline_purity.py -v
```

---

*Документ сгенерирован автоматически на основе анализа кодовой базы.*
*Верификация: Протокол Двойной Верификации (CLAUDE.md §0)*
