# Local Skills Catalog (BioETL Core)

Consolidated registry of BioETL-focused local skills under `.codex/skills/`.

## Canonical Rules

- `.codex/skills/` is the canonical source for repository-local skills.
- `docs/00-project/ai/skills/local/` is a generated mirror and must not be edited manually.
- `scripts/ai/codex/skills-mirror-contract.json` defines sanctioned parity with
  `.devin/skills/`: entrypoint and catalog membership must match, shared
  references must be identical, and runtime-specific metadata/content variants
  remain explicit.
- Treat each `SKILL.md` frontmatter (`name`, `description`) as the trigger contract.
- Verify and sync the local docs mirror with:

```bash
bash scripts/ai/codex/check_skills_mirror.sh --check
bash scripts/ai/codex/check_skills_mirror.sh --sync
```

`--sync` regenerates only the transformed docs mirror. It never overwrites the
Devin runtime tree; Codex-Devin parity violations require an owner-reviewed
runtime change.

## Skill Groups

### Orchestration

| Skill                    | Path                                   | Purpose                            |
| ------------------------ | -------------------------------------- | ---------------------------------- |
| `agent-orchestration`    | `.codex/skills/agent-orchestration`    | Multi-agent coordination map       |
| `hierarchical-evidence-orchestration` | `.codex/skills/hierarchical-evidence-orchestration` | Hierarchical evidence campaigns |
| `py-review-orchestrator` | `.codex/skills/py-review-orchestrator` | Hierarchical review campaign       |
| `py-test-swarm`          | `.codex/skills/py-test-swarm`          | Hierarchical test swarm (L1/L2/L3) |

### Profile Skills

| Skill                      | Path                                     | Purpose                                                    |
| -------------------------- | ---------------------------------------- | ---------------------------------------------------------- |
| `py-audit-bot`             | `.codex/skills/py-audit-bot`             | Audit profile workflow                                     |
| `py-code-bot`              | `.codex/skills/py-code-bot`              | Deprecated compatibility profile for historical references |
| `py-architecture-debt-bot` | `.codex/skills/py-architecture-debt-bot` | Full architecture-debt reduction workflow                  |
| `py-config-bot`            | `.codex/skills/py-config-bot`            | Config profile workflow                                    |
| `py-debug-bot`             | `.codex/skills/py-debug-bot`             | Debug profile workflow                                     |
| `py-doc-bot`               | `.codex/skills/py-doc-bot`               | Documentation profile workflow                             |
| `py-plan-bot`              | `.codex/skills/py-plan-bot`              | Planning profile workflow                                  |
| `py-test-bot`              | `.codex/skills/py-test-bot`              | Test profile workflow                                      |

`py-code-bot` is retained only as a compatibility surface for historical references. In the current Codex workflow, production code is written directly by the orchestrator.

### Architecture and Quality

| Skill                   | Path                                         | Purpose                          |
| ----------------------- | -------------------------------------------- | -------------------------------- |
| `architecture-guardian` | `.codex/skills/public/architecture-guardian` | Architecture boundary validation |
| `verify-architecture`   | `.codex/skills/verify-architecture`          | Quick/full architecture checks   |
| `vcr-record`            | `.codex/skills/vcr-record`                   | VCR cassette recording/safety    |

### Observability

| Skill                          | Path                                         | Purpose                                               |
| ------------------------------ | -------------------------------------------- | ----------------------------------------------------- |
| `grafana-dashboard-render`     | `.codex/skills/grafana-dashboard-render`     | Render, preflight, and audit shipped Grafana dashboards |
| `grafana-dashboard-extension`  | `.codex/skills/grafana-dashboard-extension`  | Edit and validate shipped Grafana dashboards          |
| `prometheus-metric-discovery`  | `.codex/skills/prometheus-metric-discovery`  | Discover real metrics, labels, and selectors          |
| `prometheus-query-debugger`    | `.codex/skills/prometheus-query-debugger`    | Debug PromQL semantics and empty-state behavior       |
| `prometheus-alert-rule-editor` | `.codex/skills/prometheus-alert-rule-editor` | Create and tune Prometheus-backed alert rules         |
| `prometheus-rule-testing`      | `.codex/skills/prometheus-rule-testing`      | Validate repo-backed Prometheus rules with `promtool` |

### Documentation

| Skill                         | Path                                        | Purpose                               |
| ----------------------------- | ------------------------------------------- | ------------------------------------- |
| `documentation-audit`         | `.codex/skills/documentation-audit`         | Full docs audit and updates           |
| `documentation-cascade-audit` | `.codex/skills/documentation-cascade-audit` | Hierarchical docs audit orchestration |

### Research and Planning Utilities

