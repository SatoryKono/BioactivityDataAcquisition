# Аудит структуры пакетов src/bioetl

**Дата:** 2026-02-07
**Версия кодовой базы:** main (HEAD)
**Автор:** Claude Code (automated audit)

---

## Общие метрики проекта

| Метрика | Значение |
|---------|----------|
| Всего Python-файлов | 510 |
| Из них `__init__.py` | 79 |
| Содержательных модулей (без `__init__`) | 431 |
| Всего каталогов | 83 |
| Общий LOC | 113 840 |

### LOC и файлы по слоям

| Слой | Файлов (без `__init__`) | LOC | % от LOC |
|------|------------------------|-----|----------|
| domain | 149 | 36 156 | 31.8% |
| application | 121 | 32 625 | 28.7% |
| infrastructure | 99 | 31 401 | 27.6% |
| composition | 38 | 10 474 | 9.2% |
| interfaces | 23 | 3 171 | 2.8% |
| root (\_\_init\_\_, \_\_main\_\_) | 1 | 13 | <0.1% |

---

## Этап 1: Поиск дублирующих модулей

### 1.1 Подтверждённое дублирование

| Модуль-источник | Модуль-дубликат | Совпадение | Рекомендация |
|-----------------|-----------------|------------|--------------|
| `domain/ports/noop.py:379` — `NoOpMetadataWriter` | `infrastructure/storage/metadata_writer.py:241` — `NoOpMetadataWriter` | ~95% | **Удалить** копию в infrastructure; импортировать из `domain.ports.noop` или вынести в composition |

Обе реализации `NoOpMetadataWriter` почти идентичны: те же методы, те же no-op возвраты. Разница — в docstring (infrastructure-версия не содержит комментарий "All operations are silently ignored").

**Действие:** Удалить класс из `infrastructure/storage/metadata_writer.py`, обновить импорты на `from bioetl.domain.ports.noop import NoOpMetadataWriter`.

### 1.2 Re-export модули (backward compatibility)

| Файл | LOC | Что реэкспортирует | Рекомендация |
|------|-----|--------------------|--------------|
| `application/services/dq_metrics_calculator.py` | 16 | `DQMetricsCalculator` из `domain/services/` | DEPRECATE — добавить warning, удалить через 2 релиза |
| `composition/factories/storage.py` | 35 | Функции из split-модулей | KEEP — документированный backward-compat |
| `application/core/shutdown.py` | ~30 | `ShutdownService` из `application/services/` | DEPRECATE — обновить импорты |

### 1.3 NoOp-реализации (НЕ дубликаты)

Три группы NoOp-классов существуют на разных слоях для разных целей:

- `domain/ports/noop.py` (470 LOC) — Null Object implementations на уровне домена
- `infrastructure/observability/noop_*.py` (3 файла, ~200 LOC) — конкретные NoOp с предупреждениями
- `composition/bootstrap/cli/noop.py` (109 LOC) — фабрики NoOp для CLI bootstrap

**Вердикт:** Архитектурно обоснованное разделение. **Исключение EXC-003** (Null Object Pattern).

### 1.4 Одноимённые файлы

| Имя файла | Кол-во файлов | Дублирование? |
|-----------|---------------|---------------|
| `base.py` | 9 | Нет — базовые классы для разных доменов |
| `publication.py` | 8 | Нет — провайдер-специфичные реализации |
| `client.py` | 6 | Нет — адаптеры для разных API |
| `transformer.py` | 6 | Нет — трансформеры для разных сущностей |
| `config.py` | 5 | Нет — конфиги для разных подсистем |
| `models.py` | 5 | Нет — модели для разных контекстов |
| `validation.py` | 4 | Нет — валидация (функции / исключения / адаптер / порт) |

**Вердикт:** Одноимённые файлы НЕ являются дубликатами — каждый работает в своём архитектурном контексте.

---

## Этап 2: Файлы с пересекающейся ответственностью

### 2.1 Анализ крупных файлов (500+ LOC)

Проанализировано **18 файлов** от 709 до 1698 строк.

