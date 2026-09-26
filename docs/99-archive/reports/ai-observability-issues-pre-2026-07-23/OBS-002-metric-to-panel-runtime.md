# OBS-002: Metric-to-Panel Mapping Runtime Proof Gap

## Priority
**High Priority** - Important observability validation gap

## Issue Type
Observability Validation Gap

## Description
Deep Research Audit (2026-07-14) identified that while BioETL has comprehensive metric-to-panel documentation and machine-readable metric declarations, there is **no runtime proof that declared metrics actually appear in the correct dashboards with expected panel configurations**.

## Current State
- ✅ Metric declarations exist in machine-readable format
- ✅ Dashboard JSON files contain panel configurations
- ✅ Documentation describes metric-to-panel relationships
- ✅ CI checks validate dashboard inventory and panel titles
- ❌ **No runtime verification that metrics flow to expected panels**
- ❌ **No proof that panel queries return actual data**
- ❌ **No validation of metric-to-panel mapping under load**

## Metric Surface Analysis
The repository defines metric families including:
- Adapter request latency and request counts
- Adapter batch size and fallback metrics
- Health-check counters and latency histograms
- Observer event counters
- Workflow runs/steps
- DQ validation metrics
- Processed-record metrics
- Operational telemetry (replay lag, control-plane reads)

## Dashboard Inventory
8 shipped dashboards with panel counts:
- bioetl-control-plane-v1: 57 panels
- bioetl-overview-v2: 25 panels
- bioetl-runtime: 42 panels
- bioetl-provider-health-v2: 29 panels
- bioetl-dq-v2: 36 panels
- bioetl-workflow-overview: 16 panels
- bioetl-silver-reject-explorer: 16 panels
- bioetl-alerts-slo: 7 panels

## Impact
- **Visualization gaps**: Declared metrics may not reach intended dashboards
- **Silent failures**: Broken metric-to-panel mappings may go undetected
- **Operational confusion**: Operators may trust empty or incorrect panels
- **Alert effectiveness**: Alert rules may reference non-existent metrics

## Audit Finding
> "Metric-to-panel mapping is substantially documented, but end-to-end runtime proof is still missing."

## Required Evidence
1. **Metric Existence Verification**
   - [ ] Each declared metric family appears in Prometheus `/api/v1/label/__name__/values`
   - [ ] Metric samples are present for representative time ranges
   - [ ] Metric labels conform to declared contracts

2. **Panel Query Validation**
   - [ ] Each panel's PromQL returns valid time-series data
   - [ ] Panel queries reference metrics that actually exist
   - [ ] No panels show "No data" due to missing metrics

3. **Mapping Consistency**
   - [ ] Documented metric-to-panel relationships match runtime reality
   - [ ] Metric declarations align with actual Prometheus metadata
   - [ ] Panel configurations use correct metric names and label combinations

4. **Runtime Stress Testing**
   - [ ] Metric-to-panel mappings hold under representative load
   - [ ] High-cardinality scenarios don't break visualizations
   - [ ] Dashboard performance remains acceptable with real data volumes

## Acceptance Criteria
1. **Automated Validation**
   - [ ] Script to verify all declared metrics exist in Prometheus
   - [ ] Script to validate all panel queries return data
   - [ ] CI check for metric-to-panel mapping consistency

2. **Runtime Verification**
   - [ ] Execute validation in staging environment
   - [ ] Capture evidence of metric-to-panel data flow
   - [ ] Document any discrepancies and remediation steps

3. **Continuous Monitoring**
   - [ ] Add metric-to-panel health checks to observability stack
   - [ ] Alert on missing metrics or broken panel queries
   - [ ] Regular audit of metric-to-panel mapping consistency

## Proposed Solution
1. **Create validation script** that:
   - Loads metric declarations from machine-readable format
   - Queries Prometheus for metric existence
   - Validates each panel query in dashboard JSON
   - Reports missing metrics and broken queries

2. **Add to CI/CD pipeline** for pre-deployment validation

3. **Implement runtime monitoring** for metric-to-panel health

## Related Issues
- OBS-003: Live Grafana/Prometheus validation (parent issue)
- OBS-004: Emitter-bypass proof
- OBS-006: Live datasource compliance verification

## Audit Reference
Deep Research Audit of BioETL GitHub Observability Documentation (2026-07-14)
Finding ID: OBS-002 (Open)

## Labels
`observability`, `validation`, `metrics`, `dashboards`, `runtime`, `prometheus`
