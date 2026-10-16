# DUX2 — Dashboard System 2.0 Phase-2 Residual Issue Pack

**Date:** 2026-07-28  
**Parent epic:** [#6828](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6828)  
**Supersedes as execution plan:** greenfield «Unified Plan v2.0» (not executable as-is)  
**Builds on:** closed epic #6800 (DUX Phase-1)

## Constraints (all children)

- Portfolio **≤7** first-class boards; stable uids  
- SOT: `grafana/dashboards/*.json`  
- ADR-010: Grafana optional; no required Docker/Redis  
- **No** reintroduce Loki/Tempo/Silver Reject UI without ADR  
- **No invent metrics** / no `run_id` PromQL labels  
- Tech-debt budgets must not increase  
- Integration grafana tests must stay green  

## Portfolio (fixed)

| # | uid | Role |
| ---: | --- | --- |
| 0 | `bioetl-control-plane-v1` | Trust |
| 1 | `bioetl-overview-v2` | Fleet / Global Ops alias |
| 2 | `bioetl-runtime` | Pipeline explorer |
| 3 | `bioetl-provider-health-v2` | Provider fleet |
| 4 | `bioetl-dq-v2` | Data trust |
| 5 | `bioetl-incident-v1` | Incident workspace |
| 6 | `bioetl-run-explorer-v1` | Run explorer |

## Child map

| ID | P | Issue | Title |
| --- | --- | --- | --- |
| DUX2-01 | P0 | [#6831](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6831) | Residual plan SSOT + rebaseline docs |
| DUX2-02 | P1 | [#6829](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6829) | Visualization upgrades (existing series only) |
| DUX2-03 | P1 | [#6834](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6834) | Incident Workspace depth |
| DUX2-04 | P2 | [#6832](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6832) | Run Explorer depth |
| DUX2-05 | P1 | [#6835](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6835) | First Action + empty-state chrome standard |
| DUX2-06 | P2 | [#6836](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6836) | Nav bus readability polish |
| DUX2-07 | P1 | [#6837](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6837) | Usability re-measure post-DUX |
| DUX2-08 | P2 | [#6833](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6833) | Operator docs sync (Grafana surface) |
| DUX2-09 | P3 | [#6830](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6830) | Gated backlog (Sankey/Topology/Health Score) |

## Recommended order

#6831 → #6829+#6835 → #6834 → #6837 → #6832+#6836 → #6833 → #6830 (tracking only)

## Non-goals (epic)

- Greenfield Tier0–3 portfolio  
- New monorepo `bioetl-dashboards/`  
- System Health Score / ML DDx without metrics+ADR  
- 5–10s global refresh  