| Файл | LOC | Вердикт | Делегирование |
|------|-----|---------|---------------|
| `application/composite/merger.py` | 1698 | PROPER DELEGATION | 4+ компонента |
| `infrastructure/storage/silver_writer.py` | 1151 | PROPER DELEGATION | 5+ компонентов |
| `infrastructure/adapters/chembl/client.py` | 1098 | PROPER DELEGATION | 4+ компонента |
| `infrastructure/schemas/pipeline_config.py` | 1093 | PROPER DELEGATION | Единственная ответственность: валидация конфигов |
| `application/composite/runner.py` | 1074 | PROPER DELEGATION | 7+ компонентов |
| `infrastructure/schemas/silver.py` | 1003 | PROPER DELEGATION | Единственная ответственность: схемы |
| `domain/composite/config.py` | 978 | PROPER DELEGATION | Единственная ответственность: dataclasses |
| `infrastructure/storage/gold_writer.py` | 934 | PROPER DELEGATION | 4+ компонента |
| `application/core/preflight_service.py` | 816 | PROPER DELEGATION | Вспомогательные внутренние классы |
| `application/core/base_transformer.py` | 786 | PROPER DELEGATION | 5+ компонентов |
| `application/core/batch_executor.py` | 783 | PROPER DELEGATION | 4+ компонента |
| `domain/models/metadata.py` | 777 | PROPER DELEGATION | Единственная ответственность: модели |
| `composition/entrypoints.py` | 771 | **NEEDS SPLITTING** | 4 категории энтрипоинтов |
| `infrastructure/adapters/openalex/client.py` | 770 | PROPER DELEGATION | 4+ компонента |
| **`application/services/dq/gold_analyzer.py`** | **761** | **GOD MODULE** | **8 разных типов DQ-проверок, минимальное делегирование** |
| `domain/contracts/gold/chembl.py` | 758 | PROPER DELEGATION | Единственная ответственность: схемы |
| `composition/providers/registration.py` | 715 | **NEEDS SPLITTING** | 7 провайдеров в одном файле |
| `application/pipelines/semanticscholar/extractors.py` | 709 | **NEEDS SPLITTING** | 20+ функций извлечения |

### 2.2 God Module: `gold_analyzer.py`

**Файл:** `src/bioetl/application/services/dq/gold_analyzer.py` (761 LOC)

**8 разных ответственностей в одном классе `GoldDQAnalyzer`:**

1. Проверка количества записей (record count checks)
2. Проверка полноты (completeness checks)
3. Бизнес-правила (business rules validation)
4. Ссылочная целостность (referential integrity)
5. Статистическое профилирование (statistical profiling)
6. Обнаружение аномалий (anomaly detection)
7. Целостность SCD (SCD integrity)
8. Свежесть данных (data freshness)

**Рекомендация:** Разделить на 5 модулей:
- `gold_analyzer_core.py` — базовый анализатор и оркестрация
- `gold_checks_basic.py` — record count, completeness
- `gold_checks_business.py` — business rules
- `gold_checks_integrity.py` — referential integrity, SCD
- `gold_checks_statistical.py` — statistical profiling, anomaly detection

### 2.3 Файлы, требующие разделения

#### `composition/entrypoints.py` (771 LOC)
**Проблема:** 4 категории энтрипоинтов (пайплайны, обслуживание, ресурсы, сервисы) в одном файле.
**Рекомендация:**
- `pipeline_entrypoints.py` — run_pipeline, create_pipeline_runner
- `maintenance_entrypoints.py` — vacuum, archive, cleanup
- `service_entrypoints.py` — get_* сервис-функции

#### `composition/providers/registration.py` (715 LOC)
**Проблема:** Создатели для 7 провайдеров в одном файле.
**Рекомендация:**
- `core_providers.py` — ChEMBL, PubChem, UniProt
- `publication_providers.py` — PubMed, CrossRef, OpenAlex, SemanticScholar

#### `application/pipelines/semanticscholar/extractors.py` (709 LOC)
**Проблема:** 20+ функций извлечения без чёткой группировки.
**Рекомендация:**
- `basic_extractors.py` — DOI, external IDs, year validation
- `author_extractors.py` — Authors, affiliations, ORCIDs, h-indices
- `journal_extractors.py` — Volume/issue parsing, page ranges

---

## Этап 3: Слишком мелкие файлы

### 3.1 Общая статистика

Найдено **47 файлов** менее 60 строк (без `__init__.py`).

| Категория | Кол-во | Действие |
|-----------|--------|----------|
| **KEEP** — обоснованные маленькие модули | 28 | Оставить |
| **MERGE** — пустые pipeline-классы | 17 | Консолидировать |
| **RE-EXPORT** — backward compatibility | 2 | Оценить deprecation |
| **DELETE** — мёртвый код | 0 | — |

### 3.2 Главная находка: 17 пустых pipeline-классов

Крупнейшая возможность для консолидации — **17 пустых классов пайплайнов**, которые наследуют всё от `BasePipeline` без добавления логики:

