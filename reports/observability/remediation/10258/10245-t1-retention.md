# #10245 T1 Retention — implementation note

Date: 2026-09-09
Branch: `codex/grafana-10258-remediation`
Issue: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10245

## Changes (allowed surfaces only)

- `grafana/dashboards/bioetl-control-plane-v1.json` panel 9416
- `tests/integration/test_dashboard_first_window_containment.py` (9416 assertions)
- this note

906 was narrowed to `w=12` at `x=0,y=12` so the taller 9416 (`h=8`) does not overlap the next-step rail. Other first-window panels were not reverted.

## How T1 is met

### Live summary (`3 OK, 2 UNKNOWN`)

Infinity target **B** reads `/ops/control-plane/retention-compliance` with `root_selector: "summary"` and UQL/jsonata that builds `headline` from `summary.ok_count` and `summary.unknown_count`. Grafana `configFromData` maps `headline` onto the `check` field `displayName`, so the first-column header is data-driven. JSON `title` stays `Review Retention Compliance` (static tests).

### UNKNOWN before OK

`sortBy` transformation on field `status` descending runs **before** `limit=5`. Alphabetical desc puts `UNKNOWN` before `OK`. `options.sortBy` on displayName `Status` is the operator-visible sort. Backend row order is unchanged.

### Five rows without inner scroll

`gridPos.h` 5 → 8 (`y=7`, bottom 15 ≤ `first_window_y=18`). `cellHeight=sm`, `wrapText=false` on check/status/reason so mapped labels stay one row. 906 sits left of 9416 (`w=12`) instead of spanning 24.

### Readable names on the wide layout

Mapped labels fit the locked 200% CSS budget (`w=12`, reason width 150, status remains flex / no `custom.width`):

- check 80 → 150; names such as `Snapshots` / `Required evidence`
- reasons such as `Snapshot incomplete` / `Archive missing` (no wrap)

`test_cycle5_wrap_text_columns_restore_declared_widths` still requires reason=150 and status unbounded.

## Remaining risk

- `configFromData.targetField` depends on Grafana mapping support; if ignored, all columns could share the live displayName. Rows and sort still work.
- Infinity UQL/jsonata on target B is not exercised by static pytest; browser evidence is optional unless Grafana is already up.
- `scripts/ops/observability/grafana/render_nav_bus.py` still pins 9416 to `h=5` and 906 to `w=24`. Regenerating the nav bus without updating that map would revert geometry. That script is outside #10245 exclusive ownership.
- Status desc is lexicographic: `WARNING`, `UNKNOWN`, `OK`, `ERROR`. The audited payload is 3 OK + 2 UNKNOWN, which sorts correctly. An ERROR row would sort after OK.

## Validation

See the agent report for pytest commands and results. `docker-compose.monitoring.yml` was not started. No commit.
