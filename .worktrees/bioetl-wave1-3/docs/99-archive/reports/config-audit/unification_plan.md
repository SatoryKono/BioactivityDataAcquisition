# План Унификации Конфигурационных Файлов BioETL

**Дата генерации**: 2026-02-03
**Версия анализатора**: 2.1.0 (Enhanced by Claude Config Audit Agent)

---

## Executive Summary

Анализ **97 конфигурационных файлов** проекта BioETL показал **0 критических проблем**.

Все конфигурации соответствуют требованиям:
- ✅ **ADR-014** (Deterministic Writes): `sort-by.columns` авто-пропагируется из `primary-keys`
- ✅ **ADR-025** (Config Unification): Иерархия `-base.yaml` → provider → entity соблюдена
- ✅ **ADR-027** (DQ Externalization): DQ defaults и entity configs корректны
- ✅ **ADR-028** (Filter Externalization): Filter configs корректны
- ✅ **ADR-029** (Convention Paths): Авто-вычисление путей работает корректно

### Key Finding: Convention System Verified

Критический вывод: система convention-based defaults в `config-loader.py` (строки 151-209) корректно автоматически заполняет:
- `sink.silver.primary-key` ← `primary-keys`
- `sink.silver.sort-by.columns` ← `primary-keys`
- `sink.gold.sort-by.columns` ← `primary-keys`
- `sink.*.path` ← `data/output/{layer}/{provider}/{entity-type}`
- File references ← convention paths

Это означает, что "отсутствующие" параметры в минимальных конфигах (activity, assay, protein) — это **by design**, а не ошибка.

---

## 1. Статистика Конфигураций

| Категория | Количество | Статус |
|-----------|------------|--------|
| Pipeline configs (regular) | 19 | ✅ OK |
| Composite configs | 2 | ✅ OK |
| DQ configs (-defaults + providers + entities) | 29 | ✅ OK |
| Filter configs (-defaults + providers + entities) | 28 | ✅ OK |
| Source configs | 7 | ✅ OK |
| Data schema configs | 22 | ✅ OK |
| **Итого** | **97** | **✅ OK** |

---

## 2. Провайдеры и Entities

### Regular Pipelines (19)

| Provider | Count | Entities |
|----------|-------|----------|
| chembl | 12 | activity, assay, assay-parameters, cell-line, compound-record, molecule, protein-class, publication, publication-similarity, publication-term, target, target-component |
| pubchem | 1 | compound |
| uniprot | 2 | idmapping, protein |
| pubmed | 1 | publication |
| crossref | 1 | publication (entity-type: work) |
| openalex | 1 | publication |
| semanticscholar | 1 | publication |

### Composite Pipelines (2)

| Name | Seed | Dependencies/Enrichers |
|------|------|------------------------|
| composite-publication | chembl-publication | crossref, openalex, pubmed, semanticscholar |
| composite-target | chembl-target | target-component, protein-class, idmapping, protein |

---

## 3. ADR Compliance Checklist

### ADR-014: Deterministic Writes ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `sink.silver.sort-by.columns` | ✅ | Авто-пропагируется из `primary-keys` (`config-loader.py:170-172`) |
| `sink.gold.sort-by.columns` | ✅ | Авто-пропагируется из `primary-keys` (`config-loader.py:170-172`) |
| `sink.silver.primary-key` | ✅ | Авто-пропагируется из `primary-keys` (`config-loader.py:167-168`) |
| Timestamps via `PipelineContext` | ✅ | Реализовано в transformer layer |

### ADR-025: Config Unification ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `-base.yaml` v2.0.0 | ✅ | 474 строк, schema-version: "2.0.0" |
| `-schema.json` validation | ✅ | JSON Schema v2020-12, 247 строк |
| Path convention | ✅ | `{layer}/{provider}/{entity-type}` |
| 7 source configs | ✅ | Все провайдеры покрыты |

### ADR-027: DQ Externalization ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `-defaults.yaml` thresholds | ✅ | soft-fail=0.05, hard-fail=0.20 |
| soft-fail < hard-fail | ✅ | Инвариант соблюдён во всех файлах |
| Provider DQ configs | ✅ | 7 файлов (chembl stricter: 0.15) |
| Entity DQ configs | ✅ | 21 файл (idmapping: 0.30/0.80) |

### ADR-028: Filter Externalization ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `-defaults.yaml` | ✅ | batch-size=100 |
| Provider filter configs | ✅ | 7 файлов |
| Entity filter configs | ✅ | 20 файлов |
| input-filter merge | ✅ | Реализовано в `-merge-filter-config()` |
| gold-filters merge | ✅ | Реализовано в `-merge-filter-config()` |

### ADR-029: Convention-Based Paths ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| File reference defaults | ✅ | `-apply-file-reference-defaults()` |
| Layer path defaults | ✅ | `-apply-layer-defaults()` |
| Primary key propagation | ✅ | `-apply-convention-defaults()` |
| Minimal config support | ✅ | 3 configs use convention-only |

---

## 4. Анализ Стилей Конфигурации

### 4.1 Три Стиля Конфигов

