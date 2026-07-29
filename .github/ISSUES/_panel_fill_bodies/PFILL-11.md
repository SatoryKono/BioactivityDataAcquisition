## Summary

DQ panel **Time Range · Worst Freshness Age** can show UNKNOWN when `bioetl_data_freshness_seconds` is absent for selected pipeline, while other DQ scores/accounting still render — operator may trust 100% score without freshness.

## Panel

- Dashboard: `bioetl-dq-v2`
- Panel id: 8
- Expr: `(max(clamp_min(time() - max_over_time(bioetl_data_freshness_seconds{pipeline=~"$pipeline"}[12h]), 0))) / 3600`

## Fix direction

1. Ensure pipeline emit of `bioetl_data_freshness_seconds`
2. Pair panel with explicit noValue + description: TELEMETRY_MISSING vs not-started
3. Optional recording rule for worst freshness hours

## Acceptance

- Freshness panel never looks "healthy empty" when series missing
- Status/score/freshness empty states are consistent on first screen

## Related

#7158
