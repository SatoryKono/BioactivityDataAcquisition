# OBS-004: Emitter-Bypass Proof Gap

## Priority
**Medium Priority** - Cardinality policy enforcement gap

## Issue Type
Observability Architecture Gap

## Description
Deep Research Audit (2026-07-14) identified that while BioETL has strong label normalization and adapter checks, there is **no proof that all runtime emitters actually use the canonical observability contracts without side-door bypasses**. The residual risk is smaller than initially assessed but remains unverified.

## Current State
- ✅ Label normalization layer exists in PrometheusMetrics adapter
- ✅ Adapter fails loudly on unknown metric names
- ✅ Adapter rejects labels when metric definition doesn't declare any
- ✅ Domain ports defined: MetricsPort, TracingPort, LoggerPort, DQMonitorPort
- ✅ PipelineObserver described as canonical lifecycle emitter
- ✅ Cardinality policy documented (no run_id in Prometheus labels)
- ❌ **No proof that all emitters use canonical contracts**
- ❌ **No verification that side-door logger-only calls don't bypass contracts**
- ❌ **No audit of ad-hoc metric emission patterns**

## Cardinality Policy Strengths
The repository has materially stronger cardinality governance than documentation-only rules:
- **Runtime label normalization**: Adapter enforces label formatting
- **Metric name validation**: Unknown metrics cause adapter failures
- **Label contract enforcement**: Labels rejected if not declared in metric definition
- **Bounded vocabularies**: source_kind, operation, lifecycle stage/phase have canonical values
- **Correlation separation**: run_id kept in logging/tracing, forbidden in Prometheus labels

## Architectural Safeguards
- **PipelineObserver**: Canonical lifecycle emitter for ordinary runs
- **Typed domain events**: Projected into runtime observability vocabulary
- **Observer-owned metric**: bioetl_observability_events_total protected from generic reuse
- **Fail-closed bootstrap**: NoOpLogger/NoOpMetrics/NoOpTracing/NoOpAudit unless explicitly overridden

## Impact
- **Cardinality explosions**: Side-door emitters could introduce high-cardinality labels
- **Metric inconsistency**: Bypass patterns could create metric naming conflicts
- **Observability fragmentation**: Multiple emission paths reduce reliability
- **Policy violations**: Documented cardinality rules could be silently violated

## Audit Finding
> "Cardinality policy is stronger than first thought because label normalization and adapter checks exist, but emitter-bypass proof is still incomplete. The preliminary caution on 'normalizers do not prove the absence of side-door emitters' remains valid, although the residual risk is smaller than it looked before the code-level adapter checks were inspected."

## Required Evidence
1. **Emitter Audit**
   - [ ] All runtime emitters identified across codebase
   - [ ] Each emitter verified to use canonical ports (MetricsPort, TracingPort, LoggerPort)
   - [ ] No direct Prometheus client usage outside infrastructure layer
   - [ ] No ad-hoc logger-only calls that bypass structured logging contracts

2. **Contract Compliance**
   - [ ] All metric emissions go through PrometheusMetrics adapter
   - [ ] All tracing emissions go through TracingPort implementation
   - [ ] All logging emissions use LoggerPort structured methods
   - [ ] All DQ monitoring uses DQMonitorPort typed methods

3. **Side-Door Detection**
   - [ ] Static analysis for direct Prometheus client imports outside infrastructure
   - [ ] Code review for logger-only calls that should use observer pattern
   - [ ] Audit of metric name usage against declared metric contracts

4. **Runtime Verification**
   - [ ] Verify actual emitted metrics match contract expectations
   - [ ] Confirm no unexpected metric names appear in Prometheus
   - [ ] Validate label cardinality stays within expected bounds

## Acceptance Criteria
1. **Static Analysis**
   - [ ] Import-linter rule for observability layer boundaries
   - [ ] Architecture test for forbidden direct Prometheus usage
   - [ ] Code review checklist for observability contract compliance

2. **Runtime Monitoring**
   - [ ] Alert on unexpected metric names in Prometheus
   - [ ] Monitor label cardinality growth patterns
   - [ ] Track metric emission patterns for anomalies

3. **Documentation Updates**
   - [ ] Document approved emitter patterns
   - [ ] Provide examples of correct contract usage
   - [ ] Create anti-pattern catalog for code review

## Proposed Solution
1. **Static Analysis Rules**
   - Add import-linter rules to enforce observability layer boundaries
   - Create architecture tests for forbidden direct Prometheus client usage
   - Implement code scanning for side-door emission patterns

2. **Runtime Guards**
   - Extend PrometheusMetrics adapter to emit warnings on unexpected metric names
   - Add cardinality monitoring for label growth patterns
   - Implement metric emission audit logging

3. **Code Review Process**
   - Add observability contract compliance to PR checklist
   - Create examples of correct vs incorrect emission patterns
   - Document anti-patterns to watch for

## Related Issues
- OBS-003: Live Grafana/Prometheus validation
- OBS-002: Metric-to-panel runtime proof
- OBS-006: Live datasource compliance verification

## Audit Reference
Deep Research Audit of BioETL GitHub Observability Documentation (2026-07-14)
Finding ID: OBS-004 (Open, reduced confidence of failure)

## Labels
`observability`, `architecture`, `cardinality`, `contracts`, `validation`, `static-analysis`
