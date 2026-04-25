# Consolidated Review — S5: Cross-cutting

**Date**: 2026-04-18
**Sub-reviews**: 4 agents
**Status**: PASS
**Consolidated Score**: 8.4

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S5.1 — Cross Domain | 469 | 7.7 | WARN | 0 | 6 |
| S5.2 — Cross Application | 437 | 10.0 | PASS | 0 | 0 |
| S5.3 — Cross Infrastructure | 418 | 7.1 | WARN | 4 | 1 |
| S5.4 — Cross Other | 279 | 8.8 | PASS | 0 | 3 |

## Aggregated Issues
### Critical (MUST fix)
1. **AP-001** in `src/bioetl/infrastructure/export/dq_report_writer.py:59` - Hard-coded dependency instantiation: DQReportSerializer()
2. **AP-001** in `src/bioetl/infrastructure/observability/tracing.py:260` - Hard-coded dependency instantiation: TracerProvider()
3. **AP-001** in `src/bioetl/infrastructure/observability/anomaly/monitor.py:61` - Hard-coded dependency instantiation: AnomalyDetector()
4. **AP-001** in `src/bioetl/infrastructure/validation/contract_validator.py:312` - Hard-coded dependency instantiation: PanderaSilverValidator()

### High
1. **TYPE-001** in `src/bioetl/domain/normalization/profiles/chembl_activity.py:39` - Public function 'create_case_normalizer' lacks return type annotation.
2. **TYPE-001** in `src/bioetl/domain/normalization/profiles/chembl_activity.py:49` - Public function 'normalizer' lacks return type annotation.
3. **TYPE-001** in `src/bioetl/domain/normalization/profiles/chembl_assay.py:64` - Public function 'create_case_normalizer' lacks return type annotation.
4. **ARCH-003** in `src/bioetl/domain/ports/publication_strategy.py:19` - Protocol DataExtractorStrategy in domain/ports must end with 'Port'.
5. **ARCH-003** in `src/bioetl/domain/ports/publication_strategy.py:41` - Protocol IdentifierResolverStrategy in domain/ports must end with 'Port'.
6. **ARCH-003** in `src/bioetl/domain/ports/publication_strategy.py:69` - Protocol PublicationMetadataStrategy in domain/ports must end with 'Port'.
7. **TYPE-001** in `src/bioetl/infrastructure/storage/silver/operations/metadata_operations.py:497` - Public function 'logger' lacks return type annotation.
8. **AP-002** in `src/bioetl/composition/bootstrap_logger.py:25` - Direct import of structlog outside infrastructure.
9. **TYPE-001** in `src/bioetl/composition/factories/services/polars_join_adapter.py:23` - Public function 'get_polars_join_type' lacks return type annotation.
10. **TYPE-001** in `src/bioetl/composition/factories/services/polars_join_adapter.py:27` - Public function 'execute_polars_join' lacks return type annotation.

## Cross-subzone Observations
No significant cross-subzone issues found.

## Top 5 Recommendations
1. Address critical issues immediately.
2. Review high issues.
