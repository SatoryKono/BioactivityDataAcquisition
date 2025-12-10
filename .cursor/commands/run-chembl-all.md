# /run-chembl-all

**Goal:** Последовательно запустить ChEMBL-пайплайны и собрать отчёт.

**Inputs**

- `--output-root PATH` (required)
- `--configs-dir PATH` (optional)
- `--profile NAME` (optional)
- `--limit N` (optional)
- `--golden PATH` (optional)

**Steps**

1) Запустить: assay → activity → target → publication → molecule
2) Использовать команды `/run-*-chembl` (CLI: `bioetl run <name> ...`)
3) Агрегировать QC/метрики
4) Опционально сравнить с golden-наборами

**Constraints**

- ISO-UTC, общий seed, детерминизм; частичные результаты сохранять

**Outputs**

- `reports/chembl_all/summary.md`, `reports/chembl_all/qc.json`

**Exit criteria**

- Успешное завершение или документированные причины с кодами

