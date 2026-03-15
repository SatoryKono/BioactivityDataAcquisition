# Consolidated Review — S5: Cross-cutting
**Date**: 2026-03-15
**Sub-reviews**: 5 agents
**Status**: FAIL
**Consolidated Score**: 5.5/10.0

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S5.1 — Cross-cutting Core | 1079 | 5.5 | FAIL | 0 | 32 |

## Aggregated Issues
### Critical (MUST fix)

### High
- **ARCH-009**: src/bioetl/infrastructure/adapters/common/api_request_collector.py:67 - datetime.now() used in infrastructure layer
- **ARCH-009**: src/bioetl/infrastructure/storage/metadata_builder.py:76 - datetime.now() used in infrastructure layer
- **ARCH-009**: src/bioetl/infrastructure/storage/metadata_builder.py:235 - datetime.now() used in infrastructure layer
- **ARCH-009**: src/bioetl/infrastructure/storage/metadata_builder.py:303 - datetime.now() used in infrastructure layer
- **ARCH-009**: src/bioetl/infrastructure/storage/silver_writer.py:197 - datetime.now() used in infrastructure layer
- **ARCH-003**: src/bioetl/domain/ports/health_check.py:31 - Class 'HealthCheckResult' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/audit.py:28 - Class 'AuditOperation' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/audit.py:47 - Class 'AuditLayer' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/audit.py:61 - Class 'AuditEntry' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/adr.py:18 - Class 'AdrInfo' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/adr.py:27 - Class 'AdrDocument' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/adr.py:39 - Class 'AdrValidationIssue' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/adr.py:49 - Class 'AdrValidationReport' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/metadata/coordinator.py:38 - Class 'BronzeMetadataInput' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/metadata/coordinator.py:67 - Class 'SilverMetadataInput' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/metadata/coordinator.py:118 - Class 'SilverRef' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/metadata/coordinator.py:136 - Class 'GoldMetadataInput' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/runtime/pipeline_debug.py:22 - Class 'StageBreakpoint' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/runtime/pipeline_debug.py:34 - Class 'DebugAction' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/runtime/pipeline_debug.py:45 - Class 'PipelineSnapshot' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/runtime/pipeline_debug.py:76 - Class 'BreakpointHit' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/runtime/memory.py:14 - Class 'MemoryStats' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/noop/_tracing.py:11 - Class '_NoOpSpan' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/noop/_tracing.py:63 - Class '_NoOpOtelTracer' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/noop/_tracing.py:83 - Class 'NoOpTracing' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/noop/_memory_metadata.py:18 - Class 'NoOpMemoryMonitor' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/noop/_memory_metadata.py:77 - Class 'NoOpMetadataWriter' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/noop/_audit_pii.py:13 - Class 'NoOpAudit' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/noop/_audit_pii.py:53 - Class 'NoOpPiiHasher' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/noop/_metrics.py:11 - Class 'NoOpMetrics' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/noop/_debug.py:15 - Class 'NoOpDebug' in domain/ports must end with Port
- **ARCH-003**: src/bioetl/domain/ports/quality/quarantine.py:27 - Class 'QuarantineWriteRequest' in domain/ports must end with Port

## Top 5 Recommendations
1. Fix all critical issues immediately.
2. Address high-priority architectural violations.
