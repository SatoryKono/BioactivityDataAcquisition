# BioETL Observability Audit Issues

## Overview
This directory contains GitHub issue specifications based on the Deep Research Audit of BioETL GitHub Observability Documentation (2026-07-14). Each issue corresponds to an open finding from the audit that requires remediation.

## Audit Summary
The audit found that BioETL has **strong static governance** (comprehensive documentation, machine-readable contracts, CI checks) but **lacks runtime validation evidence**. The repository proves artifacts exist but does not prove they work in live environments.

## Issue Priority Matrix

| Issue ID | Priority | Focus Area | Status |
|----------|-----------|-------------|--------|
| OBS-003 | **Highest** | Live Grafana/Prometheus validation | Open |
| OBS-002 | High | Metric-to-panel runtime proof | Open |
| OBS-004 | Medium | Emitter-bypass proof | Open |
| OBS-006 | Medium | Live datasource compliance | Open |

## Issue Details

### OBS-003: Live Grafana/Prometheus Validation Gap (Highest Priority)
**Problem**: No evidence that dashboards actually work in live environments despite strong static artifacts.

**Key Gaps**:
- No live Prometheus target health verification
- No live Grafana datasource availability confirmation
- No rendered panel correctness validation
- No end-to-end runtime emitter → Prometheus sample → Grafana visualization proof

**Acceptance Criteria**:
- All Prometheus targets healthy (UP state)
- All datasources available
- All 8 dashboards render without errors
- End-to-end pipeline validation with representative runs

**File**: `OBS-003-live-validation.md`

### OBS-002: Metric-to-Panel Mapping Runtime Proof (High Priority)
**Problem**: No runtime verification that declared metrics actually appear in correct dashboards.

**Key Gaps**:
- No verification that metrics flow to expected panels
- No proof that panel queries return actual data
- No validation of metric-to-panel mapping under load

**Acceptance Criteria**:
- Script to verify all declared metrics exist in Prometheus
- Script to validate all panel queries return data
- CI check for metric-to-panel mapping consistency

**File**: `OBS-002-metric-to-panel-runtime.md`

### OBS-004: Emitter-Bypass Proof Gap (Medium Priority)
**Problem**: No proof that all runtime emitters use canonical observability contracts without side-door bypasses.

**Key Gaps**:
- No verification that all emitters use canonical ports
- No audit of ad-hoc metric emission patterns
- No detection of side-door logger-only calls

**Acceptance Criteria**:
- Static analysis rules for observability layer boundaries
- Architecture tests for forbidden direct Prometheus usage
- Runtime monitoring for unexpected metric names

**File**: `OBS-004-emitter-bypass-proof.md`

### OBS-006: Live Datasource Compliance Verification Gap (Medium Priority)
**Problem**: No live environment verification that datasources comply with documented separation policies.

**Key Gaps**:
- No live verification of datasource availability
- No proof that runtime queries respect datasource boundaries
- No validation of cross-datasource handoff integrity

**Acceptance Criteria**:
- Script to test all datasource connections
- Validation of query execution per datasource type
- Monitoring for boundary-violating query patterns

**File**: `OBS-006-live-datasource-compliance.md`

## Creating GitHub Issues

### Manual Process
For each issue file:
1. Copy the content from the corresponding `.md` file
2. Create a new GitHub issue using the content
3. Apply the suggested labels from the issue file
4. Link related issues as specified

### Suggested GitHub Issue Flow
1. **Start with OBS-003** (highest priority) - Live validation foundation
2. **Then OBS-002** - Build on live validation to test metric-to-panel mapping
3. **Then OBS-006** - Extend validation to datasource compliance
4. **Finally OBS-004** - Add static analysis guards after runtime validation is working

## Closed Audit Findings
The following findings were **closed or downgraded** based on strong static evidence:

- **OBS-001**: Closed for static inventory (8 dashboards documented, not 7)
- **OBS-005**: Downgraded (documentation drift risk reduced by CI parity checks)

## Audit Reference
Deep Research Audit of BioETL GitHub Observability Documentation (2026-07-14)

## Next Steps
1. Review each issue file for completeness
2. Create GitHub issues in priority order
3. Assign to appropriate team members
4. Track progress against acceptance criteria
5. Update audit findings as issues are resolved
