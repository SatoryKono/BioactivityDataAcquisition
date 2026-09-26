# Pipeline selector relation audit — issue #6359

Captured: `2026-07-20T08:05:54Z`
Source revision: `0b65839d20f818b15132abc32e4d4f32062cd745` (`main`)
Verdict: **PASS — closeable**

## Outcome

The historical 15/19/20 counts are not a flat-equality defect. The shipped
contract intentionally has one shared operator universe plus two
evidence-gated role-local universes. A live Grafana datasource capture now
proves the required relations with zero unexplained values.

| Surface | Dashboards | Default range | Pipelines | `(pipeline, run_type)` pairs | Relation |
| --- | --- | ---: | ---: | ---: | --- |
| Canonical shared | Overview, Runtime, Provider, DQ, Workflow, Alerts | 12h / 24h | 27 | 54 | exact equality |
| Control Plane | Control Plane | 12h | 15 | 16 | provenance-gated subset in this capture |
| Explorer | Silver Reject Explorer | 24h | 15 | 16 | processed-row subset |

Overview and Runtime returned identical values and pairs at both 12h and
24h. All six shared dashboards resolved the same 27/54 set despite their
different default ranges.

## Difference classification

The 12 canonical-only pipelines are:

- `composite_activity`
- `composite_assay`
- `composite_molecule`
- `composite_publication`
- `composite_target`
- `crossref_publication`
- `openalex_publication`
- `pubchem_compound`
- `pubmed_publication`
- `semanticscholar_publication`
- `uniprot_idmapping`
- `uniprot_protein`

There are 38 canonical-only pairs.
Every one is present in `bioetl_pipeline_runs_total`; none is unexplained.
Control Plane has no role-local-only value in this sample, and every observed
Control Plane pair is backed by `bioetl_control_plane_manifest_writes_total`.
Explorer has no value outside the canonical universe, and every observed
Explorer pair is backed by `bioetl_records_processed_total`.
`bioetl_workflow_pipeline_expected` had no samples in the captured windows;
the runtime/manifest/row sources fully explain the current sets.

## Navigation and handoff

- Live Grafana API returned all 8 provisioned dashboards.
- 56/56 dashboard-to-dashboard links target every other dashboard.
- Every audited handoff preserves `${__url_time_range}` and a variable-backed
  `var-pipeline`; no literal replacement or silent substitution was found.
- Control Plane's Overview return path and typed empty-state guidance were
  present in the live dashboard.
- Explorer's Reset / concrete-pipeline / Backend Health recovery guidance was
  present in the live dashboard.

## Method and provenance

Selector values were resolved through Grafana's Prometheus datasource proxy
using `/api/v1/label/pipeline/values` and `/api/v1/series`, bounded to each
dashboard's shipped default range. This matches variable discovery semantics;
an empty instant vector after Pushgateway cleanup is not treated as an empty
selector history.

The worktree was dirty because of unrelated pre-existing MCP/editor/PyCharm
changes. All dashboard JSON, Prometheus rule, selector-contract, variable
reference, and selector-test paths were clean at capture time; their SHA-256
values are recorded in the machine-readable artifact.

Machine-readable evidence: `selector-evidence.json`.

## Closure decision

Required shared equality, Control Plane provenance, Explorer subset safety,
and navigation recovery all pass. Unexplained difference count is **0**.
Issue #6359 is ready to close.
