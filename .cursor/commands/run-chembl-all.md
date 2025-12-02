# /run-chembl-all

**Goal:** Последовательно запустить все ChEMBL-пайплайны и собрать единый отчёт.


**Inputs**

- `--output-root PATH` (required): корневая директория артефактов
- `--configs-dir PATH` (optional): корень конфигов
- `--limit N` (optional)
- `--extended` (optional)
- `--golden PATH` (optional)


**Steps**

1) Запуск run-assay-chembl → run-activity-chembl → run-target-chembl → run-document-chembl → run-testitem-chembl
2) Агрегировать QC/метрики
3) Опционально сравнить с golden-наборами


**Constraints**

- Общий seed и дата-время в ISO-UTC
- Обработка ошибок с сохранением частичных результатов


**Outputs**

- `reports/chembl_all/summary.md`
- `reports/chembl_all/qc.json`


**Exit criteria**

- Все пайплайны завершились без ошибок или указаны конкретные причины с кодами

