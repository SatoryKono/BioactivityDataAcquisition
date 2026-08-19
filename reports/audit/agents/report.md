# Аудит AI runtime, scripts и memory

Run: `20260819T080519Z-agents-memory-cycle-51eaed1f81`

Base: `origin/main@51eaed1f81183e8ad150e622fab1fba19afb0550`

Branch: `fix/audit-project-51eaed1f81`

Scope: `AGENTS.md .codex/ .junie/ .devin/ docs/00-project/ai/ scripts/ai/ src/memory/ scripts/memory/`

## Executive summary

За 10 итераций подтверждено 5 findings: один P0, три P1 и один P2. P0 и ещё три finding исправлены в рабочей ветке; P1 `AUD-004` остаётся открытым, потому что 13 просроченных чужих episodic-записей нельзя удалять без отдельного разрешения. Секретов, credential-like значений, private keys или полных conversation dump в scope не найдено.

Итоговый `surface_score = 1`: используется прямая шкала 0–3 из audit contract, без dimension mapping. Это минимальный score трёх контуров из-за незакрытого retention violation.

| Surface | surface_score | Итог |
| --- | ---: | --- |
| Runtime instructions and mirrors | 3 | Parity, doctor, governance и architecture contracts проходят после remediation. |
| AI and memory scripts | 2 | Критический launcher defect закрыт и автоматизирован; inventory/catalog проходят без увеличения cap, но общий pretest блокирует независимый integration-VCR drift. |
| Memory lifecycle | 1 | Catalog/schema/smoke/tests проходят, но retention gate находит 13 expired records. |

Legend: 3 — good; 2 — acceptable; 1 — weak; 0 — unacceptable.

## Findings

| ID | Priority | Status | Observation | Issue |
| --- | --- | --- | --- | --- |
| AUD-001 | P1 / High | remediated, pending merge | Published dashboard skill mirror failed parity. | [#9006](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9006) |
| AUD-002 | P2 / Medium | remediated, pending merge | Governance normalizer contradicted CODEX-RUNTIME architecture tokens and doctor omitted the drift. | [#9007](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9007) |
| AUD-003 | P0 / Critical | remediated, pending merge | Vibe launcher logged the complete prompt and recommended `curl | bash`. | [#9004](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9004) |
| AUD-004 | P1 / High | open | Retention check reports 13 expired episodic records. | [#9005](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9005) |
| AUD-005 | P1 / High | remediated, pending merge | Generated project-full prompts contained 12 broken relative links. | [#9008](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9008) |

Полная machine-readable evidence находится в `findings.json` рядом с этим отчётом.

## Evidence by contour

### Runtime

- Inventory traced root precedence through `.codex/agents/**`, `.codex/skills/**`, `.junie/**`, `.devin/**`, docs mirrors, scripts and CI contracts.
- `bash scripts/ai/junie/check_junie_mirror.sh --check` — exit 0, Codex–Junie parity OK.
- `bash scripts/ai/codex/check_skills_mirror.sh --check` — baseline mismatch for `observability-dashboard`; post-fix exit 0.
- `python -m scripts.ai.sync.governance --root . --only all --check` — baseline normalization drift; post-fix exit 0.
- `python scripts/ai/codex/doctor.py --json` — post-fix `ok=true`, findings empty.
- `python -m scripts.docs check-drift --runtime-mirrors --freshness` — 0 errors, 0 warnings.
- 64 focused runtime/governance/prompt regression tests — passed.

### Scripts

- Scoped Bash syntax scan — passed; `shellcheck scripts/ai/vibe/launch.sh` — passed.
- `ruff check scripts/ai scripts/memory src/memory` — passed.
- Ruff format check for the five changed Python files — passed.
- Static scans found no remaining full-prompt log pattern, pipe-to-shell installer guidance, private-key headers or credential assignments in scope.
- `python -m scripts.ai.prompts check` — 83 registry entries, 54 active cards, 0 errors/warnings, generated-link drift 0.
- `PYTHONPATH=src python -m scripts.docs check-links --links --specs --configs` — passed.

### Memory

- `PYTHONPATH=src python -m memory.tooling.workflow smoke` — pre-task and post-task smoke passed.
- `PYTHONPATH=src python -m memory.tooling.validate` — passed.
- 307 memory unit/integration/architecture/security test invocations — passed.
- Curated freshness/review checks — 5 current records, no due/stale items.
- Actor provenance requirements for `BIOETL_AI_RUNTIME` and `BIOETL_AI_AGENT` are present; vendor evidence remains `NOT_PROVEN` where no dated external evidence exists.
- `PYTHONPATH=src python -m memory.tooling.prune --check --json` — exit 1: 13 candidates, `density_excess=0`, `invalid_metadata=[]`, `policy_violation=true`; no apply was run.

## Remediation applied

- Replaced Vibe prompt-content logging with prompt length only and removed pipe-to-shell guidance from Bash and PowerShell launchers.
- Added launcher safety enforcement to `native_runtime_contract.py`.
- Made the Codex doctor report governance normalization drift.
- Added a CODEX-RUNTIME-specific canonical source block to the governance normalizer so required policy links are preserved.
- Refreshed the dashboard docs skill mirror from its canonical runtime source.
- Added deterministic project-full prompt link rebasing plus `--check`/`--sync` CLI support; repaired 12 generated links.
- No `.env` file, technical-debt budget, exemption, threshold or family cap was changed.

## Closeout blockers and skipped checks

1. Memory retention remains unresolved (`AUD-004`). Required follow-up after explicit destructive-operation approval: review the same 13 candidates, run the authorized prune apply workflow, then rerun `PYTHONPATH=src python -m memory.tooling.prune --check --json`.
2. `bash scripts/engineering/dev/pretest_guardrails.sh` now passes scripts inventory, lifecycle, active-script cap (338/338), catalog, hotspot and repo-identity checks, then stops at pre-existing `configs/quality/integration_vcr_policy.yaml` drift. This task does not touch integration/VCR behavior, so that unrelated policy artifact was not rewritten.
3. `python -m scripts.engineering.qa report-debt-governance-gates` reports 45 pass and 0 fail after rebasing onto the refreshed `origin/main`; debt budgets remain unchanged.
4. PowerShell AST parsing was skipped because `pwsh` is unavailable in this WSL environment. Follow-up on Windows: `pwsh -NoProfile -Command "[void][scriptblock]::Create((Get-Content -Raw scripts/ai/vibe/launch.ps1))"`.
5. Required hosted CI was not available before branch publication. Local green tests do not substitute for required PR checks.

Proof-or-stop must therefore report a non-ADMIT outcome until the remaining governance receipt is green. Merge is not authorized (`ALLOW_MERGE=false`).