| Файл | LOC | Провайдер/сущность |
|------|-----|---------------------|
| `pipelines/chembl/activity.py` | 24 | ChEMBL Activity |
| `pipelines/chembl/assay.py` | 24 | ChEMBL Assay |
| `pipelines/chembl/assay_parameters.py` | 29 | ChEMBL AssayParameters |
| `pipelines/chembl/cell_line.py` | 27 | ChEMBL CellLine |
| `pipelines/chembl/compound_record.py` | 27 | ChEMBL CompoundRecord |
| `pipelines/chembl/molecule.py` | 24 | ChEMBL Molecule |
| `pipelines/chembl/protein_class.py` | 28 | ChEMBL ProteinClass |
| `pipelines/chembl/publication.py` | 30 | ChEMBL Publication |
| `pipelines/chembl/publication_similarity.py` | 35 | ChEMBL PublicationSimilarity |
| `pipelines/chembl/publication_term.py` | 40 | ChEMBL PublicationTerm |
| `pipelines/chembl/subcellular_fraction.py` | 43 | ChEMBL SubcellularFraction |
| `pipelines/chembl/target.py` | 24 | ChEMBL Target |
| `pipelines/chembl/target_component.py` | 24 | ChEMBL TargetComponent |
| `pipelines/chembl/tissue.py` | 27 | ChEMBL Tissue |
| `pipelines/pubchem/compound.py` | 17 | PubChem Compound |
| `pipelines/uniprot/protein.py` | 17 | UniProt Protein |
| `pipelines/pubmed/publication.py` | 18 | PubMed Publication |

**Паттерн:** Каждый файл определяет класс вида:
```python
class ChemblActivityPipeline(BasePipeline):
    """ChEMBL activity pipeline."""
    # Всё наследуется от BasePipeline, нет собственной логики
```

**Рекомендация:** Заменить на фабричную регистрацию через данные (YAML/dict), чтобы один конфигурационный модуль заменил 17 файлов. Это сократит:
- 17 файлов → 1 файл
- ~500 LOC boilerplate → ~100 LOC конфигурации

**Компромиссы:**
- Текущий подход даёт IDE-discoverability и явные импорты
- Фабричный подход требует dynamic dispatch

### 3.3 Обоснованно маленькие файлы (KEEP)

- **Entry points** (2): `__main__.py` — обязательные точки входа
- **Constants** (2): `domain/constants.py`, `domain/contracts/gold/_base.py`
- **Schemas** (7): Pandera-схемы для простых сущностей (molecule_form, target_relation и т.д.)
- **Filters** (2): Domain filter dataclasses
- **Entities** (1): `chembl_tissue.py` — простая сущность
- **Exceptions** (1): `data_quality.py`
- **CLI commands** (6): Отдельные команды — нормальная CLI-архитектура
- **Bootstrap functions** (4): DI-wiring функции в composition

---

## Этап 4: Анализ разделения слоёв

### 4.1 Результат проверки импортов

| Нарушение | Кол-во |
|-----------|--------|
| domain → infrastructure | **0** |
| domain → application | **0** |
| domain → composition | **0** |
| domain → interfaces | **0** |
| application → infrastructure | **0** |
| application → composition | **0** |
| application → interfaces | **0** |
| infrastructure → application | **0** |
| infrastructure → composition | **0** |
| infrastructure → interfaces | **0** |

**Вердикт: Архитектурные границы соблюдаются полностью.** Ни одного нарушения матрицы импортов ARCH-001. Единственное совпадение (`application/pipelines/__init__.py:13`) — это комментарий в docstring, не реальный импорт.

### 4.2 Распределение по слоям

```
domain (31.8%)        ████████████████████████████████
application (28.7%)   ████████████████████████████▊
infrastructure (27.6%) ███████████████████████████▋
composition (9.2%)     █████████▏
interfaces (2.8%)      ██▊
```

**Наблюдения:**
- Баланс между domain/application/infrastructure хороший (~30% каждый)
- composition (9.2%) — приемлемо для чисто-сборочного слоя
- interfaces (2.8%) — минимален, что хорошо (тонкий адаптер)
- domain самый крупный — это нормально для domain-driven проекта

### 4.3 Потенциальная проблема: domain/schemas vs domain/contracts

В domain находятся два каталога со схемами:
- `domain/schemas/` — Pandera DataFrameModel schemas для Bronze/Silver/Gold
- `domain/contracts/gold/` — отдельные Gold-контракты

Это создаёт неоднозначность: где искать Gold-схему — в `schemas` или `contracts`?

**Рекомендация:** Консолидировать в единое место или чётко разграничить назначение в документации.

---

## Целевая структура каталогов (предложение)

Предлагаемые изменения минимальны и сфокусированы на quick wins:

