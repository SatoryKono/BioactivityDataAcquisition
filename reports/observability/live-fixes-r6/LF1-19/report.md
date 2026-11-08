# LF1-19 Processed Records DQ 9403 Audit Report

**Date:** 2026-11-08T09:12:53Z
**Base SHA:** 2540264745315b52f419c2c936603025d9f64754
**Execution Status:** BLOCKED (blocked_backend_unavailable)

## Context
This report covers issue LF1-19 for evaluating the `Processed Records` table on `bioetl-dq-v2#9403` dashboard against its contract specifications based on live run data.

## Diagnostics
Running the live panel audit failed with `blocked_backend_unavailable`. The BioETL Ops HTTP backend could not be reached via canonical health probes.

```text
bioetl-dq-v2#9403 Processed Records: error/blocked_backend_unavailable
bioetl-dq-v2#9403 Inspect Processed Records: ok/blocked_backend_unavailable
```

## Checklist Results

1. **Числовые колонки соответствуют спецификации и API.**
   - **Status:** BLOCKED / NOT_VERIFIABLE
   - **Reason:** Live backend unavailable. Contract format validation (`tests/unit/interfaces/http/test_processed_records_table.py`) passes offline.
2. **L-09(в) классифицирован и закрыт решением/исправлением; unexplained row drift отсутствует.**
   - **Status:** BLOCKED / NOT_RUN
   - **Reason:** Requires querying two exact UUID runs in live system.
3. **Результат приложен как отчёт с exact source/deploy SHA, UTC, параметрами, expected/actual и ссылками на сохранённые доказательства.**
   - **Status:** BLOCKED
   - **Reason:** Execution halted due to blocked HTTP connection. See `audit.json` and `audit.log`. No JSON patching or codebase modifications applied since root cause is an unavailable live environment rather than a verified layer defect.

### Dependencies Status
- LF1-07 (#12803): Dependent component - Not evaluated here.
- LF1-15 (#12811): Dependent component - Not evaluated here.
