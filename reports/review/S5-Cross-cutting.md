# Consolidated Review — S5: Cross-cutting

**Date**: 2026-04-06
**Sub-reviews**: 4 agents
**Status**: PASS
**Consolidated Score**: 8.1

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S5.1 — Cross Domain | 412 | 7.9 | WARN | 0 | 4 |
| S5.2 — Cross Application | 372 | 10.0 | PASS | 0 | 1 |
| S5.3 — Cross Infrastructure | 395 | 6.5 | WARN | 12 | 3 |
| S5.4 — Cross Other | 252 | 8.3 | PASS | 0 | 3 |

## Aggregated Issues
### Critical (MUST fix)
1. **AP-001** in `src/bioetl/infrastructure/export/csv_exporter.py:85` - Hard-coded dependency instantiation: Path()
2. **AP-001** in `src/bioetl/infrastructure/export/dq_report_writer.py:57` - Hard-coded dependency instantiation: Path()
3. **AP-001** in `src/bioetl/infrastructure/export/dq_report_writer.py:59` - Hard-coded dependency instantiation: DQReportSerializer()
4. **AP-001** in `src/bioetl/infrastructure/observability/tracing.py:257` - Hard-coded dependency instantiation: TracerProvider()
5. **AP-001** in `src/bioetl/infrastructure/observability/anomaly/monitor.py:67` - Hard-coded dependency instantiation: AnomalyDetector()
6. **AP-001** in `src/bioetl/infrastructure/validation/contract_validator.py:312` - Hard-coded dependency instantiation: PanderaSilverValidator()
7. **AP-001** in `src/bioetl/infrastructure/checkpoint/local_checkpoint.py:51` - Hard-coded dependency instantiation: Path()
8. **AP-001** in `src/bioetl/infrastructure/storage/delta_reader.py:50` - Hard-coded dependency instantiation: Path()
9. **AP-001** in `src/bioetl/infrastructure/storage/base_delta_writer.py:191` - Hard-coded dependency instantiation: ArrowDataConverter()
10. **AP-001** in `src/bioetl/infrastructure/storage/base_delta_writer.py:192` - Hard-coded dependency instantiation: RetentionPolicy()
11. **AP-001** in `src/bioetl/infrastructure/storage/bronze_writer.py:156` - Hard-coded dependency instantiation: Path()
12. **AP-001** in `src/bioetl/infrastructure/audit/file_audit.py:63` - Hard-coded dependency instantiation: Path()
