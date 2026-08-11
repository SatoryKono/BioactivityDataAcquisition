______________________________________________________________________

Version: 3.5.0
Status: active
Class: internal (repo-only entrypoint; excluded from MkDocs)
Owner: BioETL Team
Last verified: '2026-08-11'
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
| `prompt.session.grok-bootstrap` | [library/session/grok-bootstrap.md](library/session/grok-bootstrap.md) | Daily-work session bootstrap |
| `prompt.closeout.grok` | [library/closeout/grok-closeout.md](library/closeout/grok-closeout.md) | Issue/PR closeout (v2.2) |
| `prompt.audit.grok-cycle` | [library/audit/grok-audit-cycle.md](library/audit/grok-audit-cycle.md) | One audit cycle (v2.2) |
| `prompt.audit.orchestrator` | [library/audit/orchestrator.md](library/audit/orchestrator.md) | N-iteration fail-closed loop (v1.0) |
| `prompt.tests.speed-optimization` | [library/tests/speed-optimization-loop.md](library/tests/speed-optimization-loop.md) | Test speed loop |
| `prompt.tests.fix-retest` | [library/tests/fix-retest-loop.md](library/tests/fix-retest-loop.md) | Run → fix → retest |
| `prompt.tests.cycle` | [library/tests/test-cycle.md](library/tests/test-cycle.md) | Cyclic testing (N cycles, lanes) |
| `prompt.docs.ai-audit-planning` | [library/docs/ai-audit-planning.md](library/docs/ai-audit-planning.md) | Docs/AI surface audit plan |
| `prompt.architecture.review` | [library/architecture/review-assessment.md](library/architecture/review-assessment.md) | Architecture review (v2.2) |
| `prompt.observability.dashboard-panel-audit` | [library/observability/dashboard-panel-audit.md](library/observability/dashboard-panel-audit.md) | Grafana panel audit (5 phases, v1.1) |
| `prompt.observability.bi-dashboard-acceptance` | [library/observability/bi-dashboard-acceptance.md](library/observability/bi-dashboard-acceptance.md) | BI acceptance: visual / layout / data |
| `prompt.observability.dashboard-audit-cycle` | [library/observability/dashboard-audit-cycle.md](library/observability/dashboard-audit-cycle.md) | Cyclic dashboard audit (N cycles, fail-closed) |

### Domain audit cards (nine-kit intake)

Short operator-paste cards (v1.1+) with `report.md` + `findings.json`.
Archive megaprompts (opt-in only):

- [generic-nine-audit-kit-2026-08.md](archive/campaigns/generic-nine-audit-kit-2026-08.md)
- [project-audit-orchestrator-kit-2026-08-11.md](archive/campaigns/project-audit-orchestrator-kit-2026-08-11.md)
  (nine domains + full N-iteration orchestrator text)

| Id | Card | Domain |
| --- | --- | --- |
| `prompt.audit.docs-content` | [library/audit/docs-content.md](library/audit/docs-content.md) | Documentation content / drift |
| `prompt.audit.tests-system` | [library/audit/tests-system.md](library/audit/tests-system.md) | Test system / CI gates |
| `prompt.audit.tech-debt` | [library/audit/tech-debt.md](library/audit/tech-debt.md) | Technical debt register |
| `prompt.audit.repo-tree` | [library/audit/repo-tree.md](library/audit/repo-tree.md) | Root / tree hygiene |
| `prompt.audit.github-actions` | [library/audit/github-actions.md](library/audit/github-actions.md) | GitHub Actions supply chain |
| `prompt.audit.agents-runtime` | [library/audit/agents-runtime.md](library/audit/agents-runtime.md) | Agents, skills, agent scripts |
| `prompt.audit.diagrams` | [library/audit/diagrams.md](library/audit/diagrams.md) | Diagrams + render scripts |
| `prompt.audit.docs-pipeline` | [library/audit/docs-pipeline.md](library/audit/docs-pipeline.md) | Docs build/publish pipeline |
| `prompt.architecture.review` | [library/architecture/review-assessment.md](library/architecture/review-assessment.md) | Architecture (v2.3) |

**Routing:**

| Need | Card |
| --- | --- |
| Single domain audit | domain card above |
| One meta cycle | `prompt.audit.grok-cycle` |
| N-iteration audit→issues→fix→CI | `prompt.audit.orchestrator` (`N=1` default; ALLOW_* false) |
| Issue/PR closeout | `prompt.closeout.grok` |

Shared: `fragments/audit-scale.md` (0–3 + optional 0–5 / score_1_5 maps),
`fragments/finding-schema.md` (JSON contract),
`fragments/bi-check-schema.md` (BI checks),
`fragments/orchestrator-guards.md`, `fragments/reports-output.md`.
Artifacts → `reports/audit/<domain>/` or `reports/audit-runs/<run_id>/`.

### Observability routing

