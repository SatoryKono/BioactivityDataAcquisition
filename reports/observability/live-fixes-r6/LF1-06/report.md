# LF1-06 Live Environment Filter Options Snapshot Report

## 1. Environment Identity & Context
- **Base SHA:** 9b33adf0174a97ec88a7b95942e6a78eaf40cf1a (current tip of main)
- **Time (UTC):** 2026-11-08 19:35:00 UTC
- **Environment Access:** `BLOCKED`. The live environment is objectively unavailable. Attempts to start the stack using `docker compose up -d` failed with overlayfs mount errors (`invalid argument` in containerd-overlayfs cachemounts) preventing the `bioetl` container and the live environment from running.
- **Original Source SHA:** facb0b5673c7cec55b6f4efb230f531618e9b56e (as described in the issue).

## 2. Infrastructure & Catalog Trace
Following #12782, `bioetl-overview-v2` run_id selector uses a control-plane table query pointing to `/ops/control-plane/filter-options`. The `handle_control_plane_filter_options` delegates to `SelectorOptionsCache.read()`, bounding execution via `_FILTER_OPTIONS_TIMEOUT_SECONDS` (20.0s). The `SelectorOptionsCache` maintains status including `snapshot_id`, `age_seconds`, and a calculated state (`fresh` < 300s < `stale` < 600s < `unavailable`).

## 3. Snapshot Retrieval Attempt
The `bioetl-overview-v2` queries `/ops/control-plane/filter-options`. Live requests cannot be performed because the live environment is objectively unavailable and cannot be mocked without violating the rules.

## 4. Diagnostics Results
- **Manifest Availability:** `NOT_VERIFIABLE` / `BLOCKED`. Live filesystem and API access are refused due to docker startup failure.
- **Run ID Resolution:** `NOT_VERIFIABLE`. Backend cannot resolve options without live access.
- **Snapshot Freshness (TTL):** `NOT_VERIFIABLE`. STALE is defined statically in `_selector_options_cache.py` as age > `FRESH_SECONDS` (300.0) and < `MAX_AGE_SECONDS` (600.0). However, the actual live payload cannot be retrieved.

## 5. Conclusions
Other validation routes were not inspected. The conflict boundary is preserved: publication and snapshot state rely exclusively on `SelectorOptionsCache`. The diagnostic cannot be fully completed on a live environment as it is blocked.
