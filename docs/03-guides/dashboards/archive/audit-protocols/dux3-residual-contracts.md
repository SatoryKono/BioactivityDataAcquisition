______________________________________________________________________

Version: 1.0.0
Status: archived
Class: published
Owner: BioETL Team
Last verified: '2026-07-29'
Issues: '#7053–#7077 (DUX3)'

______________________________________________________________________

# DUX3 residual contracts (post-DSA screenshot audit)

Normative residual after closed DS2/DSA. SOT for layout remains
`grafana/dashboards/*.json`. This file freezes **W0 contracts** that W1–W3
edits must obey.

Related:

- Issue pack: `.github/ISSUES/DUX3-2026-07-29-DASHBOARD-UX-RESIDUAL-ISSUE-PACK.md`
- Inventory: `docs/03-guides/dashboards/dux3-first-screen-inventory.json`
- Operator UX: [operator-ux-v2.md](../../operator-ux-v2.md)
- Verdict ontology: [verdict-ontology.md](../../verdict-ontology.md)
- Synthetic zero policy: [contracts/synthetic-zero-policy.yaml](../../contracts/synthetic-zero-policy.yaml)
- Audit selection notes: `docs/03-guides/dashboards/dux3-audit-selection-notes.md`

## 1. Scope enum (DUX3-02)

Every first-screen cell declares exactly one **scope**:

| Scope | Meaning | May use `run_id`? |
| --- | --- | --- |
| `NOW` | Instant / current recording-rule posture | No (Prom) |
| `RANGE` | Selected Grafana time range aggregation | No (Prom) |
| `RUN` | Exact selected run via Ops HTTP / control-plane | Yes (HTTP only) |
| `WORKFLOW` | Cross-pipeline workflow blast radius | No |
| `GLOBAL` | Fleet / portfolio population (provider fleet, global severity) | No |

**Rule:** panels with different scopes MUST NOT be presented as peer health
badges without a visible scope marker (title prefix or context strip).

## 2. Semantic family (DUX3-02)

| Family | Examples |
| --- | --- |
| `HEALTH` | Pipeline/provider/DQ current severity |
| `EXECUTION` | Runtime phase, blockers, stage lag |
| `EVIDENCE` | Freshness, telemetry gap, SCRAPING confidence |
| `APPLICABILITY` | Empty provider selection, N/A scopes |
| `IMPACT` | Blast radius, reject counts, delivery impact |

**Rule:** `EXECUTION` phase (e.g. SCRAPING) must not use health-green semantics.
`EVIDENCE` gaps reduce confidence; they are not pipeline success.

## 3. Empty-state / zero / color contract (DUX3-03)

### Typed UI signals (prefer over bare UNKNOWN)

| Signal | Meaning | Color cue | Non-color label required |
| --- | --- | --- | --- |
| `OK` | Healthy with expected evidence | green | `OK` |
| `WARN` | Degraded | orange | `WARN` |
| `CRIT` | Failed / critical | red | `CRIT` |
| `VALID_EMPTY` | Query ok, zero matching events | gray / neutral | `VALID EMPTY` |
| `N/A` | Selector/applicability not met | gray | `N/A` |
| `NOT_STARTED` | Work not begun | gray | `NOT STARTED` |
| `MISSING` / `TELEMETRY_ABSENT` | Required series absent | gray/blue | `MISSING` or `TELEMETRY ABSENT` |
| `STALE` | Freshness breach | orange | `STALE` |
| `BACKEND_ERROR` | HTTP/Prom failure | red or gray + text | `BACKEND ERROR` |
| `INCOMPLETE` | Trust gate: evidence gap | orange/gray | `INCOMPLETE` |
| `UNKNOWN` | Truly undetermined only | gray | `UNKNOWN` + reason when known |

### Hard bans

1. **No green success** when denominator is 0 (e.g. Failure Rate 0.00% with 0 checks).
2. **No red** for expected absence / valid empty zero (e.g. Processed Records empty rows).
3. **No health color** for execution-phase chips (SCRAPING / stage phase).
4. **No bare UNKNOWN** when a typed class above is already knowable from mappings.
5. **No synthetic healthy zero** on first-screen Status (see synthetic-zero-policy).

### Checklist for field overrides

For each first-screen stat/table on the 7 UIDs:

- [ ] thresholds do not paint 0 green unless denominator/evidence proves expected zero success
- [ ] color-background does not paint non-severity columns
- [ ] mappings include text labels for every threshold color
- [ ] scope marker present in title or shared provenance strip

## 4. First viewport budget (DUX3 W2)

```text
[Nav bus h≤3]
[Context strip: workflow/pipeline/run_type · range · freshness · scope legend]
[Health | Execution | Evidence | Impact]  ≤4 compact cells
[Primary cause / VALID_EMPTY reason | Primary action]
[One dominant viz]
── fold ──
[Collapsed forensics / ID thin shell / trends]
```

Budgets:

- ≤ **1** dominant visualization above fold
- ≤ **4** compact verdict cells above fold
- ID / Processed Records: **Run Explorer hub only** as first-screen KPI; other boards collapsed thin shell
- No internal vertical scroll on triage text panels
- No horizontal scroll at 1366px except named explorers

## 5. Semantic fixtures (DUX3-33)

Fixture states for regression notes (do not invent metrics):

`OK | WARN | CRIT | FRESH | STALE | MISSING | BACKEND_ERROR | NOT_STARTED | N/A | VALID_EMPTY`

Map each to preferred appearance using the table in §3.

## 6. Data-link contract (DUX3-34)

Reaffirm [navigation-contract.md](../../navigation-contract.md) and
`contracts/navigation-links.yaml`:

- preserve `${__url_time_range}` / `from`+`to`
- pass only allowed vars
- `run_id` only on run-scoped destinations
- never inject `run_id` into Prometheus selectors

## 7. Usability proxies (DUX3-35)

Measure only proxies from [usability-baseline-protocol.md](../../usability-baseline-protocol.md):

| Proxy | Target |
| --- | ---: |
| Clicks to first cause | 3–5 |
| Screens per investigation | 2–3 |
| Time-to-first-suspect | ≤30s first screen |

**No** causal MTTD/MTTI/MTTR claims.

## 8. Track only (DUX3-40)

- Scenes Trust+DQ tabs (ADR-053)
- Node graph / Sankey / waterfall (contract-gated)
- UID retirement criteria
- Incident owner/ack write-path (ADR + backend)

No unsolicited implementation in residual wave.
