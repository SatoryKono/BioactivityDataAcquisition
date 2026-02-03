# План Унификации Конфигурационных Файлов BioETL

**Дата генерации**: 2026-02-03
**Версия анализатора**: 2.1.0 (Enhanced by Claude Config Audit Agent)

---

## Executive Summary

Анализ **97 конфигурационных файлов** проекта BioETL показал **0 критических проблем**.

Все конфигурации соответствуют требованиям:
- ✅ **ADR-014** (Deterministic Writes): `sort_by.columns` авто-пропагируется из `primary_keys`
- ✅ **ADR-025** (Config Unification): Иерархия `_base.yaml` → provider → entity соблюдена
- ✅ **ADR-027** (DQ Externalization): DQ defaults и entity configs корректны
- ✅ **ADR-028** (Filter Externalization): Filter configs корректны
- ✅ **ADR-029** (Convention Paths): Авто-вычисление путей работает корректно

### Key Finding: Convention System Verified

Критический вывод: система convention-based defaults в `config_loader.py` (строки 151-209) корректно автоматически заполняет:
- `sink.silver.primary_key` ← `primary_keys`
- `sink.silver.sort_by.columns` ← `primary_keys`
- `sink.gold.sort_by.columns` ← `primary_keys`
- `sink.*.path` ← `data/output/{layer}/{provider}/{entity_type}`
- File references ← convention paths

Это означает, что "отсутствующие" параметры в минимальных конфигах (activity, assay, protein) — это **by design**, а не ошибка.

---

## 1. Статистика Конфигураций

| Категория | Количество | Статус |
|-----------|------------|--------|
| Pipeline configs (regular) | 19 | ✅ OK |
| Composite configs | 2 | ✅ OK |
| DQ configs (_defaults + providers + entities) | 29 | ✅ OK |
| Filter configs (_defaults + providers + entities) | 28 | ✅ OK |
| Source configs | 7 | ✅ OK |
| Data schema configs | 22 | ✅ OK |
| **Итого** | **97** | **✅ OK** |

---

## 2. Провайдеры и Entities

### Regular Pipelines (19)

| Provider | Count | Entities |
|----------|-------|----------|
| chembl | 12 | activity, assay, assay_parameters, cell_line, compound_record, molecule, protein_class, publication, publication_similarity, publication_term, target, target_component |
| pubchem | 1 | compound |
| uniprot | 2 | idmapping, protein |
| pubmed | 1 | publication |
| crossref | 1 | publication (entity_type: work) |
| openalex | 1 | publication |
| semanticscholar | 1 | publication |

### Composite Pipelines (2)

| Name | Seed | Dependencies/Enrichers |
|------|------|------------------------|
| composite_publication | chembl_publication | crossref, openalex, pubmed, semanticscholar |
| composite_target | chembl_target | target_component, protein_class, idmapping, protein |

---

## 3. ADR Compliance Checklist

### ADR-014: Deterministic Writes ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `sink.silver.sort_by.columns` | ✅ | Авто-пропагируется из `primary_keys` (`config_loader.py:170-172`) |
| `sink.gold.sort_by.columns` | ✅ | Авто-пропагируется из `primary_keys` (`config_loader.py:170-172`) |
| `sink.silver.primary_key` | ✅ | Авто-пропагируется из `primary_keys` (`config_loader.py:167-168`) |
| Timestamps via `PipelineContext` | ✅ | Реализовано в transformer layer |

### ADR-025: Config Unification ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `_base.yaml` v2.0.0 | ✅ | 474 строк, schema_version: "2.0.0" |
| `_schema.json` validation | ✅ | JSON Schema v2020-12, 247 строк |
| Path convention | ✅ | `{layer}/{provider}/{entity_type}` |
| 7 source configs | ✅ | Все провайдеры покрыты |

### ADR-027: DQ Externalization ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `_defaults.yaml` thresholds | ✅ | soft_fail=0.05, hard_fail=0.20 |
| soft_fail < hard_fail | ✅ | Инвариант соблюдён во всех файлах |
| Provider DQ configs | ✅ | 7 файлов (chembl stricter: 0.15) |
| Entity DQ configs | ✅ | 21 файл (idmapping: 0.30/0.80) |

### ADR-028: Filter Externalization ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `_defaults.yaml` | ✅ | batch_size=100 |
| Provider filter configs | ✅ | 7 файлов |
| Entity filter configs | ✅ | 20 файлов |
| input_filter merge | ✅ | Реализовано в `_merge_filter_config()` |
| gold_filters merge | ✅ | Реализовано в `_merge_filter_config()` |

