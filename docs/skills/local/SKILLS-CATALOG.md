# Local Skills Catalog

Consolidated registry of project-local skills under `.codex/skills/`.

## Canonical Rules

- Prefer local skills from `.codex/skills/` over global `/root/.codex/skills/` when both exist.
- Treat each `SKILL.md` frontmatter (`name`, `description`) as the trigger contract.
- Validate changed skills with:

```bash
python3 /root/.codex/skills/.system/skill-creator/scripts/quick-validate.py <skill-dir>
```

## Skill Groups

### Orchestration

| Skill | Path | Purpose |
|------|------|---------|
| `agent-orchestration` | `.codex/skills/agent-orchestration` | Multi-agent coordination map |
| `py-review-orchestrator` | `.codex/skills/py-review-orchestrator` | Hierarchical review campaign |
| `py-test-swarm` | `.codex/skills/py-test-swarm` | Hierarchical test swarm (L1/L2/L3) |

### Profile Skills

| Skill | Path | Purpose |
|------|------|---------|
| `py-audit-bot` | `.codex/skills/py-audit-bot` | Audit profile workflow |
| `py-code-bot` | `.codex/skills/py-code-bot` | Code implementation profile |
| `py-config-bot` | `.codex/skills/py-config-bot` | Config profile workflow |
| `py-debug-bot` | `.codex/skills/py-debug-bot` | Debug profile workflow |
| `py-doc-bot` | `.codex/skills/py-doc-bot` | Documentation profile workflow |
| `py-plan-bot` | `.codex/skills/py-plan-bot` | Planning profile workflow |
| `py-test-bot` | `.codex/skills/py-test-bot` | Test profile workflow |

### Architecture and Quality

| Skill | Path | Purpose |
|------|------|---------|
| `architecture-guardian` | `.codex/skills/public/architecture-guardian` | Architecture boundary validation |
| `verify-architecture` | `.codex/skills/verify-architecture` | Quick/full architecture checks |
| `vcr-record` | `.codex/skills/vcr-record` | VCR cassette recording/safety |

### Documentation

| Skill | Path | Purpose |
|------|------|---------|
| `documentation-audit` | `.codex/skills/documentation-audit` | Full docs audit and updates |
| `documentation-cascade-audit` | `.codex/skills/documentation-cascade-audit` | Hierarchical docs audit orchestration |

### Build and Design Utilities

| Skill | Path | Purpose |
|------|------|---------|
| `new-pipeline` | `.codex/skills/new-pipeline` | Provider/entity pipeline scaffolding |
| `technical-designer-mermaid` | `.codex/skills/technical-designer-mermaid` | Mermaid technical diagram design |

## Current Consolidation Status

- All local skills are structurally valid.
- `documentation-cascade-audit` has been normalized from template/TODO state to an active skill.