| Need | Card |
| --- | --- |
| **Cyclic** audit → issues → fix → re-verify | `prompt.observability.dashboard-audit-cycle` |
| Per-panel render/query → issues → fix (one shot) | `prompt.observability.dashboard-panel-audit` |
| Acceptance only: a11y, layout, data DQ | `prompt.observability.bi-dashboard-acceptance` |
| Full BI matrices / multi-tool notes | archive `bi-dashboard-audit-kit-2026-08-11.md` |

Root-level `grok-*.md` / `test_*.md` paths remain as **redirect stubs** for
bookmarks from #8279.

## CLI

```bash
python -m scripts.ai.prompts list
python -m scripts.ai.prompts show prompt.audit.grok-cycle
python -m scripts.ai.prompts render prompt.session.grok-bootstrap \
  --param TASK="..." --param MODE=implement --param SCOPE="src/bioetl/domain"
python -m scripts.ai.prompts render prompt.audit.grok-cycle --param SCOPE="src/bioetl/domain"
python -m scripts.ai.prompts render prompt.closeout.grok --param SCOPE="issues: #NNNN"
python -m scripts.ai.prompts render prompt.observability.dashboard-panel-audit \
  --param SCOPE="grafana/dashboards" --param AUDIT_MODE=full
python -m scripts.ai.prompts render prompt.observability.bi-dashboard-acceptance \
  --param SCOPE="grafana/dashboards" --param DEPTH=quick --param PLATFORM=grafana
python -m scripts.ai.prompts render prompt.observability.dashboard-audit-cycle \
  --param SCOPE="grafana/dashboards" --param CYCLE_COUNT=1 --param MODE=audit \
  --param DEPTH=quick --param CONTOURS="panels,visual,layout,data"
python -m scripts.ai.prompts render prompt.tests.cycle \
  --param SCOPE="tests/unit/domain" --param LANE=unit-fast \
  --param CYCLE_COUNT=1 --param MODE=run+fix
python -m scripts.ai.prompts render prompt.tests.cycle \
  --param SCOPE=all --param LANE=full --param CYCLE_COUNT=1 --param MODE=run
python -m scripts.ai.prompts render prompt.audit.docs-content \
  --param SCOPE="README.md docs/00-project" --param MODE=audit
python -m scripts.ai.prompts render prompt.audit.github-actions \
  --param SCOPE=".github/workflows" --param MODE=audit
python -m scripts.ai.prompts render prompt.audit.orchestrator \
  --param N=1 --param SCOPE="docs-content,github-actions" --param MODE=plan
python -m scripts.ai.prompts check-registry
python -m scripts.ai.prompts check
python -m scripts.ai.prompts catalog
python -m scripts.ai.prompts new --id prompt.example --class operator-paste
```

Windows: use `.\.venv-win\Scripts\python.exe -m scripts.ai.prompts ...`.

Grok project skills (machine-local install from tracked sources):

```powershell
.\scripts\ai\grok\install_skills.ps1
```

## Multi-domain audit workflow (Grok)

Nine domain cards can be orchestrated as a Grok Build workflow:

| Domain | Prompt id | Card |
| --- | --- | --- |
| 1 Documentation content | `prompt.audit.docs-content` | `library/audit/docs-content.md` |
| 2 Tests system | `prompt.audit.tests-system` | `library/audit/tests-system.md` |
| 3 Technical debt | `prompt.audit.tech-debt` | `library/audit/tech-debt.md` |
| 4 Root / tree hygiene | `prompt.audit.repo-tree` | `library/audit/repo-tree.md` |
| 5 GitHub Actions | `prompt.audit.github-actions` | `library/audit/github-actions.md` |
| 6 Agents + scripts | `prompt.audit.agents-runtime` | `library/audit/agents-runtime.md` |
| 7 Diagrams + scripts | `prompt.audit.diagrams` | `library/audit/diagrams.md` |
| 8 Docs pipeline + scripts | `prompt.audit.docs-pipeline` | `library/audit/docs-pipeline.md` |
| 9 Architecture | `prompt.architecture.review` | `library/architecture/review-assessment.md` |

Workflow script (regenerate if missing):

```powershell
.\.venv-win\Scripts\python.exe scripts\ai\generate_project_domain_audit_workflow.py
```

Path: `.grok/workflows/project-domain-audit.rhai`

Run (Grok TUI): `/workflow project-domain-audit` or workflow tool with
`name: project-domain-audit` and args:

| Arg | Default | Meaning |
| --- | --- | --- |
| `mode` | `audit` | `audit` \| `propose-patches` (ideas only) |
| `language` | `ru` | operator language |
| `domains` | `all` | or CSV: `docs-content,tech-debt,architecture` |
| `require_gh_tracking` | `false` | issues only if true |
| `run_id` | `project-domain-audit` | under `reports/audit/project-domain/<run_id>/` |

Artifacts: per-domain `reports/audit/<domain>/` + rollup
`reports/audit/project-domain/<run_id>/`. Agent budget: ≥10 (9 domains + synth).

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