| Стиль | Количество | Примеры | Описание |
|-------|------------|---------|----------|
| **Convention Minimal** | 3 | activity, assay, protein | Только обязательные поля, остальное по convention |
| **Explicit Full** | 14 | molecule, target, pubchem | Все пути и параметры указаны явно |
| **Hybrid** | 2 | pubmed, idmapping | Частичная explicit конфигурация |

**Вывод:** Все стили валидны и работают корректно. Рекомендуется использовать convention minimal для новых конфигов.

### 4.2 Naming Variations

| Параметр | Старое имя | Новое имя | Файлов |
|----------|------------|-----------|--------|
| Column schema | `column-groups-file` | `data-schema-file` | 14 vs 6 |

**Рекомендация:** Использовать `data-schema-file` для новых конфигов (поддерживает layer-specific columns).

### 4.3 CrossRef entity-type

CrossRef использует `entity-type: work` вместо `publication`:
- **Причина**: CrossRef API использует термин "Works" для публикаций
- **Статус**: **По дизайну**, не требует изменения
- **pipeline-name**: `crossref-publication` (консистентно с системой)

---

## 5. Convention System Deep Dive

### 5.1 Код Auto-Propagation

```python
# config-loader.py:151-177
def -apply-layer-defaults(layer, provider, entity-type, layer-name, primary-keys):
    # Path auto-computed
    layer.setdefault("path", f"data/output/{layer-name}/{provider}/{entity-type}")

    if primary-keys:
        # Silver gets primary-key
        if layer-name == "silver":
            layer.setdefault("primary-key", list(primary-keys))

        # Both silver and gold get sort-by.columns
        sort-by = layer.setdefault("sort-by", {})
        sort-by.setdefault("columns", list(primary-keys))

    # CSV export path mirrors layer path
    csv-export = layer.setdefault("csv-export", {})
    csv-export.setdefault("path", layer["path"])
```

### 5.2 Что Авто-Заполняется

| Параметр | Источник | Формула |
|----------|----------|---------|
| `source-file` | Convention | `../../sources/{provider}.yaml` |
| `dq-config-file` | Convention | `../../dq/entities/{provider}/{entity-type}.yaml` |
| `filter-config-file` | Convention | `../../filter/entities/{provider}/{entity-type}.yaml` |
| `column-groups-file` | Convention | `../data-schema/{provider}/{entity-type}.yaml` |
| `sink.bronze.path` | Convention | `data/output/bronze/{provider}/{entity-type}` |
| `sink.silver.path` | Convention | `data/output/silver/{provider}/{entity-type}` |
| `sink.gold.path` | Convention | `data/output/gold/{provider}/{entity-type}` |
| `sink.silver.primary-key` | `primary-keys` | Копия списка |
| `sink.silver.sort-by.columns` | `primary-keys` | Копия списка |
| `sink.gold.sort-by.columns` | `primary-keys` | Копия списка |
| `sink.*.csv-export.path` | `sink.*.path` | То же значение |

---

## 6. Рекомендации

### Приоритет P3 (Nice to Have)

| # | Рекомендация | Effort | Impact |
|---|--------------|--------|--------|
| 1 | Документировать convention vs explicit в `-base.yaml` | 15 min | Улучшение onboarding |
| 2 | Добавить `force-full-scan`, `loading-strategy` в `-schema.json` | 30 min | Schema completeness |
| 3 | Стандартизировать ChEMBL на convention style | 1 hour | Code consistency |
| 4 | Создать `-composite-schema.json` для composite pipelines | 1 hour | Validation coverage |

### Не Требуется

- ❌ Добавление sort-by в entity configs (авто-пропагируется)
- ❌ Изменение DQ thresholds (корректны)
- ❌ Добавление missing configs (все существуют)
- ❌ Миграция column-groups-file → data-schema-file (оба работают)

---

## 7. Выводы

**Конфигурационные файлы BioETL унифицированы и соответствуют ADR.**

Система использует:
1. **Иерархическое наследование** (`-base.yaml` → provider → entity)
2. **Convention-based defaults** (авто-генерация путей и параметров в `config-loader.py`)
3. **Отдельные схемы** для regular и composite pipelines
4. **Merge logic** для filter и DQ конфигов

**Действий не требуется** — конфигурации корректны.

---

## 8. Артефакты Анализа

| Файл | Описание |
|------|----------|
| `config-analysis-report.yaml` | Полный YAML отчёт с convention validation |
| `config-comparison-matrix.csv` | Матрица сравнения 19 параметров × 19 configs |
| `config-issues.md` | Список issues (5 style recommendations) |
| `unification-plan.md` | Этот документ |

---

## Verification Checklist

- [x] Все 19 pipeline configs обработаны
- [x] Все 2 composite configs обработаны
- [x] Все 29 DQ configs обработаны
- [x] Все 28 Filter configs обработаны
- [x] Все 7 Source configs обработаны
- [x] Convention system verified in `config-loader.py`
- [x] ADR compliance confirmed (014, 025, 027, 028, 029)
- [x] Recommendations prioritized (P3 only)

---

*Сгенерировано Claude Config Audit Agent v2.1 | 2026-02-03*
