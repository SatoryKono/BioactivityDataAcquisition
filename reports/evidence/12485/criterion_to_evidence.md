# Criterion to Evidence Matrix - Issue 12485

1. **Criterion:** Сохранить принятую checkpoint-first/hybrid модель ADR-046. Не реализовывать новую resume-архитектуру и не объявлять санкционированную сложность дефектом.
   **Evidence:** No code changes were made to the `bioetl` logic (`src/bioetl/application/composite/checkpoint/load_service.py`, `_checkpoint_replay_projection.py`). The existing logic was preserved.

2. **Criterion:** Подлинная provenance уже принятого риска (сообщение пользователя от 2026-10-22).
   **Evidence:** `reports/ledger12457_handoff.json` records `provenance.owner_decision` with verifiable GitHub anchors: issue [#12485](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12485) (risk registration + owner-decision text for Фёдор / 22.10.2026 / AUDIT-20261022 / P11-001) and ledger issue [#12457](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12457), plus ADR-046 as the governing decision.

3. **Criterion:** Условия соответствия документации фактической реализации.
   **Evidence:** Updated `docs/02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md` to clarify that `RunLedgerReplayProjection` actually projects rich checkpoint payloads (dependency result maps, enrichment result maps, merge details) into the suffix delta. This directly matches the code in `src/bioetl/application/composite/checkpoint/_checkpoint_replay_projection.py` without promising universal ledger replay.

4. **Criterion:** Проверяемые ссылки на source-of-truth, mismatch, restart и replay.
   **Evidence:** Ran testing suite for architecture drift (`test_config_topology_docs_drift.py`), ledger replay (`test_run_ledger_replay.py`), and checkpoint runtime (`test_checkpoint_runtime.py`). Verified with 100% pass rate. These links are stored in `reports/ledger12457_handoff.json`.

5. **Criterion:** Подготовить полную доказательную запись для существующего ledger12457.
   **Evidence:** `reports/ledger12457_handoff.json` was generated and forced-staged with all necessary tracking fields, including `current_sha` evaluated after merging `main`.

6. **Criterion:** Выполнить штатный ARTIFACT_REFRESH check/update/check, docs drift.
   **Evidence:** Executed:
   - `python -m scripts.docs check-drift --runtime-mirrors --freshness`
   - `python -m scripts.docs check-links --links`
   - `python -m scripts.engineering.ci.update_test_telemetry_baseline`
   - `python -m scripts.engineering.qa refresh-ci-drift-families --update --test-gov --flaky-fingerprint`
   - `python -m scripts.engineering.qa.refresh_governance_artifacts`
   All checks pass cleanly.