```
src/bioetl/
├── domain/                          # БЕЗ ИЗМЕНЕНИЙ — чистый, хорошо структурирован
│   ├── schemas/                     # Консолидировать contracts/gold/ сюда (?)
│   └── ...
├── application/
│   ├── pipelines/
│   │   ├── chembl/
│   │   │   ├── __init__.py          # Убрать 14 пустых pipeline-классов
│   │   │   ├── registry.py          # НОВЫЙ: фабричная регистрация пайплайнов
│   │   │   ├── compound.py          # Оставить — содержит логику
│   │   │   ├── compound_transformer.py
│   │   │   └── ...
│   │   └── ...
│   └── services/
│       └── dq/
│           ├── gold_analyzer_core.py      # SPLIT из gold_analyzer.py
│           ├── gold_checks_basic.py       # SPLIT
│           ├── gold_checks_business.py    # SPLIT
│           ├── gold_checks_integrity.py   # SPLIT
│           └── gold_checks_statistical.py # SPLIT
├── infrastructure/                  # БЕЗ СУЩЕСТВЕННЫХ ИЗМЕНЕНИЙ
├── composition/
│   ├── entrypoints/                 # SPLIT из entrypoints.py
│   │   ├── pipeline.py
│   │   ├── maintenance.py
│   │   └── services.py
│   └── providers/
│       ├── core_providers.py        # SPLIT из registration.py
│       └── publication_providers.py # SPLIT
└── interfaces/                      # БЕЗ ИЗМЕНЕНИЙ
```

---

## Сводка рекомендаций

### Quick Wins (низкий риск, быстрая реализация)

| # | Действие | Файлов | LOC | Трудоёмкость |
|---|----------|--------|-----|--------------|
| 1 | Удалить дубликат `NoOpMetadataWriter` из infrastructure | 1 | -60 | 1ч |
| 2 | Deprecate re-export `application/services/dq_metrics_calculator.py` | 1 | -16 | 0.5ч |
| 3 | Консолидировать 17 пустых pipeline-классов в реестр | -16 | -400 | 4ч |

### Средний приоритет (требуют аккуратного рефакторинга)

| # | Действие | Файлов | LOC | Трудоёмкость |
|---|----------|--------|-----|--------------|
| 4 | Разделить `gold_analyzer.py` (God Module) | +4 | ±0 | 3ч |
| 5 | Разделить `entrypoints.py` на 3 модуля | +2 | ±0 | 2ч |
| 6 | Разделить `registration.py` на 2 модуля | +1 | ±0 | 2ч |
| 7 | Разделить `semanticscholar/extractors.py` | +2 | ±0 | 2ч |

### Долгосрочный редизайн (требуют дискуссии)

| # | Действие | Описание | Трудоёмкость |
|---|----------|----------|--------------|
| 8 | Консолидация domain/schemas + domain/contracts | Устранить неоднозначность расположения Gold-схем | 8ч |

---

## Оценка итогового эффекта

| Метрика | Было | Станет (quick wins) | Станет (всё) |
|---------|------|---------------------|--------------|
| Python-файлов | 510 | **494** (-16) | **494** |
| Содержательных модулей | 431 | **415** (-16) | **424** (+9 от split, -16 от merge) |
| LOC | 113 840 | **113 364** (-476) | ~113 364 |
| God Modules | 1 | 1 | **0** |
| Нарушений ARCH-001 | 0 | 0 | 0 |
| Дубликатов классов | 1 | **0** | **0** |

---

## Приоритеты реализации

```
1. [Quick Win]  Удалить NoOpMetadataWriter дубликат          → 1ч
2. [Quick Win]  Консолидировать 17 пустых pipeline-классов   → 4ч
3. [Medium]     Разделить gold_analyzer.py                   → 3ч
4. [Medium]     Разделить entrypoints.py                     → 2ч
5. [Medium]     Разделить registration.py                    → 2ч
6. [Medium]     Разделить semanticscholar/extractors.py      → 2ч
7. [Low]        Deprecate re-export модули                   → 0.5ч
8. [Long-term]  Консолидация schemas/contracts               → 8ч
```

**Общая трудоёмкость:** ~22.5 человеко-часов

---

## Заключение

Кодовая база BioETL в целом **хорошо структурирована**:

- **Архитектурные границы соблюдаются на 100%** — ни одного нарушения ARCH-001
- **Из 18 крупнейших файлов только 1 — God Module** (gold_analyzer.py)
- **Дублирование минимально** — 1 подтверждённый дубликат (NoOpMetadataWriter)
- **Баланс LOC между слоями адекватный** (~30%/30%/28%/9%/3%)

Основные точки улучшения:
1. **17 пустых pipeline-классов** — главный source навигационного шума
2. **God Module gold_analyzer.py** — единственный серьёзный SRP-violation
3. **3 файла 700+ LOC** требуют разделения для лучшей навигации

Рекомендуемый подход: начать с quick wins (пп. 1-2), затем поэтапно реализовать средний приоритет с полным покрытием тестами перед каждым merge.
