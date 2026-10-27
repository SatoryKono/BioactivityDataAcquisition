# Criterion to Evidence Matrix - Issue 12485

1. **Criterion:** Сохранить принятую checkpoint-first/hybrid модель ADR-046. Не реализовывать новую resume-архитектуру и не объявлять санкционированную сложность дефектом.
   **Evidence:** No code changes were made to the `bioetl` logic (`src/bioetl/application/composite/checkpoint/load_service.py`, `_checkpoint_replay_projection.py`). The existing logic was preserved.

2. **Criterion:** Подлинная provenance уже принятого риска (сообщения пользователя от 2026-10-22).
   **Evidence:** `reports/ledger12457_handoff.json` now cites the exact source-message IDs, UTC timestamps, and excerpts for the existing owner instructions: `Sentinel_fda89a6cbfc48191b7b40052d5cb09f8` (2026-10-22T10:21:21.955023Z; move item 2.8 to accepted risks, section 6) and `Sentinel_1f79397dd26c8191b2136a4b90d7cd32` (2026-10-22T13:58:06.101058Z; record acceptance in 6.1 through the ledger). The messages are traceable transcript references; no public GitHub permalink for either message was supplied. Issue [#12485](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12485) is the risk registration, issue [#12457](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12457) is the completed reconciliation ledger, and [ADR-046](../../02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md) is the governing architecture decision. These GitHub/ADR references are contextual records, not substitutes for the original message references.

3. **Criterion:** Условия соответствия документации фактической реализации.
   **Evidence:** Updated `docs/02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md` to clarify that `RunLedgerReplayProjection` actually projects rich checkpoint payloads (dependency result maps, enrichment result maps, merge details) into the suffix delta. This directly matches the code in `src/bioetl/application/composite/checkpoint/_checkpoint_replay_projection.py` without promising universal ledger replay.

4. **Criterion:** Проверяемые ссылки на source-of-truth, mismatch, restart и replay.
   **Evidence:** Ran testing suite for architecture drift (`test_config_topology_docs_drift.py`), ledger replay (`test_run_ledger_replay.py`), and checkpoint runtime (`test_checkpoint_runtime.py`). Verified with 100% pass rate. These links are stored in `reports/ledger12457_handoff.json`.

5. **Criterion:** Подготовить полную доказательную запись для существующего ledger12457.
   **Evidence:** `reports/ledger12457_handoff.json` was generated and forced-staged with all necessary tracking fields, including `current_sha` evaluated after merging `main`.

6. **Criterion:** Выполнить штатный ARTIFACT_REFRESH check/update/check, docs drift.
   **Evidence:** Verified on tip `d5b6ce5d3d` (Asia/Baghdad wall-clock 2026-10-27 ~18:04 UTC+3):
   - `python -m scripts.docs check-drift --runtime-mirrors --freshness` → OK (0 errors, 0 warnings)
   - `python -m scripts.docs check-links` (full suite; not `--links` alone) → OK — Links/Nav/Specs/Configs/Gold contracts/Workflow inventory/ChEMBL overview/Provider/Runbook/Control-plane/Not-in-nav/Doc drift all passed (`All checks passed.`)
   - `python -m scripts.engineering.ci.update_test_telemetry_baseline --rebind-current-tree` → idempotent; preserves `local_coverage_verify` capture (`source_commit=8a4286d21b…`, coverage 99.66%, `measurement_provenance` present; `source_tree_sha256=394069633f…`)
   - `python -m scripts.engineering.qa refresh-ci-drift-families --check --test-gov --flaky-fingerprint --telemetry --remote-main` → OK (`CI drift families complete (no budget ratchet)`). Per AGENTS.md this is the allowed CI-family path; `refresh_governance_artifacts` was **not** used for this rebind and is not claimed.
