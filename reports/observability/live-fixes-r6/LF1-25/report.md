# LF1-25 Filter-options freshness

Issue: #12821.

- Source SHA: `48dc0257ed980decaf0d8bf4c209c7e39309a4c4` (`origin/main`).
- Local Ops HTTP: `http://127.0.0.1:8000`.
- TTL constants were not changed: fresh below 300s, stale until 600s (`FRESH_SECONDS`, `MAX_AGE_SECONDS`).
- Deploy SHA and Grafana selector pixels: `NOT_VERIFIABLE`. The variable URL in `bioetl-overview-v2` is the `allow_stale=1` options query below.

## Snapshot before refresh

`GET /ops/control-plane/filter-options?pipeline=chembl_assay&dimension=run_id&status_only=1`

HTTP 200. `catalog.state=unavailable`, `snapshot_id=null`, `observed_at=null`, `age_seconds=null`, `last_refresh_error=null`.

This is an empty cache, not a STALE label and not a manifest-completeness claim.

## Authorized refresh

`GET /ops/control-plane/filter-options?dimension=run_id&response_shape=options&workflow=.*&pipeline=chembl_assay&run_type=incremental&timezone=UTC&allow_stale=1`

HTTP 200 at `observed_at=2026-11-09T08:36:29.659723+00:00`.

- `catalog.state=fresh`
- `snapshot_id=9f4170c8aa8990f399849ffa3cb5dc1476c756f6e3f4142bd9eb98f2f71aa425`
- `age_seconds` at that response was under 1 second
- `items=[{"text":"НЕТ ЗАПУСКОВ","value":"-"}]`
- the payload does not contain `STALE`

An earlier object-shaped refresh of the same pipeline and dimension, without `response_shape=options`, produced a different snapshot `7c6703c45f28a03bd001ccd40e9fd6e9e0b95907d4dd4d8a95f262c0c41f9ea6` at `2026-11-09T08:35:23.656035+00:00`, also `fresh`, with `items=["-"]`. A later `status_only=1` on that key stayed `fresh` (age about 52s), still below 300s.

The default path without `allow_stale` returns the live payload and does not add a `catalog` object. Grafana's run-id variable uses `allow_stale=1`, which is the path that can append `[STALE catalog]`.

## New UUID

No new UUID appeared. The fresh options item is the empty sentinel `-` / `НЕТ ЗАПУСКОВ`. `GET /ops/observability/pipeline-run-reports?pipeline=chembl_assay&limit=3` returned HTTP 200, `index_state=tree_missing`, `count=0`. No ETL run was started. Freshness of this snapshot is not a statement that a manifest catalog is complete.

## Isolated stale snapshot

The running server was not aged past 300s, and the TTL was not increased. The isolated case is `tests/unit/interfaces/http/test_selector_options_cache.py::test_stale_is_immediate_under_saturation_and_expires`.

Command: `python -m pytest -q -p no:cacheprovider -o addopts= tests/unit/interfaces/http/test_selector_options_cache.py::test_stale_is_immediate_under_saturation_and_expires`

Result: 1 passed in the same run as the Overview mapping checks (3 passed, 2.75s, UTC date 2026-11-09). The test sets age to `FRESH_SECONDS + 1`, expects `state=stale`, and expects the label `assay [STALE catalog]` while the value stays `chembl_assay`. At `MAX_AGE_SECONDS + 1` the state becomes `unavailable`.

## Decision

No source change. A fresh `allow_stale` snapshot did not carry `STALE`. The stale suffix remains the age marker in the isolated test. It was not deleted.

## Checklist

- Fresh snapshot: measured, no `STALE` suffix. New UUID: `NOT_RUN` (empty report tree, no authorized ETL).
- Manifest completeness and option age are different responses: empty options sentinel versus `manifest-validation` `selected_run_id_not_found`.
- Evidence is this report, the receipt and checksums. Grafana pixels and deploy SHA are `NOT_VERIFIABLE`.
