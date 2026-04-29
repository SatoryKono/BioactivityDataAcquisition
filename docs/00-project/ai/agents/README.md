______________________________________________________________________

Version: 1.2.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-04'

______________________________________________________________________

# Agent Catalog — BioETL (Mirror)

*Статус: internal-published | Docs mirror (2026-04-04)*

Этот каталог является зеркалом документации по агентам для разных рантаймов AI в BioETL.

## Surface Note

- Это **публикуемое зеркало** документации.
- Codex source-of-truth orchestration живёт в `.codex/agents/ORCHESTRATION.md`
  и связанных `.codex/agents/py-*.md`.
- Параллельные runtime copies могут жить в других runtime trees; использовать
  их нужно только внутри соответствующего runtime.
- Логические профили `py-*` отображаются на native runtime mechanisms
  (`spawn_agent` roles в Codex, runtime-specific agent tools/registries в других
  средах).
- Edit local runtime behavior in `.codex/**` first; use this docs surface for
  published mirrors, navigation, and contributor guidance.

Ownership and sync rules are fixed in
[AI Runtime Mirror Ownership](policy/AI_RUNTIME_MIRROR_OWNERSHIP.md).

## BioETL Core (8 активных агентов)

| Agent                    | Role             | Primary Responsibility                       |
| ------------------------ | ---------------- | -------------------------------------------- |
| `py-audit-bot`           | Compliance Gate  | Code/architecture audit, RULES.md compliance |
| `py-plan-bot`            | Architect        | Task planning, RF-\* decomposition           |
| `py-test-bot`            | Tester           | Tests (baseline/final/retest), coverage, VCR |
| `py-config-bot`          | Config Engineer  | YAML configs (pipeline/DQ/filter)            |
| `py-debug-bot`           | Troubleshooter   | RCA, bug fixes, regression debugging         |
| `py-doc-bot`             | Technical Writer | Docs, ADR, CHANGELOG, Mermaid diagrams       |
| `py-test-swarm`          | QA Orchestrator  | Hierarchical testing (L1->L2->L3)            |
| `py-review-orchestrator` | Review Lead      | Code review (S1-S8 stages)                   |

## Related Files

- Repository path `.codex/agents/ORCHESTRATION.md` — Codex source-of-truth orchestration
- Repository path `.gemini/agents/ORCHESTRATION.md` — Gemini runtime copy
- [ORCHESTRATION.md](agents/ORCHESTRATION.md) — published mirror for documentation/navigation
- [AGENT.md](guides/AGENT.md) — Core Engineering Guide
- [CLAUDE.md](guides/CLAUDE.md) — Claude CLI specific guide
- [GEMINI.md](guides/GEMINI.md) — Gemini CLI specific guide
- [AI Runtime Mirror Ownership](policy/AI_RUNTIME_MIRROR_OWNERSHIP.md) —
  source-of-truth, sync direction, allowed divergence
