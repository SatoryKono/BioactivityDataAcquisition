# Audit Baseline: audit-2026-02-08

**Дата**: 2026-02-08
**Scope**: Full Project Audit
**Чеклисты**: A (Architecture), B (Code Quality), C (Data/ETL), D (Config), E (Docs)

## Summary

| Severity | Count |
|----------|:-----:|
| **MUST (Critical)** | **9** |
| SHOULD (Medium) | 13 |
| MAY (Low) | 28 |

## Findings

### AUD-001 [MUST] Config Compliance (ADR-014, ADR-025)
**Location**: `configs/pipelines/chembl/activity.yaml`, `assay.yaml`, `pubmed/publication.yaml`, `uniprot/protein.yaml`.
**Rule Violated**: ADR-014 (Deterministic Writes), ADR-025 (Pipeline Config Unification).
**Evidence**:
- Missing `sink.silver.sort-by` field.
- Missing `sink.silver.primary-key` field.
- Missing `sink.gold.sort-by` field (where gold is enabled).
**Impact**: Недетерминированные записи в Delta Lake, нарушение контракта конфигурации.
**Recommendation**: Добавить поля `sort-by` и `primary-key` во все silver/gold sink конфигурации.

### AUD-002 [MUST] Project Structure
**Location**: `[ROOT]/run/`
**Rule Violated**: Johnny.Decimal structure (ADR-003).
**Evidence**: Папка `run` находится в корне проекта.
**Impact**: Загрязнение корня проекта.
**Recommendation**: Переместить скрипты из `run/` в `scripts/` или удалить, если они дублируют `bioetl` CLI.

### AUD-003 [SHOULD] Missing Documentation
**Location**: `docs/04-reference/pipelines/chembl/`
**Rule Violated**: Documentation Coverage.
**Evidence**: Отсутствует документация для `chembl-publication-similarity`, `chembl-publication-term`, `chembl-protein-class`, `chembl-target-component`.
**Impact**: Неполная справка по пайплайнам.
**Recommendation**: Создать спецификации (RFC-DOC-*).

### AUD-004 [SHOULD] Legacy Config Sections
**Location**: Multiple files in `configs/pipelines/`.
**Rule Violated**: ADR-025.
**Evidence**: Missing `sink.bronze` and `sink.gold` sections in some configs (e.g. `chembl/activity.yaml`).
**Impact**: Неполное описание потоков данных.
**Recommendation**: Явно определить секции sink для всех слоев.

## Valid-by-design
- `MemoryLock` usage в infrastructure (ADR-010 local-only).
- `NoOpMetrics` в тестах.
- `Ruff` форматирование соответствует стандартам (passed).
- Архитектурные границы соблюдены (1126 тестов прошли).

## Рекомендации для pyPlanBot

1. **RF-CFG-001 (Critical)**: Исправить конфигурации `chembl`, `pubmed`, `uniprot` (добавить `sort-by`, `primary-key`).
2. **RF-STR-001 (Critical)**: Удалить/переместить папку `run/`.
3. **RF-DOC-001 (Medium)**: Добавить недостающие спецификации пайплайнов.
