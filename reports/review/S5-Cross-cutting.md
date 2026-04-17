# Consolidated Review — S5: Cross-cutting

**Date**: 2026-04-17
**Sub-reviews**: 4 agents
**Status**: PASS
**Consolidated Score**: 8.3

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S5.1 — Cross Domain | 465 | 7.6 | WARN | 0 | 7 |
| S5.2 — Cross Application | 437 | 10.0 | PASS | 0 | 4 |
| S5.3 — Cross Infrastructure | 418 | 7.0 | WARN | 4 | 2 |
| S5.4 — Cross Other | 278 | 8.6 | PASS | 0 | 5 |

## Aggregated Issues
### Critical (MUST fix)
1. **AP-001** in `src/bioetl/infrastructure/export/dq_report_writer.py:59` - Hard-coded dependency instantiation: DQReportSerializer()
2. **AP-001** in `src/bioetl/infrastructure/observability/tracing.py:258` - Hard-coded dependency instantiation: TracerProvider()
3. **AP-001** in `src/bioetl/infrastructure/observability/anomaly/monitor.py:61` - Hard-coded dependency instantiation: AnomalyDetector()
4. **AP-001** in `src/bioetl/infrastructure/validation/contract_validator.py:312` - Hard-coded dependency instantiation: PanderaSilverValidator()

### High Issues
1. **TYPE-001** in `src/bioetl/domain/normalization/profiles/chembl_activity.py:35` - Public function 'create_case_normalizer' lacks return type annotation.
2. **TYPE-001** in `src/bioetl/domain/normalization/profiles/chembl_activity.py:44` - Public function 'normalizer' lacks return type annotation.
3. **TYPE-001** in `src/bioetl/domain/normalization/profiles/chembl_assay.py:64` - Public function 'create_case_normalizer' lacks return type annotation.
4. **ARCH-003** in `src/bioetl/domain/ports/publication_strategy.py:19` - Protocol DataExtractorStrategy in domain/ports must end with 'Port'.
5. **ARCH-003** in `src/bioetl/domain/ports/publication_strategy.py:41` - Protocol IdentifierResolverStrategy in domain/ports must end with 'Port'.
6. **ARCH-003** in `src/bioetl/domain/ports/publication_strategy.py:63` - Protocol PublicationMetadataStrategy in domain/ports must end with 'Port'.
7. **TYPE-002** in `src/bioetl/domain/exceptions/base_exceptions.py:41` - Usage of Any without comment justification.
8. **TYPE-002** in `src/bioetl/application/services/error_handler.py:205` - Usage of Any without comment justification.
9. **TYPE-002** in `src/bioetl/application/services/error_handler.py:160` - Usage of Any without comment justification.
10. **TYPE-002** in `src/bioetl/application/composite/merger_input_mixin.py:41` - Usage of Any without comment justification.
11. **TYPE-002** in `src/bioetl/application/composite/merger_input_mixin.py:42` - Usage of Any without comment justification.
12. **TYPE-002** in `src/bioetl/infrastructure/storage/silver_writer.py:421` - Usage of Any without comment justification.
13. **TYPE-001** in `src/bioetl/infrastructure/storage/silver/operations/metadata_operations.py:488` - Public function 'logger' lacks return type annotation.
14. **AP-002** in `src/bioetl/composition/bootstrap_logger.py:25` - Direct import of structlog outside infrastructure.
15. **TYPE-002** in `src/bioetl/composition/monitoring/deprecation_tracker.py:28` - Usage of Any without comment justification.
16. **TYPE-002** in `src/bioetl/composition/monitoring/deprecation_tracker.py:28` - Usage of Any without comment justification.
17. **TYPE-001** in `src/bioetl/composition/factories/services/polars_join_adapter.py:23` - Public function 'get_polars_join_type' lacks return type annotation.
18. **TYPE-001** in `src/bioetl/composition/factories/services/polars_join_adapter.py:27` - Public function 'execute_polars_join' lacks return type annotation.

## Cross-subzone Observations
- Needs manual review of sub-reports to identify cross-subzone patterns.

## Top Recommendations
1. Address CRITICAL issues in sub-reports immediately.
