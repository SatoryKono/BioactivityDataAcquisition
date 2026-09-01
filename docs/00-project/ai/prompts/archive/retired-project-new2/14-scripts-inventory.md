---
id: prompt.audit.project.new2.scripts-inventory
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
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - scripts/engineering/repo/catalog.yaml
  - configs/quality/scripts_inventory_manifest.json
  - configs/quality/scripts_lifecycle_registry.json
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Raising active_script_count_max
  - Root-level ad-hoc scripts / _tmp_*.py
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Deleting scripts without lifecycle registry update
tags: [audit, scripts, inventory, lifecycle, cycle, operator]
summary: Cyclic scripts inventory audit — catalog, lifecycle, no-growth cap, ALLOW_* true, early-stop
max_body_lines: 220
---

# Cyclic scripts inventory / lifecycle audit

`scripts/engineering/repo/catalog.yaml` — canonical roots, no-growth active
count. Не docs-pipeline и не diagrams-scripts как единственный SCOPE.
Loop: `prompt.audit.orchestrator`. Library defaults: **`ALLOW_*=true`**.
**УВЕЛИЧИВАТЬ budget/cap техдолга и active_script_count_max ЗАПРЕЩЕНО.**

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `scripts/ configs/quality/scripts_inventory_manifest.json configs/quality/scripts_lifecycle_registry.json` |
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
| `WORK_BRANCH` | `fix/scripts-inv-cycle-new2-<shortsha>` |

## Anchors

- Catalog + lifecycle JSON
- Root allowlist / no scripts in repo root (except catalog allowlist)
- Canonical invocation for new integrations
- PROVEN finding MUST have `requirement_id`
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA. Snapshot cap/count from catalog (read-only).
2. `run_id = <UTC>-scripts-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
3. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Tracked scripts vs manifest vs lifecycle registry. Orphans/unknown. |
| **B Cap** | Count vs `active_script_count_max`. Increase → `REJECTED_POLICY`. |
| **C Root** | Root clutter / device-name files. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[scripts][<REQ-id>][P#]`. |
| **E Fix** | Register, deprecate with replacement+sunset, or move to canonical root. |
| **F Validate** | Repo inventory checks if documented. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.

## Success

- Manifest/registry delta ↓ orphans or flat
- Cap not raised
