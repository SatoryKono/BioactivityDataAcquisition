# Consolidated Review — S1: Domain
**Date**: 2026-03-15
**Sub-reviews**: 5 agents
**Status**: PASS
**Consolidated Score**: 9.2/10.0

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S1.1 — ports, contracts | 79 | 6.8 | WARN | 0 | 27 |
| S1.2 — entities, value_objects | 66 | 9.8 | PASS | 0 | 0 |
| S1.3 — schemas | 41 | 10.0 | PASS | 0 | 0 |
| S1.4 — services, filtering, mapping | 50 | 10.0 | PASS | 0 | 0 |
| S1.5 — config, composite, exceptions, other | 113 | 9.9 | PASS | 0 | 0 |

## Aggregated Issues
### Critical (MUST fix)

### High
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
