# OBS-003: Live Grafana/Prometheus Validation Gap

## Priority
**Highest Priority** - Critical observability validation gap

## Issue Type
Observability Validation Gap

## Description
Deep Research Audit (2026-07-14) identified that while BioETL has comprehensive static observability artifacts (dashboards, rules, contracts, CI checks), there is **no evidence of live runtime validation** for Grafana/Prometheus functionality. The repository proves artifacts exist but does not prove they work in a live environment.

## Current State
- ✅ Static artifacts exist: 8 shipped dashboards, Prometheus rules, selector contracts
- ✅ CI checks validate docs-to-JSON parity, dashboard inventory, selector contracts
- ✅ Domain ports implemented: MetricsPort, TracingPort, LoggerPort, DQMonitorPort
- ✅ Infrastructure adapters exist: PrometheusMetrics, tracing implementations
- ❌ **No live Prometheus target health evidence**
- ❌ **No live /api/v1/query results verification**
- ❌ **No Grafana datasource availability confirmation**
- ❌ **No rendered panel correctness validation**
- ❌ **No end-to-end runtime emitter → Prometheus sample → Grafana visualization proof**

## Impact
- **Operational risk**: Dashboards may fail to render in production
- **Monitoring blind spots**: Critical metrics may not be collected or visualized
- **False confidence**: Strong static governance masks runtime gaps
- **Incident response**: Alerts may not fire or may fire incorrectly

## Audit Finding
> "The repository proves the existence of static artifacts, policies, contracts, and validation tooling. It does not prove that a live BioETL runtime currently scrapes cleanly, renders correctly, or emits the expected samples under representative pipeline runs."

## Required Evidence
The following validation surfaces exist in the repository but lack execution evidence:
- `check-grafana-audit-preflight` - pre-flight dashboard validation
- `audit-live-grafana` - live Grafana audit
- `rerender-grafana` - dashboard rendering verification
- `observability-checklist` - procedure for verifying logs, metrics, alerts, dashboards

## Acceptance Criteria
1. **Live Prometheus Validation**
   - [ ] All Prometheus targets are healthy (UP state)
   - [ ] `/api/v1/query` returns expected metric samples
   - [ ] Metric names match declared metric contracts
   - [ ] Label values conform to normalization rules

2. **Live Grafana Validation**
   - [ ] All datasources (Prometheus, Loki, Quarantine Explorer) are available
   - [ ] All 8 dashboards render without errors
   - [ ] No panels show "No data" unexpectedly
   - [ ] Dashboard queries return valid time-series data

3. **End-to-End Pipeline Validation**
   - [ ] Representative pipeline runs (chembl_activity, chembl_assay, chembl_molecule, chembl_target)
   - [ ] Runtime emitters → Prometheus samples chain verified
   - [ ] Prometheus samples → Grafana visualization chain verified
   - [ ] Alert rules fire correctly on test conditions

4. **Automated Runtime Checks**
   - [ ] CI/CD pipeline includes live validation for Grafana/Prometheus
   - [ ] Automated screenshot capture for dashboard regression testing
   - [ ] Runtime metric contract validation against live Prometheus

## Proposed Solution
1. **Immediate**: Execute existing validation commands in staging environment
2. **Short-term**: Add live validation to CI/CD pipeline
3. **Long-term**: Implement continuous runtime observability health checks

## Related Issues
- OBS-002: Metric-to-panel mapping runtime proof
- OBS-004: Emitter-bypass proof
- OBS-006: Live datasource compliance verification

## Audit Reference
Deep Research Audit of BioETL GitHub Observability Documentation (2026-07-14)
Finding ID: OBS-003 (Open, highest priority)

## Labels
`observability`, `validation`, `critical`, `grafana`, `prometheus`, `runtime`
