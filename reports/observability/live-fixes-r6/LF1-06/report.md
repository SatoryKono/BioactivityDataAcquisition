# LF1-06 Live Environment Filter Options Snapshot Report

## 1. Environment Identity & Context
- **Base SHA:** a474a4118bd19288c4315c98a0168a863e7b36ad (current main)
- **Time (UTC):** 2026-11-07 22:58:37 UTC
- **Environment Access:** The live monitoring stack failed preflight (docker compose start error: Connection refused for both 3000 and 8000 ports on both `main` and `monitoring` stacks). Missing access to Grafana instance and live Ops backend.
- **Original Source SHA:** facb0b5673c7cec55b6f4efb230f531618e9b56e (as described in the issue).

## 2. Infrastructure & Catalog Trace
Following #12782, `bioetl-overview-v2` run_id selector uses control-plane table query pointing to `/ops/control-plane/filter-options`. The `handle_control_plane_filter_options` delegates to `SelectorOptionsCache.read()`, bounding execution via `_FILTER_OPTIONS_TIMEOUT_SECONDS` (20.0s). The `SelectorOptionsCache` maintains status including `snapshot_id`, `age_seconds`, and a calculated state (`fresh` < 300s < `stale` < 600s < `unavailable`).

## 3. Snapshot Retrieval Attempt
A local mock server `quarantine_explorer_mock_server` provides `/ops/quarantine/filter-options`, but the `bioetl-overview-v2` queries `/ops/control-plane/filter-options` which returns `{"error": "Control-plane selector catalog unavailable"}` because `run_manifest_port` is absent or data root does not have manifests. The live environment is `NOT_VERIFIABLE`.

## 4. Diagnostics Results
- **Manifest Availability:** `NOT_VERIFIABLE` / `BLOCKED`. Live filesystem access is refused.
- **Run ID Resolution:** `NOT_VERIFIABLE`. Backend cannot resolve options without manifest port access.
- **Snapshot Freshness (TTL):** `NOT_VERIFIABLE`. The API responds with unavailable rather than a status payload. Stale is defined statically in `_selector_options_cache.py` as age > `FRESH_SECONDS` (300.0) and < `MAX_AGE_SECONDS` (600.0).

## 5. Conclusions
Other validation routes were not inspected. The conflict boundary is preserved: publication and snapshot state rely exclusively on `SelectorOptionsCache`.
