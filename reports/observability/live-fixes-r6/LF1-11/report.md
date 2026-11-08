# LF1-11 Execution Report (Остаток)

## Overview
Этот отчет фиксирует статус выполнения живого запуска для проверки манифестов. В соответствии с решением сводного гейта LF1-09 (REJECTED), живой запуск и поставка **не разрешены**.

## Execution Details
- **Command:** `uv run python -m bioetl run --pipeline chembl_activity --run-type backfill --limit 10 --required-persistence-profile degraded_observable -y` (Не выполнялась)
- **Exit Code:** NOT_RUN
- **Source SHA (base):** `ba13e94f23ff267ac940cc6d8fc9bf35bbc8be06`
- **Deploy SHA (HEAD):** NOT_VERIFIABLE (Среда недоступна / запуск заблокирован)
- **Report assessment UTC:** 2026-11-08 21:17:36 UTC
- **Run ID:** NOT_RUN
- **Manifest ID:** NOT_RUN
- **Status:** BLOCKED

## Actual vs Expected
- **Expected:** Pipeline executes successfully and generates a complete manifest bundle in `data/output/control/run_manifest`.
- **Actual:** Запуск не выполнялся (BLOCKED), так как сводный гейт LF1-09 отклонен (REJECTED) и поставка заблокирована.

## Dependencies
- **LF1-10 / #12806:** BLOCKED. Поставка отменена из-за LF1-09 REJECTED. (На проверенной ревизии файл LF1-10 отсутствует. Документирование блокировки ведётся в PR #12906).
- **LF1-05 / #12801:** BLOCKED / NOT_VERIFIABLE (Живая приёмка отклонена, живая среда недоступна).
- **LF1-09 / #12805:** REJECTED. Поставка НЕ РАЗРЕШЕНА, контрольный запуск (ETL/downstream) НЕ РАЗРЕШЁН.

## Artifacts
Запуск не производился. Исторические артефакты остаются в каталоге, но новые не сгенерированы.

## Historical execution and retained evidence

Эти результаты относятся к предыдущему запуску. Соседние артефакты относятся к указанным ниже идентификаторам.

- **Command:** `uv run python -m bioetl run --pipeline chembl_activity --run-type backfill --limit 10 --required-persistence-profile degraded_observable -y`
- **Exit Code:** 0
- **Source SHA (base):** `74cb6ccaa5dfe6fa97ec4e7ce468cc2d3c3992fd`
- **Deploy SHA (HEAD):** `99caf1aee6f214de0832eef2c8e0d51496cc811d`
- **Execution UTC:** 2026-11-07 23:22:46 UTC
- **Run ID:** `8ed593ce-3b75-56e0-a337-192953048582`
- **Manifest ID:** `6da492a7-cc24-5adf-88f0-b9c2ad0e8df2`
- **Status:** PASS

## Actual vs Expected
- **Expected:** Pipeline executes successfully and generates a complete manifest bundle in `data/output/control/run_manifest`.
- **Actual:** Pipeline executed successfully. The manifest, contract-evidence sidecar, and validation/inspection artifacts were generated and successfully copied to `reports/observability/live-fixes-r6/LF1-11/`.

### Historical artifacts

1. `manifest.json` - Complete manifest bundle.
2. `contract-evidence.json` - Evidence of contract validation.
3. `manifest-validation.json` - Score validation output.
4. `manifest-show.txt` - Complete execution diagnostics and trace output.
