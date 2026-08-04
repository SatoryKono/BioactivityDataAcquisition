______________________________________________________________________

Version: 1.0.1
Status: active
Class: repo-only
Owner: BioETL Team
Last verified: '2026-08-04'

______________________________________________________________________

# Migration map — Dashboard System 2.0

> **Classification:** repo-only working map (not MkDocs-published SSOT).
> Docs audit cycle 2 / #7430. Prefer dashboard README + navigation contract for
> operator entry; this table tracks UID stability for System 2.0 migration.

Epic #6800. UIDs stay stable for primary boards unless noted.

| Current uid | Current title | Target workspace | Phase | Deprecation |
| --- | --- | --- | --- | --- |
| `bioetl-control-plane-v1` | 0. Trust | Control Plane Explorer | DUX-03 | none — uid stable |
| `bioetl-overview-v2` | 1. Overview | Fleet Command Center | DUX-02 | title may gain Fleet alias; uid stable |
| `bioetl-runtime` | 2. Pipeline Diagnostics | Pipeline Explorer | DUX-05 | none — uid stable |
| `bioetl-provider-health-v2` | 3. Provider Health | Provider Explorer | DUX-04/09 | none — uid stable |
| `bioetl-dq-v2` | 4. Data Quality | Data Trust Explorer | DUX-06 | none — uid stable |
| _(new)_ `bioetl-incident-v1` | Incident Workspace | Incident Workspace | DUX-08 | new |
| _(new)_ `bioetl-run-explorer-v1` | Run Explorer | Run Explorer | DUX-10 | new; thins duplicated run-context rows |

## Alert entry rebind

| Alert family | First UI hop | Then |
| --- | --- | --- |
| Runtime / pipeline blockers | Fleet (`bioetl-overview-v2`) or Incident | Pipeline Diagnostics |
| Provider severity / retries | Provider Explorer | Incident suspects |
| DQ hard threshold / quarantine | Data Trust | Incident + Run Explorer |
| Replay / checkpoint | Trust | Run Explorer identity |

## Portfolio cap

≤7 first-class boards. Adjunct Explore UIs and Silver Reject Explorer remain removed
(surface reduction 2026-07-23).

## Phase-2 residual (epic #6828)

Do **not** create new uids for Global Ops / Pipeline Overview / DQ Center aliases —
map names to the fixed seven above. Execution plan:
`dashboard-system-2.0-phase2-residual.md`. Gated fancy viz (Sankey/Topology/Health
Score): issue #6830 only after metrics+ADR gates.
