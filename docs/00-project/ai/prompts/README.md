______________________________________________________________________

Version: 3.0.0
Status: active
Class: internal (repo-only entrypoint; excluded from MkDocs)
Owner: BioETL Team
Last verified: '2026-08-10'
Epic: '#8513'

______________________________________________________________________

# AI Prompts Surface — Prompt Library

Operator/task **paste templates**, shared **fragments**, and a machine-readable
**registry**. This directory is **not** governance or runtime SSOT.

## Authority / precedence

When a prompt conflicts with active sources, **active sources win**:

1. Runtime agents/skills: `.codex/**`, `.junie/**`, `.devin/**`
2. Governance: `AGENTS.md` → `docs/00-project/NORMATIVE_SOURCES.md` →
   `RULES.md` / accepted ADRs
3. This Prompt Library (operator aid only)

See [AI Runtime Mirror Ownership](../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md).

## When to use what

| Need | Use |
| --- | --- |
| Role behavior / routing | Runtime agent profile (`.codex/agents/py-*.md`) |
| Multi-step procedure | Skill under `.codex/skills/**` |
| Short operator paste for a task | **Library card** here (`library/**`) |
| Shared guardrail block | **Fragment** (`fragments/**`) |
| Historical megaprompt / mirror snapshot | `archive/**` or `COLLECTED_PROMPTS_INDEX.md` |

## Layout

```text
docs/00-project/ai/prompts/
  README.md                 # this entrypoint
  INVENTORY.md              # Phase 0 classification
  REGISTRY.yaml             # machine-readable catalog
  _schema/prompt.schema.json
  fragments/                # composable guardrail blocks
  library/                  # active operator-paste cards
    audit/ closeout/ tests/ docs/ architecture/ observability/
  archive/                  # mirrors + campaigns (not default paste)
  generated/CATALOG.md      # generated from REGISTRY
  COLLECTED_PROMPTS_INDEX.md
```

## Active operator paste (start here)

| Id | Card | Summary |
| --- | --- | --- |
| `prompt.closeout.grok` | [library/closeout/grok-closeout.md](library/closeout/grok-closeout.md) | Short issue/PR closeout |
| `prompt.audit.grok-cycle` | [library/audit/grok-audit-cycle.md](library/audit/grok-audit-cycle.md) | One audit cycle (default) |
| `prompt.tests.speed-optimization` | [library/tests/speed-optimization-loop.md](library/tests/speed-optimization-loop.md) | Test speed loop |
| `prompt.tests.fix-retest` | [library/tests/fix-retest-loop.md](library/tests/fix-retest-loop.md) | Run → fix → retest |
| `prompt.docs.ai-audit-planning` | [library/docs/ai-audit-planning.md](library/docs/ai-audit-planning.md) | Docs/AI surface audit plan |
| `prompt.architecture.review` | [library/architecture/review-assessment.md](library/architecture/review-assessment.md) | Read-only architecture review |
| `prompt.observability.dashboard-panel-audit` | [library/observability/dashboard-panel-audit.md](library/observability/dashboard-panel-audit.md) | Grafana panel audit (5 phases) |

Root-level `grok-*.md` / `test_*.md` paths remain as **redirect stubs** for
bookmarks from #8279.

## CLI

```bash
python -m scripts.ai.prompts list
python -m scripts.ai.prompts show prompt.audit.grok-cycle
python -m scripts.ai.prompts render prompt.audit.grok-cycle --param SCOPE="src/bioetl/domain"
python -m scripts.ai.prompts render prompt.observability.dashboard-panel-audit \
  --param SCOPE="grafana/dashboards" --param AUDIT_MODE=full
python -m scripts.ai.prompts check-registry
python -m scripts.ai.prompts check
python -m scripts.ai.prompts new --id prompt.example --class operator-paste
```

Windows: use `.\.venv-win\Scripts\python.exe -m scripts.ai.prompts ...`.

## Surface types

- **operator-paste** — short parameterized templates for paste into an agent session
- **fragment** — shared blocks composed by `includes` / render CLI
- **campaign** — long playbooks; opt-in only (`archive/campaigns/` or labeled)
- **mirror** — runtime snapshots; **not** paste SSOT (`archive/mirrors/`)
- **historical / index** — discoverability only

## Related

- Epic: [#8513](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8513)
- Precedent short templates: [#8279](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8279)
- [INVENTORY.md](INVENTORY.md) · [REGISTRY.yaml](REGISTRY.yaml) · [generated/CATALOG.md](generated/CATALOG.md)
- [COLLECTED_PROMPTS_INDEX.md](COLLECTED_PROMPTS_INDEX.md)
- Parent AI surface: [../README.md](../README.md)
