# LF1-19 Processed Records DQ 9403 Audit Report

**Date:** 2026-11-08T19:22:28Z
**Base SHA:** 52cb6ea07ca5f2a4dbdaf3c34bf207539cef1e05
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
   - **Reason:** Live backend unavailable. Offline contract check on source SHA 3292de8d85240104d2c5e6f11e21986d362780bd. Command: python -m pytest -o addopts= -q --no-cov -p no:cacheprovider tests/unit/interfaces/http/test_processed_records_table.py. Exit code 0. 12 passed in 5.08s.
2. **L-09(в) классифицирован и закрыт решением/исправлением; unexplained row drift отсутствует.**
   - **Status:** BLOCKED / NOT_RUN
   - **Reason:** Requires querying two exact UUID runs in live system.
3. **Результат приложен как отчёт с exact source/deploy SHA, UTC, параметрами, expected/actual и ссылками на сохранённые доказательства.**
   - **Status:** BLOCKED
   - **Reason:** Execution halted due to blocked HTTP connection. See `audit.json` and `audit.log`. No JSON patching or codebase modifications applied since root cause is an unavailable live environment rather than a verified layer defect.

### Dependencies Status
- LF1-07 (#12803): Dependent component - Not evaluated here.
- LF1-15 (#12811): Dependent component - Not evaluated here.
