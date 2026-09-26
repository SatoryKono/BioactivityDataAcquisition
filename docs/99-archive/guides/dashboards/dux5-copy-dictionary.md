> Archived snapshot. The maintained guide remains at
> [DUX5 operator copy dictionary](../../../03-guides/dashboards/dux5-copy-dictionary.md).

# DUX5 operator copy dictionary

**Status:** active  
**Wave:** DUX5 (#7116)  
**Owner:** interface / Grafana dashboard system  
**Verdict logic owner:** application / control-plane / recording rules (not Grafana transforms)

## Reading order

`Context → Status → Reason → Impact → Action → Evidence`

## State classes (operator-facing)

| Class | When | Display guidance |
| --- | --- | --- |
| **OK** | Validated healthy | green badge; neutral surface preferred for non-critical |
| **WARN** | Degraded / attention | orange |
| **CRIT** | Confirmed failure | red |
| **INCOMPLETE** | Required trust evidence missing/stale | gray; never OK |
| **UNKNOWN** | Evidence incomplete (missing/stale/not-started/backend-error) | gray; always pair with Reason |
| **None observed** | Query completed; zero matching events | neutral; not success |
| **Not started** | Stage not applicable yet (e.g. Silver during SCRAPING) | neutral |
| **Not available** | Denominator zero / signal N/A | neutral; never `0%` rate |
| **Selection required** | Required selector empty | neutral; action = select |
| **Telemetry missing** | Required metric family absent | gray; action = inspect scrape |

L0 Status panels keep enum tokens `OK/WARN/CRIT/UNKNOWN/INCOMPLETE` for contract stability
(DUX4-01 Approach B + metric semantics tests). Expanded meaning lives in Provenance /
description / paired reason panels.

## Forbidden primary copy

- Bare `No data` without class
- `VALID_EMPTY` developer token
- Raw `GET /ops/...` endpoint syntax in triage bodies
- Literal Markdown `###` headings as on-canvas chrome
- Auto `Value #A` without displayName
- Full UUID as the only visible identity without Copy/Open

## Title policy

Panel titles with `Monitor:` / `Track:` / `Inspect:` prefixes remain **contract-stable**
for integration tests. Operator nouns live in Provenance status cards and action lists.

## Typography floors (DUX5-10)

| Token | Min size @1366 | Use |
| --- | ---: | --- |
| `dashboard-context` | 12px | breadcrumb / selectors |
| `panel-title` | 13px | panel titles (≤2 lines) |
| `status-badge` | 14px bold | Status enum |
| `stat-primary` | 18px | primary numeric |
| `body-primary` | 13px | reason/action |
| `body-secondary` | 12px | scope/freshness |
| `table-cell` | 12px | tables |
| `axis-label` | 11px | chart axes |

No auto-shrink below floors; reflow/wrap/shorten instead.

## Ownership

| Surface | Owner board |
| --- | --- |
| Exact-run forensic tables | Run Explorer |
| Ranked triage | Incident Workspace |
| Cross-domain routing | Overview |
| Replay confidence | Trust |
| Domain decision | Runtime / Provider / DQ |

## DUX6 residual

Pixel residual after re-audit: [dux6-residual-readability.md](dux6-residual-readability.md).
