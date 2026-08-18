______________________________________________________________________

Version: 1.0.0
Status: internal (repo-only entrypoint; excluded from MkDocs nav/publication)
Class: internal
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# AI Documentation Surface

Этот каталог собирает AI-related documentation surfaces для BioETL:
runtime-facing guides, published mirrors, prompts, skills, memory notes и
supporting internal artifacts.

## Surface Types

- **Runtime source**: live orchestration, agent registries и runtime-specific
  instructions живут в `.codex/agents/` и parallel runtime registries.
- **Published mirrors and guides**: `docs/00-project/ai/agents/` хранит
  discoverable docs mirrors, guides и runtime-facing helper docs.
- **Memory surface**: `docs/00-project/ai/memory/` хранит project memory entry
  point и role-specific memory sheets.
- **Prompts surface**: `docs/00-project/ai/prompts/` — Prompt Library
  (operator paste cards, fragments, `REGISTRY.yaml`, archive); not runtime SSOT.
- **Skills surface**: `docs/00-project/ai/skills/` хранит published mirrors,
  catalogs и reference mirrors для локальных/global skills.

## Ownership Contract

- `.codex/**` is the runtime source of truth for Codex behavior.
- No active `ai/claude/**` runtime tree is retained in the local workflow
  surface; historical Claude references should be read only as migration
  context.
- `docs/00-project/ai/**` is the published/internal mirror and contributor
  guidance surface; it does not redefine runtime behavior by itself.
- Default sync direction is runtime tree first, docs mirror second.

See [AI Runtime Mirror Ownership](agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md).

## Reading Priority

При чтении AI docs используй такой приоритет:

1. runtime source в `.codex/agents/`, `.codex/skills/` и related Codex runtime
   surfaces
1. canonical governance docs:
   - `docs/00-project/NORMATIVE_SOURCES.md`
   - `docs/00-project/RULES.md`
   - `docs/01-requirements/REQUIREMENTS.md`
   - accepted ADRs in `docs/02-architecture/decisions/`
1. AI docs under `docs/00-project/ai/` and their published/internal mirrors

Если published AI docs расходятся с runtime source или canonical governance,
приоритет у runtime source и canonical governance.

## Main Entry Points

- [AI Agents Context](agents/README.md) — runtime-specific agent guidance,
  published mirrors, guides, policy notes
- [AI Memory Surface](memory/README.md) — project memory entry point and
  role-specific memory sheets
- [AI Prompts Surface](prompts/README.md) — Prompt Library (registry, fragments,
  active paste cards, archive)
- [Skills Mirror](skills/README.md) — published mirrors, practical indexes and
  skill references

## Notes

- This directory is intentionally **repo-only** and excluded from MkDocs; use
  repository-path links for discoverability.
- Different runtimes may keep intentionally divergent orchestration docs.
- Prompts, memory sheets and skill mirrors are support artifacts; they do not
  redefine project rules by themselves.
- When contributors need to change runtime behavior, they SHOULD edit the
  relevant runtime tree first and then refresh the docs mirror if needed.

## Grok operator aids

- [grok/README.md](grok/README.md) — skills sources + install
- [agents/guides/grok-operator-runbook.md](agents/guides/grok-operator-runbook.md)
- [agents/guides/grok-tui-config-checklist.md](agents/guides/grok-tui-config-checklist.md)
- [prompts/library/session/grok-bootstrap.md](prompts/library/session/grok-bootstrap.md)
  (`prompt.session.grok-bootstrap`)
- [prompts/library/closeout/grok-closeout.md](prompts/library/closeout/grok-closeout.md)
  (`prompt.closeout.grok`, v2.2)
- [prompts/library/audit/grok-audit-cycle.md](prompts/library/audit/grok-audit-cycle.md)
  (`prompt.audit.grok-cycle`, v2.2)
- Domain audits: `prompt.audit.docs-content`, `tests-system`, `tech-debt`,
  `repo-tree`, `github-actions`, `agents-runtime`, `diagrams`, `docs-pipeline`
- Ten-domain cyclic pack: `prompt.audit.cycle.*` in
  [prompts/library/audit/cycle/](prompts/library/audit/cycle/README.md)
- Orchestrated loop: `prompt.audit.orchestrator`
- BI acceptance: `prompt.observability.bi-dashboard-acceptance`
- Cyclic dashboards: `prompt.audit.cycle.dashboards` (alias:
  `prompt.observability.dashboard-audit-cycle`)
- V5 residuals: `prompt.observability.dashboard-v5.pack` (implement /
  closeout / R-F audit)
- Cyclic testing: `prompt.tests.cycle` (see
  [prompts/README.md](prompts/README.md))
- Install skills: `.\scripts\ai\grok\install_skills.ps1`
- CLI: `python -m scripts.ai.prompts list|render|check`
