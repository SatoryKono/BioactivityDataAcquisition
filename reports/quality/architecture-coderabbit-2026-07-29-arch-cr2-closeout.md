# ARCH-CR2 closeout — 2026-07-29

| Field | Value |
| --- | --- |
| Epic | #7005 |
| Children | #7006–#7014 |
| Audit | `reports/grok/review_coderabbit_architecture_audit_20260728_1520_FINAL.md` |

## Delivered

| Issue | Status | Evidence |
| --- | --- | --- |
| #7006 CR2-01 | done | `read_bronze` uses `asyncio.to_thread`; write/list/cleanup already offloaded |
| #7007 CR2-02 | done | Strict hydration raises `ValueError`; removed bare `RuntimeError` from lifecycle catch |
| #7008 CR2-03 | done | Quarantine resolved before `build_health_server` |
| #7009 CR2-04 | done | Maintenance commands `copy.copy` before rename |
| #7010 CR2-05 | done | Unit tests for bronze offload, hydration, health order, maintenance non-mutation |
| #7011 CR2-06 | done | Storage mixins typed host attrs; health_service_access cast note |
| #7012 CR2-07 | done | TOOLS CodeRabbit section; ADR-052/053 Migration+Rollback; rules-summary SSOT |
| #7013 CR2-08 | rejected/no-op | pytest closeout globs already cover flat paths; scorecard counters not raised |
| #7014 CR2-09 | done | Live residual closeout JSON must be non-empty parseable objects |

## Tests

```text
pytest tests/unit/infrastructure/storage/test_arch_cr2_bronze_async_offload.py \
  tests/unit/application/services/control_plane/manifest/test_arch_cr2_hydration_strict.py \
  tests/unit/interfaces/cli/commands/domains/test_arch_cr2_health_and_maintenance.py \
  tests/architecture/test_live_residual_snapshot.py::test_historical_tech_debt_closeout_json_artifacts_remain_present
```

Result: green.

## Constraints

- No tech-debt budget growth
- Domain purity preserved
