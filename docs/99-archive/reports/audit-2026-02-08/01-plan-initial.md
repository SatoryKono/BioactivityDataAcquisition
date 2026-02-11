# Plan: audit-fix-2026-02-08

**Дата**: 2026-02-08
**Task ID**: `audit-fix-2026-02-08`
**Subagent**: pyPlanBot

## 1. Резюме задачи
Устранение критических замечаний аудита от 2026-02-08: приведение конфигураций к стандартам ADR-014/025, очистка структуры корня проекта и расширение документации.

## 2. Список изменений (RF-*)

### RF-CFG-001 [MUST] — Конфигурации Sink
**Описание**: Добавить явные параметры `sort_by` и `primary_key` в конфигурации пайплайнов для соответствия ADR-014 и ADR-025.
**Файлы**:
- `configs/pipelines/chembl/activity.yaml`
- `configs/pipelines/chembl/assay.yaml`
- `configs/pipelines/pubmed/publication.yaml`
- `configs/pipelines/uniprot/protein.yaml`

### RF-STR-001 [MUST] — Удаление папки run/
**Описание**: Переместить `run/setup.sh` в `scripts/` для соблюдения структуры проекта.
**Действия**:
1. `mv run/setup.sh scripts/setup.sh`
2. `rmdir run/`

### RF-DOC-001 [SHOULD] — Документация ChEMBL
**Описание**: Создать недостающие спецификации для пайплайнов ChEMBL.
**Файлы**:
- `docs/04-reference/pipelines/chembl/15-protein-class-spec.md`
- `docs/04-reference/pipelines/chembl/16-target-component-spec.md`
- `docs/04-reference/pipelines/chembl/17-publication-similarity-spec.md`
- `docs/04-reference/pipelines/chembl/18-publication-term-spec.md`

## 3. Последовательность выполнения
1. **Implementation (Config)**: Выполнить RF-CFG-001.
2. **Implementation (Structure)**: Выполнить RF-STR-001.
3. **Implementation (Doc)**: Выполнить RF-DOC-001.
4. **Verification**: Запустить `scripts/config_gap_analysis.py` и `scripts/audit_structure.py`.

## 4. Критерии успеха
- `config_gap_analysis.py` показывает 0 critical issues.
- `audit_structure.py` показывает 0 MUST violations.
- Документация по 4 новым пайплайнам доступна.