| Skill                          | Path                                         | Purpose                                           |
| ------------------------------ | -------------------------------------------- | ------------------------------------------------- |
| `capability-discovery`         | `.codex/skills/capability-discovery`         | Discover available agents/skills/quality commands |
| `collecting-evidence`          | `.codex/skills/collecting-evidence`          | Build traceable evidence objects                  |
| `deep-research`                | `.codex/skills/deep-research`                | Structured deep research workflow                 |
| `hierarchical-evidence-orchestration` | `.codex/skills/hierarchical-evidence-orchestration` | Coordinate hierarchical evidence collection |
| `synthesizing-pillars`         | `.codex/skills/synthesizing-pillars`         | Convert evidence into synthesis insights          |
| `making-decisions`             | `.codex/skills/making-decisions`             | Turn synthesis into explicit decisions            |
| `generating-constrained-specs` | `.codex/skills/generating-constrained-specs` | Generate PRD/architecture specs from decisions    |
| `initializing-ledger`          | `.codex/skills/initializing-ledger`          | Initialize decision/evidence workspace            |
| `repo-config`                  | `.codex/skills/repo-config`                  | Resolve dynamic repository configuration          |
| `suggest-users`                | `.codex/skills/suggest-users`                | Suggest reviewers/assignees from repo context     |
| `create-pr`                    | `.codex/skills/create-pr`                    | PR creation workflow guidance                     |
| `nci-analysis`                 | `.codex/skills/nci-analysis`                 | Manipulation/disinformation pattern analysis      |

### Build and Design Utilities

| Skill                        | Path                                       | Purpose                              |
| ---------------------------- | ------------------------------------------ | ------------------------------------ |
| `new-pipeline`               | `.codex/skills/new-pipeline`               | Provider/entity pipeline scaffolding |
| `py-reproducibility-audit`  | `.codex/skills/py-reproducibility-audit`  | Reproducibility and replay audit  |
## Current Consolidation Status

- All local skills are structurally valid.
- `documentation-cascade-audit` has been normalized from template/TODO state to an active skill.
- Shared wrapper, evidence/decision, and Grafana/Prometheus prerequisite contracts are factored into reusable `references/` files.
- Active project skills provide `agents/openai.yaml` metadata and are covered by the Codex skill architecture gate.

## Mirror Doc Index

- [agent-orchestration](agent-orchestration/SKILL.md)
- [hierarchical-evidence-orchestration](hierarchical-evidence-orchestration/SKILL.md)
- [capability-discovery](capability-discovery/SKILL.md)
- [collecting-evidence](collecting-evidence/SKILL.md)
- [create-pr](create-pr/SKILL.md)
- [deep-research](deep-research/SKILL.md)
- [hierarchical-evidence-orchestration](hierarchical-evidence-orchestration/SKILL.md)
- [documentation-audit](documentation-audit/SKILL.md)
- [documentation-cascade-audit](documentation-cascade-audit/SKILL.md)
- [grafana-dashboard-render](grafana-dashboard-render/SKILL.md)
- [grafana-dashboard-extension](grafana-dashboard-extension/SKILL.md)
- [generating-constrained-specs](generating-constrained-specs/SKILL.md)
- [initializing-ledger](initializing-ledger/SKILL.md)
- [making-decisions](making-decisions/SKILL.md)
- [nci-analysis](nci-analysis/SKILL.md)
- [new-pipeline](new-pipeline/SKILL.md)
- [py-audit-bot](py-audit-bot/SKILL.md)
- [py-architecture-debt-bot](py-architecture-debt-bot/SKILL.md)
- [py-code-bot](py-code-bot/SKILL.md)
- [py-config-bot](py-config-bot/SKILL.md)
- [py-debug-bot](py-debug-bot/SKILL.md)
- [py-doc-bot](py-doc-bot/SKILL.md)
- [py-plan-bot](py-plan-bot/SKILL.md)
- [py-reproducibility-audit](py-reproducibility-audit/SKILL.md)
- [py-review-orchestrator](py-review-orchestrator/SKILL.md)
- [py-reproducibility-audit](py-reproducibility-audit/SKILL.md)
- [prometheus-alert-rule-editor](prometheus-alert-rule-editor/SKILL.md)
- [prometheus-metric-discovery](prometheus-metric-discovery/SKILL.md)
- [prometheus-query-debugger](prometheus-query-debugger/SKILL.md)
- [prometheus-rule-testing](prometheus-rule-testing/SKILL.md)
- [py-test-bot](py-test-bot/SKILL.md)
- [py-test-swarm](py-test-swarm/SKILL.md)
- [repo-config](repo-config/SKILL.md)
- [suggest-users](suggest-users/SKILL.md)
- [synthesizing-pillars](synthesizing-pillars/SKILL.md)
- [technical-designer-mermaid](technical-designer-mermaid/SKILL.md)
- [vcr-record](vcr-record/SKILL.md)
- [verify-architecture](verify-architecture/SKILL.md)


## Shared Generic Skills

Additional non-BioETL generic skills may coexist under `.codex/skills/` (for example discovery, decision, and research helpers). They are intentionally excluded from the core catalog above.