### ADR-029: Convention-Based Paths ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| File reference defaults | ✅ | `_apply_file_reference_defaults()` |
| Layer path defaults | ✅ | `_apply_layer_defaults()` |
| Primary key propagation | ✅ | `_apply_convention_defaults()` |
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
| Column schema | `column_groups_file` | `data_schema_file` | 14 vs 6 |

**Рекомендация:** Использовать `data_schema_file` для новых конфигов (поддерживает layer-specific columns).

### 4.3 CrossRef entity_type

CrossRef использует `entity_type: work` вместо `publication`:
- **Причина**: CrossRef API использует термин "Works" для публикаций
- **Статус**: **По дизайну**, не требует изменения
- **pipeline_name**: `crossref_publication` (консистентно с системой)

---

## 5. Convention System Deep Dive

### 5.1 Код Auto-Propagation

```python
# config_loader.py:151-177
def _apply_layer_defaults(layer, provider, entity_type, layer_name, primary_keys):
    # Path auto-computed
    layer.setdefault("path", f"data/output/{layer_name}/{provider}/{entity_type}")

    if primary_keys:
        # Silver gets primary_key
        if layer_name == "silver":
            layer.setdefault("primary_key", list(primary_keys))

        # Both silver and gold get sort_by.columns
        sort_by = layer.setdefault("sort_by", {})
        sort_by.setdefault("columns", list(primary_keys))

    # CSV export path mirrors layer path
    csv_export = layer.setdefault("csv_export", {})
    csv_export.setdefault("path", layer["path"])
```

### 5.2 Что Авто-Заполняется

| Параметр | Источник | Формула |
|----------|----------|---------|
| `source_file` | Convention | `../../sources/{provider}.yaml` |
| `dq_config_file` | Convention | `../../dq/entities/{provider}/{entity_type}.yaml` |
| `filter_config_file` | Convention | `../../filter/entities/{provider}/{entity_type}.yaml` |
| `column_groups_file` | Convention | `../data_schema/{provider}/{entity_type}.yaml` |
| `sink.bronze.path` | Convention | `data/output/bronze/{provider}/{entity_type}` |
| `sink.silver.path` | Convention | `data/output/silver/{provider}/{entity_type}` |
| `sink.gold.path` | Convention | `data/output/gold/{provider}/{entity_type}` |
| `sink.silver.primary_key` | `primary_keys` | Копия списка |
| `sink.silver.sort_by.columns` | `primary_keys` | Копия списка |
| `sink.gold.sort_by.columns` | `primary_keys` | Копия списка |
| `sink.*.csv_export.path` | `sink.*.path` | То же значение |

---

## 6. Рекомендации

### Приоритет P3 (Nice to Have)

| # | Рекомендация | Effort | Impact |
|---|--------------|--------|--------|
| 1 | Документировать convention vs explicit в `_base.yaml` | 15 min | Улучшение onboarding |
| 2 | Добавить `force_full_scan`, `loading_strategy` в `_schema.json` | 30 min | Schema completeness |
| 3 | Стандартизировать ChEMBL на convention style | 1 hour | Code consistency |
| 4 | Создать `_composite_schema.json` для composite pipelines | 1 hour | Validation coverage |

### Не Требуется

- ❌ Добавление sort_by в entity configs (авто-пропагируется)
- ❌ Изменение DQ thresholds (корректны)
- ❌ Добавление missing configs (все существуют)
- ❌ Миграция column_groups_file → data_schema_file (оба работают)

---

## 7. Выводы

**Конфигурационные файлы BioETL унифицированы и соответствуют ADR.**

Система использует:
1. **Иерархическое наследование** (`_base.yaml` → provider → entity)
2. **Convention-based defaults** (авто-генерация путей и параметров в `config_loader.py`)
3. **Отдельные схемы** для regular и composite pipelines
4. **Merge logic** для filter и DQ конфигов

**Действий не требуется** — конфигурации корректны.

---

## 8. Артефакты Анализа

| Файл | Описание |
|------|----------|
| `config_analysis_report.yaml` | Полный YAML отчёт с convention validation |
| `config_comparison_matrix.csv` | Матрица сравнения 19 параметров × 19 configs |
| `config_issues.md` | Список issues (5 style recommendations) |
| `unification_plan.md` | Этот документ |

---

## Verification Checklist

- [x] Все 19 pipeline configs обработаны
- [x] Все 2 composite configs обработаны
- [x] Все 29 DQ configs обработаны
- [x] Все 28 Filter configs обработаны
- [x] Все 7 Source configs обработаны
- [x] Convention system verified in `config_loader.py`
- [x] ADR compliance confirmed (014, 025, 027, 028, 029)
- [x] Recommendations prioritized (P3 only)

---

*Сгенерировано Claude Config Audit Agent v2.1 | 2026-02-03*
