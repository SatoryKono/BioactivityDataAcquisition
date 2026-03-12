# Local Skills Catalog (BioETL Core)

*Статус: internal-published (Internal / Extended)*
*Обновлено: 2026-03-12 (Wave 6 consolidation)*

Consolidated registry of BioETL-focused local skills under `.claude/skills/`.

## Canonical Rules

- `.claude/skills/` is the canonical source for repository-local skills.
- `docs/00-project/ai/skills/local/` is a generated mirror and must not be edited manually.
- Treat each `SKILL.md` frontmatter (`name`, `description`) as the trigger contract.

## Skill Groups

### Orchestration

| Skill | Path | Purpose |
|------|------|---------|
| `agent-orchestration` | `.claude/skills/agent-orchestration` | Multi-agent coordination map |
| `py-review-orchestrator` | `.claude/skills/py-review-orchestrator` | Hierarchical review campaign |
| `py-test-swarm` | `.claude/skills/py-test-swarm` | Hierarchical test swarm (L1/L2/L3) |

### Profile Skills

| Skill | Path | Purpose |
|------|------|---------|
| `py-audit-bot` | `.claude/skills/py-audit-bot` | Audit profile workflow |
| `py-config-bot` | `.claude/skills/py-config-bot` | Config profile workflow |
| `py-debug-bot` | `.claude/skills/py-debug-bot` | Debug profile workflow |
| `py-doc-bot` | `.claude/skills/py-doc-bot` | Documentation profile workflow |
| `py-plan-bot` | `.claude/skills/py-plan-bot` | Planning profile workflow |
| `py-test-bot` | `.claude/skills/py-test-bot` | Test profile workflow |

### Architecture and Quality

| Skill | Path | Purpose |
|------|------|---------|
| `architecture-guardian` | `.claude/skills/public/architecture-guardian` | Architecture boundary validation |
| `verify-architecture` | `.claude/skills/verify-architecture` | Quick/full architecture checks |
| `vcr-record` | `.claude/skills/vcr-record` | VCR cassette recording/safety |

### Documentation

| Skill | Path | Purpose |
|------|------|---------|
| `documentation-audit` | `.claude/skills/documentation-audit` | Full docs audit and updates |
| `documentation-cascade-audit` | `.claude/skills/documentation-cascade-audit` | Hierarchical docs audit orchestration |

### Utilities

| Skill | Path | Purpose |
|------|------|---------|
| `capability-discovery` | `.claude/skills/capability-discovery` | Discover available agents/skills/quality commands |
| `deep-research` | `.claude/skills/deep-research` | Structured deep research workflow |
| `repo-config` | `.claude/skills/repo-config` | Resolve dynamic repository configuration |
| `suggest-users` | `.claude/skills/suggest-users` | Suggest reviewers/assignees from repo context |
| `create-pr` | `.claude/skills/create-pr` | PR creation workflow guidance |

### Build and Design

| Skill | Path | Purpose |
|------|------|---------|
| `new-pipeline` | `.claude/skills/new-pipeline` | Provider/entity pipeline scaffolding |
| `technical-designer-mermaid` | `.claude/skills/technical-designer-mermaid` | Mermaid technical diagram design |

## Wave 6 Consolidation (2026-03-12)

Removed 6 skills from `.claude/skills/` (runtime) and docs mirrors:

| Removed | Reason |
|---------|--------|
| `collecting-evidence` | Ledger framework — not used in BioETL |
| `synthesizing-pillars` | Ledger framework — not used |
| `making-decisions` | Ledger framework — not used |
| `generating-constrained-specs` | Ledger framework — not used |
| `initializing-ledger` | Ledger framework — not used |
| `nci-analysis` | Propaganda analysis — irrelevant for ETL |

Also removed 2 OpenAI metadata files (`*.openai.yaml`).

## Mirror Doc Index

- [agent-orchestration](agent-orchestration/SKILL.md)
- [capability-discovery](capability-discovery/SKILL.md)
- [create-pr](create-pr/SKILL.md)
- [deep-research](deep-research/SKILL.md)
- [documentation-audit](documentation-audit/SKILL.md)
- [documentation-cascade-audit](documentation-cascade-audit/SKILL.md)
- [new-pipeline](new-pipeline/SKILL.md)
- [py-audit-bot](py-audit-bot/SKILL.md)
- [py-config-bot](py-config-bot/SKILL.md)
- [py-debug-bot](py-debug-bot/SKILL.md)
- [py-doc-bot](py-doc-bot/SKILL.md)
- [py-plan-bot](py-plan-bot/SKILL.md)
- [py-review-orchestrator](py-review-orchestrator/SKILL.md)
- [py-test-bot](py-test-bot/SKILL.md)
- [py-test-swarm](py-test-swarm/SKILL.md)
- [repo-config](repo-config/SKILL.md)
- [suggest-users](suggest-users/SKILL.md)
- [technical-designer-mermaid](technical-designer-mermaid/SKILL.md)
- [vcr-record](vcr-record/SKILL.md)
- [verify-architecture](verify-architecture/SKILL.md)
- [architecture-guardian (public)](public/architecture-guardian/SKILL.md)

## Notes

- `py-code-bot` is excluded from the active published catalog: starting from `ORCHESTRATION.md v4.0`, production code is written by the orchestrator directly.
