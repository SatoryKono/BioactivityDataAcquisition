______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Last verified: '2026-08-11'
Epic: '#8513'
Phase: 0 (#8515) + domain-audit intake 2026-08

______________________________________________________________________

# Prompt Library Inventory

Classification of artifacts under `docs/00-project/ai/prompts/` for the Prompt
Library program. This file is **not** governance SSOT. On conflict, runtime
trees (`.codex/**` / `.junie/**` / `.devin/**`) and
`docs/00-project/NORMATIVE_SOURCES.md` win.

## Out-of-library ownership (do not migrate into library bodies)

| Surface | Path | Owner |
| --- | --- | --- |
| Runtime agents | `.codex/agents/`, `.junie/agents/`, `.devin/agents/` | runtime |
| Skills | `.codex/skills/**`, `.junie/skills/**` | runtime |
| Devin prompts/workflows | `.devin/prompts/`, `.devin/workflows/` | Devin |
| CodeRabbit | `.coderabbit.yaml` | tool |
| Memory seed | `scripts/memory/prompts/` | memory tooling |

## Root-level classification

| path | class | status | size_bytes | has_paste_body | evaluation_bloat | related_ssot | phase1_action |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| `README.md` | index | active | 648 | no | yes (stub meta) | — | restore entrypoint |
| `COLLECTED_PROMPTS_INDEX.md` | index | active | 2785 | no | no | `collected/` | leave (archive index) |
| `INVENTORY.md` | index | active | — | no | no | #8513 | leave |
| `grok-audit-cycle.md` | operator-paste | active | 5569 | yes | yes | AGENTS.md | keep-as-card → `library/audit/` |
| `grok-closeout.md` | operator-paste | active | 5597 | yes | yes | AGENTS.md | keep-as-card → `library/closeout/` |
| `test_speed_optimization_loop.md` | operator-paste | active | 11712 | yes | yes | AGENTS.md, tests | keep-as-card → `library/tests/` |
| `test_fix_retest_loop.md` | operator-paste | active | 6953 | yes | yes | AGENTS.md, tests | keep-as-card → `library/tests/` |
| `docs_ai_audit_planning_codex_prompt.md` | operator-paste | active | 13888 | yes | yes | docs/00-project/ai | keep-as-card → `library/docs/` |
| `architecture_review_and_refactoring_assessment.md` | operator-paste | active | 22697 | yes | yes | RULES, ADR | keep-as-card → `library/architecture/` |
| `documentation_diagrams_audit.md` | campaign | archive-candidate | 21804 | yes | yes | docs diagrams | archive (#8517) |
| `architecture_metric_exemptions_tasks_json_prompt.md` | campaign | archive-candidate | 33363 | yes | yes | quality scorecard | archive (#8517) |
| `refactor_orchestration_prompt.md` | campaign | archive-candidate | 28082 | yes | yes | architecture | archive (#8517) |
| `scripts_inventory_consolidation_cleanup_prompt.md` | historical | archive-candidate | 9372 | yes | yes | scripts/ | archive (#8517) |
| `specialized-prompts-1-scripts-inventory.md` | historical | archive-candidate | 10660 | yes | yes | scripts/ | archive (#8517) |
| `specialized-prompts-2-coderabbit-audit.md` | campaign | archive-candidate | 17999 | yes | yes | `.coderabbit.yaml` | archive (#8517) |
| `role-specific-agents-1-py-audit-bot.md` | mirror | archive-candidate | 4146 | no | yes | `.codex/agents/py-audit-bot.md` | archive mirror |
| `role-specific-agents-2-py-debug-bot.md` | mirror | archive-candidate | 3121 | no | yes | `.codex/agents/py-debug-bot.md` | archive mirror |
| `runtime-agentry-1-CODEX-RUNTIME.md` | mirror | archive-candidate | 10137 | no | yes | `.codex/agents/CODEX-RUNTIME.md` | archive mirror |
| `runtime-agentry-2-JUNIE-RUNTIME.md` | mirror | archive-candidate | 10960 | no | yes | `.junie/agents/JUNIE-RUNTIME.md` | archive mirror |
| `skills-1-research-workflow.md` | mirror | archive-candidate | 10237 | no | yes | `.codex/skills/**` | archive mirror |
| `skills-2-verify-architecture.md` | mirror | archive-candidate | 3213 | no | yes | `.codex/skills/**` | archive mirror |
| `workflows-1-master.md` | mirror | archive-candidate | 14577 | no | yes | runtime workflows | archive mirror |
| `workflows-2-post-change.md` | mirror | archive-candidate | 13360 | no | yes | POST_CHANGE_VALIDATION | archive mirror |
| `setup-prompts-1-devin-setup-prompt.md` | mirror | archive-candidate | 11350 | no | yes | `.devin/prompts/` | archive mirror |
| `setup-prompts-2-optimization-prompt.md` | mirror | archive-candidate | 12046 | no | yes | `.devin/prompts/` | archive mirror |
| `memory-py-audit-bot.md` | mirror | archive-candidate | 11626 | no | yes | `docs/.../memory-py-audit-bot.md` | archive mirror |
| `agent-memory.md` | mirror | archive-candidate | 13865 | no | yes | `docs/.../agent-memory.md` | archive mirror |
| `trash/README.md` | historical | archived | 1798 | no | no | — | leave (legacy draft) |

## Phase 1 migrate shortlist (#8514)

Target **6** active operator-paste cards:

| Source | Target id | Target path |
| --- | --- | --- |
| `grok-audit-cycle.md` | `prompt.audit.grok-cycle` | `library/audit/grok-audit-cycle.md` |
| `grok-closeout.md` | `prompt.closeout.grok` | `library/closeout/grok-closeout.md` |
| `test_speed_optimization_loop.md` | `prompt.tests.speed-optimization` | `library/tests/speed-optimization-loop.md` |
| `test_fix_retest_loop.md` | `prompt.tests.fix-retest` | `library/tests/fix-retest-loop.md` |
| `docs_ai_audit_planning_codex_prompt.md` | `prompt.docs.ai-audit-planning` | `library/docs/ai-audit-planning.md` |
| `architecture_review_and_refactoring_assessment.md` | `prompt.architecture.review` | `library/architecture/review-assessment.md` |

Migration rules: strip evaluation scorecards from paste body; add YAML
frontmatter; compose shared guardrails via `fragments/`.

## Phase 3 archive / demote candidates (#8517)

### Runtime mirrors → `archive/mirrors/`

- `role-specific-agents-*.md`
- `runtime-agentry-*.md`
- `skills-*.md`
- `workflows-*.md`
- `setup-prompts-*.md`
- `memory-py-audit-bot.md`, `agent-memory.md`

### Campaigns / historical megaprompts → `archive/campaigns/`

- `documentation_diagrams_audit.md`
- `architecture_metric_exemptions_tasks_json_prompt.md`
- `refactor_orchestration_prompt.md`
- `scripts_inventory_consolidation_cleanup_prompt.md`
- `specialized-prompts-1-scripts-inventory.md`
- `specialized-prompts-2-coderabbit-audit.md`
- `generic-nine-audit-kit-2026-08.md` (+ `…-SOURCES.md`) — intake 2026-08-11;
  active short cards: `library/audit/{docs-content,tests-system,tech-debt,
  repo-tree,github-actions,agents-runtime,diagrams,docs-pipeline}.md` and
  `library/architecture/review-assessment.md` v2.3
- `project-audit-orchestrator-kit-2026-08-11.md` (+ `…-SOURCES.md`) — kit #2
  with orchestrator; active: `library/audit/orchestrator.md`
  (`prompt.audit.orchestrator`); domain cards v1.1+ (`findings.json`)

### External archive (already)

- `docs/99-archive/guides/stale-ai-prompts/`
- `collected/` (if present) — archive-only snapshots

## Fragment candidates (shared blocks)

| Fragment | Purpose |
| --- | --- |
| `fragments/read-order.md` | Mandatory read order (AGENTS → NORMATIVE → memory) |
| `fragments/git-safety.md` | No main commits, no foreign WIP, no force-push |
| `fragments/debt-budget-ban.md` | Tech-debt budgets must not grow |
| `fragments/env-guardrail.md` | No `.env` edits without explicit approval |
| `fragments/evidence-contract.md` | Evidence format for findings/closeout |
| `fragments/language-ru.md` | Default Russian operator language |

## Notes

- Size bytes are approximate snapshot values from 2026-08-10 checkout.
- `evaluation_bloat=yes` means meta/scorecard sections dominate or exceed the
  useful paste body (common after automated “prompt evaluation” rewrites).
- Prefer short library cards + fragments over megaprompts for default discovery.
