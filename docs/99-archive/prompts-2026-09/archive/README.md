# Prompt archive (opt-in)

Historical and non-default prompt material. **Not** default operator paste SSOT.

| Subdir | Contents |
| --- | --- |
| `mirrors/` | Snapshots that duplicated runtime agents/skills/workflows — prefer `.codex/**` / `.junie/**` / `.devin/**` |
| `campaigns/` | Long playbooks and pre-library megaprompts (evaluation bloat retained for history) |
| `retired-project-new/` | Unregistered 10-card `project/new/` megacards; use overlays + `generated/` |
| `retired-project-new2/` | Unregistered 14-card `project/new2/` megacards (`ALLOW_*=true`); use `compatibility/prompt.audit.project.new2.*` |

**Discovery:** active paste lives under [`../library/`](../library/) via
[`../REGISTRY.yaml`](../REGISTRY.yaml) / `python -m scripts.ai.prompts list`.
This archive is **opt-in only** (Phase 3 / #8517).

## Mirrors (`mirrors/`)

| File | Prefer instead |
| --- | --- |
| `role-specific-agents-1-py-audit-bot.md` | `.codex/agents/py-audit-bot.md` |
| `role-specific-agents-2-py-debug-bot.md` | `.codex/agents/py-debug-bot.md` |
| `runtime-agentry-1-CODEX-RUNTIME.md` | `.codex/agents/CODEX-RUNTIME.md` |
| `runtime-agentry-2-JUNIE-RUNTIME.md` | `.junie/agents/JUNIE-RUNTIME.md` |
| `skills-1-research-workflow.md` | `.codex/skills/**` |
| `skills-2-verify-architecture.md` | `.codex/skills/verify-architecture/` |
| `workflows-1-master.md` | runtime workflows / skills |
| `workflows-2-post-change.md` | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` |
| `setup-prompts-1-devin-setup-prompt.md` | `.devin/prompts/` |
| `setup-prompts-2-optimization-prompt.md` | `.devin/prompts/` |
| `memory-py-audit-bot.md` | `docs/00-project/ai/memory/memory-py-audit-bot.md` |

## Campaigns (`campaigns/`)

| File | Prefer instead |
| --- | --- |
| `documentation_diagrams_audit.md` | `library/audit/diagrams.md` |
| `architecture_metric_exemptions_tasks_json_prompt.md` | quality scorecard tooling |
| `refactor_orchestration_prompt.md` | `library/architecture/review-assessment.md` |
| `scripts_inventory_consolidation_cleanup_prompt.md` | `scripts/engineering/repo` inventory |
| `specialized-prompts-1-scripts-inventory.md` | same |
| `specialized-prompts-2-coderabbit-audit.md` | `docs/03-guides/coderabbit-audit-playbook.md` |
| `pre-library-*.md` | removed (encoding-corrupt historical copies); use `library/**` |
| `generic-nine-audit-kit-2026-08.md` (+ SOURCES) | `prompt.audit.generic-nine.pack` + `library/audit/*` domain cards |
| `project-audit-orchestrator-kit-2026-08-11.md` (+ SOURCES) | `library/audit/orchestrator.md` |
| `bi-dashboard-audit-kit-2026-08-11.md` (+ SOURCES) | `library/observability/bi-dashboard-acceptance.md` |

## External archive

- `docs/99-archive/guides/stale-ai-prompts/`
- [`../COLLECTED_PROMPTS_INDEX.md`](../COLLECTED_PROMPTS_INDEX.md) — collected snapshots index

## Related

- Epic: #8513 · Phase 3: #8517
- Active catalog: [`../generated/CATALOG.md`](../generated/CATALOG.md)
