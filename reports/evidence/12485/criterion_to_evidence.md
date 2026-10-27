# Criterion to Evidence Matrix - Issue 12485

1. **Criterion:** Сохранить принятую checkpoint-first/hybrid модель ADR-046. Не реализовывать новую resume-архитектуру и не объявлять санкционированную сложность дефектом.
   **Evidence:** No code changes were made to the `bioetl` logic (`src/bioetl/application/composite/checkpoint/load_service.py`, `_checkpoint_replay_projection.py`). The existing logic was preserved.

2. **Criterion:** Подлинная provenance уже принятого риска (сообщения пользователя от 2026-10-22).
   **Evidence:** `reports/ledger12457_handoff.json` now cites the exact source-message IDs, UTC timestamps, and excerpts for the existing owner instructions: `Sentinel_fda89a6cbfc48191b7b40052d5cb09f8` (2026-10-22T10:21:21.955023Z; move item 2.8 to accepted risks, section 6) and `Sentinel_1f79397dd26c8191b2136a4b90d7cd32` (2026-10-22T13:58:06.101058Z; record acceptance in 6.1 through the ledger). The messages are traceable transcript references; no public GitHub permalink for either message was supplied. Issue [#12485](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12485) is the risk registration, issue [#12457](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12457) is the completed reconciliation ledger, and [ADR-046](../../../docs/02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md) is the governing architecture decision. These GitHub/ADR references are contextual records, not substitutes for the original message references.

3. **Criterion:** Условия соответствия документации фактической реализации.
   **Evidence:** Updated `docs/02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md` to clarify that `RunLedgerReplayProjection` actually projects rich checkpoint payloads (dependency result maps, enrichment result maps, merge details) into the suffix delta. This directly matches the code in `src/bioetl/application/composite/checkpoint/_checkpoint_replay_projection.py` without promising universal ledger replay.

4. **Criterion:** Проверяемые ссылки на source-of-truth, mismatch, restart и replay.
   **Evidence:** Exact owning test paths and their current result are recorded in the revision-specific status section below and in `reports/ledger12457_handoff.json`. The separate historical CI result for the merged PR is retained as-is; its overall gate failed only because the shadow selector refused three unmapped evidence paths, so no full workflow PASS is claimed.

5. **Criterion:** Подготовить полную доказательную запись для существующего ledger12457.
   **Evidence:** `reports/ledger12457_handoff.json` preserves the prior `ee4a8cbe9dfbf850a919e40b6d04591a3f9126ec` record as history and binds current condition statuses to the exact revision shown below.

6. **Criterion:** Выполнить штатный ARTIFACT_REFRESH check/update/check, docs drift.
   **Evidence:** Verified on tip `d5b6ce5d3d` (Asia/Baghdad wall-clock 2026-10-27 ~18:04 UTC+3):
   - `python -m scripts.docs check-drift --runtime-mirrors --freshness` → OK (0 errors, 0 warnings)
   - `python -m scripts.docs check-links` (full suite; not `--links` alone) → OK — Links/Nav/Specs/Configs/Gold contracts/Workflow inventory/ChEMBL overview/Provider/Runbook/Control-plane/Not-in-nav/Doc drift all passed (`All checks passed.`)
   - `python -m scripts.engineering.ci.update_test_telemetry_baseline --rebind-current-tree` → idempotent; preserves `local_coverage_verify` capture (`source_commit=8a4286d21b…`, coverage 99.66%, `measurement_provenance` present; `source_tree_sha256=394069633f…`)
   - `python -m scripts.engineering.qa refresh-ci-drift-families --check --test-gov --flaky-fingerprint --telemetry --remote-main` → OK (`CI drift families complete (no budget ratchet)`). Per AGENTS.md this is the allowed CI-family path; `refresh_governance_artifacts` was **not** used for this rebind and is not claimed.

## Current status against exact revision

The entries below record the underlying documentation/code evidence and owning-test results from `6500af7e38c569f8f73d358da9ec7045b832a062` (tree `0b65e1c0822f83e91a9cb2d918a09c62c566d103`), which includes current main `9a1d2738053cc0bcaf08e1aba414aa13ca6e32a1`. The status text and supporting ledger update are append-only follow-ups to that verified revision; they are local and do not claim that the target revision is published or merged.

| Condition | Status | Evidence |
| --- | --- | --- |
| ADR-046 matches the implemented bounded hybrid and preserves the already accepted owner decision | **verified** | ADR-046 §2 and Alternative A now consistently state that the projection reconstructs rich payloads from bounded suffix events while still requiring the checkpoint baseline. `test_config_topology_docs_drift.py` passed on the exact tree. Owner-decision source messages are listed in the handoff ledger; no new approval is requested or implied. |
| Source-of-truth, mismatch, restart, and replay scenarios have test/ADR references; the referenced tests pass | **verified locally** | The command returned exit 0 for the referenced tests (`test_config_topology_docs_drift.py`, `test_run_ledger_replay.py`, `test_checkpoint_runtime.py`, `test_pr_lane_results.py`, `test_refresh_governance_artifacts.py`). It does not exercise checkpoint/ledger mismatch reconciliation. |
| Documentation drift and links remain clean | **verified locally** | `python -m scripts.docs check-drift --runtime-mirrors --freshness` exit 0; `python -m scripts.docs check-links` exit 0; `refresh-ci-drift-families --check --evidence` exit 0 after the canonical evidence hash update. |

Current main advanced from `5416aa7a1c0fac5d8d0cbb6119b271e5ca226a73` to `9a1d2738053cc0bcaf08e1aba414aa13ca6e32a1` via PR #12578. A read-only path comparison found no changes to the files in this issue scope between those main revisions; the current main commit was locally merged and rechecked.

At the candidate-preparation snapshot (`e69f1ee1ded3989b338aca844769c171bb73d75c`, 2026-10-27 16:46 UTC), this follow-up had not yet been published and no PR had been created. That is a dated stage record, not a statement about later publication. The historical run `40527527105` remains a failure on the already merged head: its architecture and affected-pytest steps succeeded, while `Shadow compare impact selection` failed on the three exact paths now mapped in the selector change included in this candidate. The owning selector tests passed locally as recorded above; no CI result for this candidate, merge, or issue closure is claimed here.

The original source messages have stable transcript IDs but no public GitHub permalink was provided. Their exact IDs, timestamps, and supplied excerpts are recorded in the handoff ledger; issue and ADR links are identified only as contextual records, not as links to those original messages.
