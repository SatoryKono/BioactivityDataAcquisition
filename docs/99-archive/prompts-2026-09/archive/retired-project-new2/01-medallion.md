---
id: prompt.audit.project.new2.medallion
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - SCOPE
  - MODE
  - LANGUAGE
  - AUDIT_MODE
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - BASE_BRANCH
  - REPO
  - WORK_BRANCH
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/project-requirements-audit.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/RULES.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - docs/02-architecture/decisions/ADR-002-medallion-architecture.md
  - docs/02-architecture/decisions/ADR-014-deterministic-writes.md
  - docs/02-architecture/decisions/ADR-018-gold-strict-validation.md
  - src/bioetl/domain/medallion.py
  - src/bioetl/infrastructure/storage/bronze_writer.py
  - src/bioetl/infrastructure/storage/silver_writer.py
  - src/bioetl/infrastructure/storage/gold_writer.py
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Treating architecture-scorecard as a substitute for write-path evidence
  - Implicit NoOp Silver validator
  - Wall-clock defaults on replay-critical clocks
  - Non-atomic data writes (skip temp→replace)
  - Raising debt budgets
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
tags: [audit, medallion, bronze, silver, gold, quarantine, replay, cycle, operator]
summary: Cyclic Medallion write-path audit — Bronze/Silver/Gold, quarantine, determinism, ALLOW_* true, early-stop
max_body_lines: 230
---

# Cyclic Medallion / storage / replay audit

Не заменяет `prompt.audit.project.new.architecture`. Объект: **write-path**
Bronze → Silver → Gold, quarantine, replay clocks. Loop:
`prompt.audit.orchestrator`. Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/domain/medallion.py src/bioetl/infrastructure/storage/` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/medallion-cycle-new2-<shortsha>` |

## Anchors

- Policy: `domain/medallion.py`; ADR-002 / ADR-014 / ADR-018
- Atomic write: temp → `os.replace`
- Bronze same-batch overwrite: identical payload skip, else fail-closed
- Silver: explicit validator port (no implicit NoOp)
- Gold: strict validation; PK/business `unique`
- Replay clocks: no wall-clock defaults
- PROVEN finding MUST have `requirement_id`
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. SCOPE exists; empty → STOP.
3. `run_id = <UTC>-medallion-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Policy** | Map write modes vs `medallion.py` and ADR. Flag silent overwrite / missing fail-closed. |
| **B Bronze/Silver/Gold** | Writers, quarantine, Delta/time-travel claims vs code. Atomicity. |
| **C Replay** | Clocks, determinism of artifacts, unique keys on PK/business. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[medallion][<REQ-id>][P#]`. |
| **E Fix** | Minimal storage/domain change. No budget raises. Never `main`. |
| **F Validate** | Focused storage/architecture tests in SCOPE. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 и без overwrite/clock regression → STOP.

## Success

- Write-path findings with file+command evidence
- No wall-clock replay defaults; no implicit NoOp Silver
