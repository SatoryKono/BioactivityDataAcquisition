______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-28'

______________________________________________________________________

# ADR-053: Optional Grafana Scenes App Shell as Presentation Adapter

**Date:** 2026-07-28  
**Status:** Accepted  
**Decision makers:** @BioETL-Team  
**Related:** [ADR-010](ADR-010-local-only-deployment.md), [ADR-017](ADR-017-observability-architecture.md)  
**Epic:** [#6901](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6901) (DS2-00)  
**Issue:** [#6911](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6911) (DS2-10)

## Context

BioETL ships a fixed portfolio of **seven** provisioned Grafana dashboards
(`grafana/dashboards/*.json`) as the operator observability surface. Grafana is
**optional** under ADR-010. Dashboard Residual Migration (DRM/DRM-R) and DS2
Wave 0–1 repaired truth/render defects and compressed decision surfaces on JSON.

A North Star redesign proposes six task/object workspaces (Operations Home,
Incident Console, Pipeline Flow, Dependency Health, Data Trust & Recovery, Run
Explorer) implemented as a Grafana App Plugin + Scenes shell with better routing
than numbered canvas navigation.

Risks without an ADR:

- Scenes app becomes a second control plane or invents metrics
- Seven stable UIDs are deleted before parity/usage evidence
- Optional observability surface becomes a required deploy dependency

## Decision

1. **Optional presentation adapter only.** A Grafana App Plugin + Scenes shell
   MAY be introduced as a **read-only** operator interaction layer. It MUST NOT
   become a control-plane authority, write-path for incidents, or required
   runtime for BioETL pipelines.

2. **Data sources unchanged.** Prometheus (low-cardinality) and Ops HTTP
   (`/ops/control-plane/*`, `/ops/observability/*`, `pipeline_run_report_v1`)
   remain the only evidence sources. No invented series. No `run_id` Prometheus
   labels.

3. **Seven UIDs remain provisioned fallbacks** until an explicit cutover gate:
   - `bioetl-control-plane-v1`
   - `bioetl-overview-v2`
   - `bioetl-runtime`
   - `bioetl-provider-health-v2`
   - `bioetl-dq-v2`
   - `bioetl-incident-v1`
   - `bioetl-run-explorer-v1`

4. **Six app routes map to those UIDs** (Trust + DQ merge only at IA/tabs):

   | App route | Compatibility UIDs |
   | --- | --- |
   | Operations Home | `bioetl-overview-v2` |
   | Incident Console | `bioetl-incident-v1` |
   | Pipeline Flow | `bioetl-runtime` |
   | Dependency Health | `bioetl-provider-health-v2` |
   | Data Trust & Recovery | `bioetl-control-plane-v1` + `bioetl-dq-v2` (tabs) |
   | Run Explorer | `bioetl-run-explorer-v1` |

5. **Build gate.** App shell implementation (DS2-11) starts only after:
   - Wave 0 green (truth/render gates)
   - Wave 1 green (JSON compression + contextual routing)
   - This ADR accepted

6. **Parity before retirement.** Dual-surface period requires parity tests
   (counts/status/reasons/links for same scope/time). UID/route retirement
   requires usage evidence + redirects ≥1 release. Tech-debt budgets MUST NOT
   increase.

7. **ADR-010 preserved.** Local-only default remains; Docker/Grafana remain
   optional. The app package is operator tooling, not a BioETL core dependency.

## Migration

1. Keep JSON dashboards under `grafana/dashboards/*.json` as the rollback SSOT
   during dual-surface period.
2. Introduce Scenes routes/UIDs only behind explicit feature flags / optional
   package paths (see DSS epic issues).
3. Parity tests (counts/status/reasons/links for same scope/time) **MUST** pass
   before any UID or route retirement.
4. Document dual-path provisioning (JSON import vs Scenes app) before cutover.

## Rollback

1. **Parity failure:** keep JSON dashboards authoritative; disable Scenes routes
   / hide dual navigation; do not delete JSON UIDs.
2. **UID/route cutover failure:** restore previous JSON dashboard UIDs from git;
   re-enable dual-path redirects for ≥1 release if already partially cut over.
3. **Operator confusion:** set documentation banners that Scenes is optional
   adjunct (ADR-010); Local-Only core runtime does not require Grafana.
4. Tech-debt / quality budgets **MUST NOT** increase to force Scenes adoption.

## Consequences

### Positive

- Clear go/no-go for Scenes work without portfolio shrink
- Protects DRM/DRM-R/DS2 JSON investments as rollback path
- Keeps Hex/DDD and control-plane write paths out of Grafana

### Negative / costs

- Dual surface risk until cutover (mitigate with parity tests + owner)
- Scenes delivery is a separate multi-sprint effort after Wave 1

### Non-goals (explicit)

- Topology / Sankey / waterfall without separate data-contract ADRs
- Persistent collaborative incident record inside Grafana JSON
- Required cloud/SaaS Grafana for core BioETL

## Implementation notes

- Shared components (when built): Context Bar, Verdict Strip, Evidence
  Confidence, Status Matrix, Alert List, Action Rail, Empty State, Event Timeline
- Drilldown grammar: verb + target + why + context + return + success condition
- UX grammar: state → impact → evidence confidence/age → location/cause → safe
  action → verification

## Status of related issues

- DS2-10 (#6911): satisfied by this ADR
- DS2-11 (#6912): implementation **deferred** until a dedicated delivery window
  after Wave 1; JSON fallback is the production operator path
- DS2-12 / DS2-13: remain contract-gated tracking; not authorized by this ADR alone
