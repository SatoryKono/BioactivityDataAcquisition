# Audit Report: P03 Application Layer & Orchestration

## A. Audit Manifest
- **Repo**: SatoryKono/BioactivityDataAcquisition
- **Branch**: main
- **Pinned SHA (code reviewed)**: 56484ffd123b719a91811a53da6e284522d02a0d
- **Clean/Dirty Worktree**: Clean
- **Scope**: `src/bioetl/application/**`
- **Audit ID**: pack-v2.1/P03
- **Available inputs**: `reports/audit/pack-v2.1/P02-ddd-domain.md` (domain map / port inventory) and `reports/audit/pack-v2.1/P06-composition-di.md` (DI/wiring; declared input for P03) are both present on the pinned revision. They are used as cross-pack context; this report does **not** re-litigate P02/P06 findings.

## B. Scope/ownership and exclusions
- **In-scope**: Use-case orchestration, application services, failure/retry semantics, side-effect sequencing, async lifecycle.
- **Excluded**: Domain invariants (P02), Composition Root / DI assembly ownership (P06), Execution traces (P10).

## C. Evidence Ledger
- `E1 NORMATIVE`: `docs/00-project/RULES.md`
- `E2 STATIC`: `src/bioetl/application/core/runner.py`, `src/bioetl/application/core/batch_execution/run_service.py`, `src/bioetl/application/core/lifecycle/batch_fsm.py`
- `E3 EXECUTABLE`: Named pytest invocations in the Verification Matrix (H). Checkout for those runs: `2013e9015dfee5ce7767aa8434ed31eed60e3e66` (**≠** pinned `56484ffd123b719a91811a53da6e284522d02a0d`; tip adds this audit report + inventory only — `git diff --stat 56484ffd12..2013e9015d -- src/bioetl/application/ tests/architecture/test_layer_dependencies.py tests/architecture/test_no_structlog_in_application_interfaces.py tests/unit/application/core/test_batch_execution_lifecycle.py` empty). Env: `uv` + Python `3.13.16`, Linux-x86_64.
- `E4 CROSS-PACK`: P02 domain/port inventory and P06 DI/wiring report (present; not treated as missing).

## D. Findings Register

No confirmed application-layer defect was established by this bounded review. The import-boundary conclusions below are limited to the named architecture tests. Cancellation evidence is limited to two named lifecycle tests. Failure/retry policy and general side-effect ordering remain `NOT_VERIFIABLE`; they are not reported as passing. Complete application-service ↔ port implementation enumeration across the whole tree was not re-derived here from P06 and is therefore also left `NOT_VERIFIABLE` — **not** because P06 is absent.

## E. Quantitative Scorecard
- Layer Separation (only tested import boundaries): 5/5
- Cancellation finalization (two targeted scenarios): verified for those scenarios only.
- Failure/retry semantics, side-effect sequencing, and complete application DI mapping enumeration: `NOT_VERIFIABLE`.
- Overall: 3/5 — bounded evidence does not support a repo-wide orchestration/lifecycle score.

## F. Cross-cutting/root-cause clusters
- No confirmed cross-cutting defect. Lifecycle and side-effect coverage remains incomplete.

## G. Prioritized roadmap P0→P3
- No code remediation is proposed from the bounded evidence. Extend the audit only if evidence for failure/retry policy, side-effect sequencing, or a full application-side DI mapping walk from P06 is required.

## H. Verification Matrix
- Import boundary: `uv run --frozen --no-build pytest tests/architecture/test_layer_dependencies.py::test_application_layer_no_infrastructure_imports` — checkout=`2013e9015d`, UTC start=`2026-11-02T22:48:02Z`, UTC end=`2026-11-02T22:48:03Z`, exit_code=`0`, output=`1 passed in 0.65s` → **PASS**.
- No direct `structlog` in application interfaces: `uv run --frozen --no-build pytest tests/architecture/test_no_structlog_in_application_interfaces.py::TestNoStructlogInApplicationLayer::test_no_structlog_in_application_layer` — checkout=`2013e9015d`, UTC start=`2026-11-02T22:48:03Z`, UTC end=`2026-11-02T22:48:05Z`, exit_code=`0`, output=`1 passed in 0.85s` → **PASS**.
- Cancellation finalization: `uv run --frozen --no-build pytest tests/unit/application/core/test_batch_execution_lifecycle.py::test_run_service_finalizes_on_cancelled_error tests/unit/application/core/test_batch_execution_lifecycle.py::test_run_service_finalizes_when_cancel_interrupts_shield` — checkout=`2013e9015d`, UTC start=`2026-11-02T22:48:05Z`, UTC end=`2026-11-02T22:48:06Z`, exit_code=`0`, output=`2 passed in 1.06s` → **PASS** (those two scenarios only).
- Failure/retry semantics and side-effect sequencing: **NOT_RUN** / `NOT_VERIFIABLE`; no command was executed and no result is claimed.

## I. NOT_VERIFIABLE and missing evidence
- Failure/retry semantics and general side-effect sequencing were not exercised.
- P02 and P06 reports are **present**; residual `NOT_VERIFIABLE` items are untested orchestration concerns and incomplete enumeration of application-service bindings from the P06 map — not missing pack inputs. Finding id `APP_MISSING_DI_MAP` is **not** raised.

## J. Self-check
- The report distinguishes tested import boundaries and cancellation cases from untested retry/side-effect coverage. No maximum lifecycle score is inferred from architecture tests. Available P02/P06 inputs are acknowledged; fabricated Overall 5 and false missing-input claims from Jules tip `92ae76e1` are rejected.

## K. Verdict
The named architecture checks support the stated import-boundary conclusions, and the two targeted cancellation-finalization tests pass. This evidence does not establish full application-layer compliance for retries, side-effect sequencing, or shutdown scenarios beyond those tests.
