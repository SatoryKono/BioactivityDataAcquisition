# LF1-11 Execution Report (Остаток)

## Overview
Этот отчет фиксирует статус выполнения живого запуска для проверки манифестов. В соответствии с решением сводного гейта LF1-09 (REJECTED), живой запуск и поставка **не разрешены**.

## Execution Details
- **Command:** `uv run python -m bioetl run --pipeline chembl_activity --run-type backfill --limit 10 --required-persistence-profile degraded_observable -y` (Не выполнялась)
- **Exit Code:** NOT_RUN
- **Source SHA (base):** `ba13e94f23ff267ac940cc6d8fc9bf35bbc8be06`
- **Deploy SHA (HEAD):** NOT_VERIFIABLE (Среда недоступна / запуск заблокирован)
- **Execution UTC:** 2026-11-08 21:17:36 UTC
- **Run ID:** NOT_RUN
- **Manifest ID:** NOT_RUN
- **Status:** BLOCKED

## Actual vs Expected
- **Expected:** Pipeline executes successfully and generates a complete manifest bundle in `data/output/control/run_manifest`.
- **Actual:** Запуск не выполнялся (BLOCKED), так как сводный гейт LF1-09 отклонен (REJECTED) и поставка заблокирована.

## Dependencies
- **LF1-10 / #12806:** BLOCKED. Поставка отменена из-за LF1-09 REJECTED. (Отчет в `reports/observability/live-fixes-r6/LF1-10/report.md` не смог подтвердить поставку).
- **LF1-05 / #12801:** BLOCKED / NOT_VERIFIABLE (Живая приёмка отклонена, живая среда недоступна).
- **LF1-09 / #12805:** REJECTED. Поставка НЕ РАЗРЕШЕНА, контрольный запуск (ETL/downstream) НЕ РАЗРЕШЁН.

## Artifacts
Запуск не производился. Исторические артефакты остаются в каталоге, но новые не сгенерированы.
