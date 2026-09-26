# Итерация 9 — residual и telemetry gates

`surface_score: 1/3`.

`report_live_residual_snapshot --check` ложно пропускал closeout/module metrics, которые отдельно блокировал architecture test. `TEST-SYS-009` исправлен общим ratchet helper и regression test. Telemetry baseline остаётся stale (`TEST-SYS-010`) до восстановления CI artifacts.
