# OBS-006: Live Datasource Compliance Verification Gap

## Priority
**Medium Priority** - Datasource boundary enforcement gap

## Issue Type
Observability Validation Gap

## Description
Deep Research Audit (2026-07-14) identified that while BioETL has strong datasource boundary documentation and JSON contracts, there is **no live environment verification that datasources actually comply with documented separation policies**. The static evidence is strong but runtime compliance remains unverified.

## Current State
- ✅ Datasource boundary documented: Prometheus/Grafana for aggregate questions
- ✅ Forensic boundary documented: Manifest/ledger/CLI/explorer for record-level forensics
- ✅ Selector contracts: run_id as control-plane identity, not Prometheus label
- ✅ Dashboard JSON matches boundary rules in description and panel configurations
- ✅ Silver Reject Explorer uses quarantine_run_id/payload_hash as forensic-only filters
- ✅ Tempo exists as Explore-side adjunct, not first-class panel datasource
- ❌ **No live verification of datasource availability**
- ❌ **No proof that runtime queries respect datasource boundaries**
- ❌ **No validation of cross-datasource handoff integrity**

## Datasource Architecture
### Aggregate Questions (Prometheus/Grafana)
- Operational health metrics
- Pipeline performance trends
- Alert/SLO monitoring
- Control-plane status

### Forensic Questions (Manifest/Ledger/CLI/Explorer)
- Exact record-level forensics
- Replay evidence
- Quarantine payload inspection
- Run identity resolution

### Boundary Enforcement
- **run_id handling**: Control-plane identity context, not Prometheus label
- **Dashboard links**: Preserve identity through explicit var-* handoffs
- **Explorer surfaces**: Quarantine Explorer backend for forensic queries
- **Tempo integration**: Explore-side adjunct, not direct panel datasource

## Shipped Datasource Usage
8 dashboards with datasource configurations:
- **bioetl-control-plane-v1**: Prometheus, Quarantine Explorer, Grafana
- **bioetl-overview-v2**: Prometheus, Quarantine Explorer, Grafana
- **bioetl-runtime**: Prometheus, Loki, Quarantine Explorer, Grafana
- **bioetl-provider-health-v2**: Prometheus, Quarantine Explorer, Grafana
- **bioetl-dq-v2**: Prometheus, Quarantine Explorer, Grafana
- **bioetl-workflow-overview**: Prometheus, Quarantine Explorer, Grafana
- **bioetl-silver-reject-explorer**: Prometheus, Quarantine Explorer, Grafana
- **bioetl-alerts-slo**: Prometheus, Grafana

## Impact
- **Boundary violations**: Runtime queries may bypass documented separation
- **Performance issues**: Forensic queries on Prometheus could cause performance problems
- **Data consistency**: Cross-datasource handoffs may fail silently
- **Operational confusion**: Operators may misuse datasources contrary to design

## Audit Finding
> "Datasource boundary is strongly encoded in docs/contracts/JSON, but live datasource compliance still needs environment verification."

## Required Evidence
1. **Datasource Availability**
   - [ ] Prometheus datasource is reachable and queries return data
   - [ ] Loki datasource is reachable and log queries work
   - [ ] Quarantine Explorer datasource is reachable and forensic queries work
   - [ ] Grafana datasource integration is functional

2. **Boundary Compliance**
   - [ ] No forensic queries routed to Prometheus in runtime
   - [ ] No aggregate queries routed to Quarantine Explorer inappropriately
   - [ ] run_id remains control-plane identity, not Prometheus label
   - [ ] Dashboard var-* handoffs preserve identity correctly

3. **Cross-Datasource Integrity**
   - [ ] Dashboard links work across datasource boundaries
   - [ ] Selector variables resolve correctly in their intended datasources
   - [ ] Tempo integration works as Explore-side adjunct only

4. **Runtime Performance**
   - [ ] Forensic queries don't impact Prometheus performance
   - [ ] Aggregate queries remain performant with expected data volumes
   - [ ] Datasource query timeouts are appropriately configured

## Acceptance Criteria
1. **Live Datasource Validation**
   - [ ] Script to test all datasource connections
   - [ ] Validation of query execution per datasource type
   - [ ] Performance testing for boundary-compliant query patterns

2. **Boundary Enforcement Verification**
   - [ ] Audit of runtime queries for datasource compliance
   - [ ] Monitoring for boundary-violating query patterns
   - [ ] Alert on inappropriate datasource usage

3. **Handoff Integrity Testing**
   - [ ] Test all dashboard cross-datasource links
   - [ ] Verify selector variable resolution across datasources
   - [ ] Validate run_id handoff through control-plane integration

## Proposed Solution
1. **Create datasource validation script** that:
   - Tests connectivity to all configured datasources
   - Validates query execution per datasource type
   - Checks for boundary-violating query patterns
   - Tests cross-datasource handoffs

2. **Add to observability checklist** for environment validation

3. **Implement runtime monitoring** for datasource compliance

## Related Issues
- OBS-003: Live Grafana/Prometheus validation (parent issue)
- OBS-002: Metric-to-panel runtime proof
- OBS-004: Emitter-bypass proof

## Audit Reference
Deep Research Audit of BioETL GitHub Observability Documentation (2026-07-14)
Finding ID: OBS-006 (Partially closed statically, open at runtime)

## Labels
`observability`, `validation`, `datasource`, `grafana`, `prometheus`, `runtime`, `boundaries`
