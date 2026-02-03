# План Унификации Конфигурационных Файлов BioETL

**Дата генерации**: 2026-02-03
**Версия анализатора**: 2.0.0

---

## Executive Summary

Анализ **58 конфигурационных файлов** проекта BioETL показал **0 критических проблем**.

Все конфигурации соответствуют требованиям:
- ✅ **ADR-014** (Deterministic Writes): `sort_by.columns` авто-пропагируется из `primary_keys`
- ✅ **ADR-025** (Config Unification): Иерархия `_base.yaml` → provider → entity соблюдена
- ✅ **ADR-027** (DQ Externalization): DQ defaults и entity configs корректны
- ✅ **ADR-028** (Filter Externalization): Filter configs корректны

---

## 1. Статистика Конфигураций

| Категория | Количество | Статус |
|-----------|------------|--------|
| Pipeline configs (regular) | 19 | ✅ OK |
| Composite configs | 2 | ✅ OK |
| DQ configs | 21 | ✅ OK |
| Filter configs | 8 | ✅ OK |
| Source configs | 7 | ✅ OK |
| **Итого** | **58** | **✅ OK** |

---

## 2. Провайдеры и Entities

### Regular Pipelines (19)

| Provider | Entities |
|----------|----------|
| chembl (12) | activity, assay, assay_parameters, cell_line, compound_record, molecule, protein_class, publication, publication_similarity, publication_term, target, target_component |
| pubchem (1) | compound |
| uniprot (2) | idmapping, protein |
| pubmed (1) | publication |
| crossref (1) | publication |
| openalex (1) | publication |
| semanticscholar (1) | publication |

### Composite Pipelines (2)

| Name | Seed | Enrichers |
|------|------|-----------|
| composite_publication | chembl_publication | crossref, openalex, pubmed, semanticscholar |
| composite_target | chembl_target | chembl_target_component, chembl_protein_class, uniprot_idmapping, uniprot_protein |

---

## 3. ADR Compliance Checklist

### ADR-014: Deterministic Writes ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `sink.silver.sort_by.columns` | ✅ | Авто-пропагируется из `primary_keys` |
| `sink.gold.sort_by.columns` | ✅ | Авто-пропагируется из `primary_keys` |
| Timestamps через `PipelineContext` | ✅ | Реализовано в config_loader.py:155-176 |

### ADR-025: Config Unification ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `_base.yaml` v2.0.0 | ✅ | 474 строк, полный template |
| `_schema.json` валидация | ✅ | JSON Schema v2020-12 |
| Пути `{layer}/{provider}/{entity}/` | ✅ | Авто-генерируются |
| 7 source configs | ✅ | Все провайдеры |

### ADR-027: DQ Externalization ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `_defaults.yaml` thresholds | ✅ | soft_fail=0.05, hard_fail=0.20 |
| soft_fail < hard_fail | ✅ | Инвариант соблюдён |
| Provider DQ configs | ✅ | 7 файлов |
| Entity DQ configs | ✅ | 14 файлов |

### ADR-028: Filter Externalization ✅

| Требование | Статус | Примечание |
|------------|--------|------------|
| `_defaults.yaml` | ✅ | batch_size=100 |
| Provider configs | ✅ | 7 файлов с batch_size |
| Entity configs | ✅ | По необходимости |

---

## 4. Особенности и Примечания

### 4.1 CrossRef entity_type

CrossRef использует `entity_type: work` вместо `publication`:
- **Причина**: CrossRef API использует термин "Works" для публикаций
- **Статус**: Это **по дизайну**, не требует изменения
- **pipeline_name**: `crossref_publication` (консистентно с системой)

### 4.2 Convention-Based Defaults

Многие параметры **авто-генерируются** в `config_loader.py`:

```python
# Авто-пропагация (config_loader.py:155-176)
sink.silver.path     → data/output/silver/{provider}/{entity_type}
sink.silver.primary_key → {primary_keys}
sink.silver.sort_by.columns → {primary_keys}
sink.gold.path       → data/output/gold/{provider}/{entity_type}
sink.gold.sort_by.columns → {primary_keys}
```

Это означает, что entity configs **минималистичны** — они содержат только override параметры.

### 4.3 Composite Configs Schema

Composite configs используют **другую схему** (ADR-026):

```yaml
composite:
  name: composite_publication
  version: "1.1.0"
  seed:
    pipeline: chembl_publication
  enrichers:
    - pipeline: crossref_publication
  merge:
    strategy: left_outer
```

Вместо стандартных `pipeline_name`, `provider`, `entity_type`.

---

## 5. Рекомендации

### Приоритет P3 (Nice to Have)

| # | Рекомендация | Обоснование |
|---|--------------|-------------|
| 1 | Документировать CrossRef `work` entity_type | Избежать путаницы |
| 2 | Добавить validation для composite schema | Пока только для regular pipelines |
| 3 | Расширить анализатор для data_schema configs | Не все 21 data_schema файлов проанализированы |

### Не Требуется

- ❌ Добавление sort_by в entity configs (авто-пропагируется)
- ❌ Изменение DQ thresholds (корректны)
- ❌ Добавление missing configs (все существуют)

---

## 6. Выводы

**Конфигурационные файлы BioETL унифицированы и соответствуют ADR.**

Система использует:
1. **Иерархическое наследование** (`_base.yaml` → provider → entity)
2. **Convention-based defaults** (авто-генерация путей и параметров)
3. **Отдельные схемы** для regular и composite pipelines

**Действий не требуется** — конфигурации корректны.

---

## Артефакты Анализа

| Файл | Описание |
|------|----------|
| `config_analysis_report.yaml` | Полный YAML отчёт |
| `config_comparison_matrix.csv` | Матрица сравнения параметров |
| `config_issues.md` | Список issues (пустой) |
| `unification_plan.md` | Этот документ |
