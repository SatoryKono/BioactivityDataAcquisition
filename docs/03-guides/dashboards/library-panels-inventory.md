______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Library panels inventory (logical)

Grafana library-panel exports are optional. BioETL standardizes **logical library**
patterns by stable panel id ranges and titles across boards.

| Logical panel | Typical id | Type | Ownership |
| --- | ---: | --- | --- |
| `nav_bus` | 1000 | text | Shared chrome; full bus `0. Trust`…`6. Run Explorer` via `scripts/ops/observability/grafana/render_nav_bus.py` |
| `provenance` | 9400 (Overview: 99) | text | Scope / provenance summary |
| `status_strip` | 9401 (Overview: 214) | stat | Canonical current-status recording rule |
| `first_action` / `next_best_actions` | board-specific | text/table | ≤4 CTAs; preserve time+vars |
| `confidence_badge` | trust cards / telemetry gap | stat | Missing evidence / scrape trust |
| `entity_status_matrix` | Provider 9101, Overview Inputs 9002 | table | Population-first severity |
| `suspect_table` | Provider causes / Runtime blockers | table | Ranked suspects |
| `event_timeline` | Incident workspace | table/timeseries | Alert/event range |
| `run_identity` | 9402 (primary boards) / Run Explorer `3022` | table HTTP | Ops HTTP identity — not Prom labels |
| `processed_records` | 9403 (primary boards) / Run Explorer `3023` | table HTTP | Bronze/Silver/Gold accounting |

## Query ownership

- Status strips: recording rules only (`*_current_status*`), no `$__range`.
- Population matrices: recording rules with fail-closed zero policy where documented.
- Identity: **BioETL Ops HTTP** only.
