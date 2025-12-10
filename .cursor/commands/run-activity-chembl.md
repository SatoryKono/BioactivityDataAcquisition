# /run-activity-chembl

**Goal:** Запуск пайплайна активности ChEMBL с корректным CLI.

**Inputs**

- `--output PATH` (required): директория артефактов
- `--config PATH` (optional): по умолчанию `configs/pipelines/chembl/activity.yaml`
- `--dry-run` (optional)
- `--profile NAME` (optional)
- `--limit N` (optional)

**Steps**

1) Проверить `configs/pipelines/chembl/activity.yaml`
2) Создать выходную директорию при отсутствии
3) Запустить: `bioetl run activity_chembl --config configs/pipelines/chembl/activity.yaml --output <output> [--limit N] [--dry-run] [--profile NAME]`
4) Убедиться в коде возврата 0
5) Проверить артефакты и `meta.yaml`

**Constraints**

- Детерминизм, стабильная сортировка, каноническая сериализация
- Валидация Pandera перед записью
- Логирование через UnifiedLogger

**Outputs**

- `data/output/activity/` (CSV/Parquet)
- `meta.yaml`, QC отчёты, структурированные логи

**References**

- `configs/pipelines/chembl/activity.yaml`

