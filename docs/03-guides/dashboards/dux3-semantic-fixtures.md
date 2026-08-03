______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-29'
Issue: '#7074 (DUX3-33)'

______________________________________________________________________

# DUX3 semantic fixture matrix

Do **not** invent Prometheus metrics. Prefer existing recording rules / empty
frames / Ops HTTP empty responses.

| State | Preferred UI | Scope notes | Next action |
| --- | --- | --- | --- |
| OK | green + `OK` text | HEALTH/EXEC with evidence | monitor |
| WARN | orange + `WARN` | HEALTH | open First Action |
| CRIT | red + `CRIT` | HEALTH/IMPACT | open First Action / Incident |
| FRESH | freshness chip OK | EVIDENCE | none |
| STALE | orange + `STALE` | EVIDENCE | check scrape/rules |
| MISSING | gray + `MISSING` / `TELEMETRY ABSENT` | EVIDENCE | repair telemetry |
| BACKEND_ERROR | red/gray + `BACKEND ERROR` | any HTTP panel | check `/health/live` |
| NOT_STARTED | gray + `NOT STARTED` | EXEC | wait / start run |
| N/A | gray + `N/A` | APPLICABILITY (empty provider) | select provider / change scope |
| VALID_EMPTY | gray + `VALID EMPTY` | RANGE/RUN zero events | stay / monitor |

Bare `UNKNOWN` only when none of the above can be determined.

See also [dux3-residual-contracts.md](dux3-residual-contracts.md) §3.
