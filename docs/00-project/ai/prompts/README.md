______________________________________________________________________

Version: 3.8.0
Status: active
Class: internal (repo-only entrypoint; excluded from MkDocs)
Owner: BioETL Team
Last verified: '2026-08-13'
Epic: '#8513'
Phase3: '#8517'

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
| Historical megaprompt / mirror snapshot | **opt-in** [archive/README.md](archive/README.md) or `COLLECTED_PROMPTS_INDEX.md` — not default paste |

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
| `prompt.audit.dual-agent-cycle` | [library/audit/dual-agent-cycle.md](library/audit/dual-agent-cycle.md) | Dual-agent audit→plan→fix→check + role swap (v1.0) |
| `prompt.audit.tests-cycle` | [library/audit/tests-cycle.md](library/audit/tests-cycle.md) | Cyclic **tests-system** audit (v1.0) |
| `prompt.audit.docs-cycle` | [library/audit/docs-cycle.md](library/audit/docs-cycle.md) | Cyclic **docs content** audit (v1.0) |
| `prompt.audit.tech-debt-cycle` | [library/audit/tech-debt-cycle.md](library/audit/tech-debt-cycle.md) | Cyclic **tech-debt** audit (v1.0) |
| `prompt.audit.repo-tree-cycle` | [library/audit/repo-tree-cycle.md](library/audit/repo-tree-cycle.md) | Cyclic **repo hygiene** audit (v1.0) |
| `prompt.audit.cyclic-pack` | [library/audit/cyclic-pack.md](library/audit/cyclic-pack.md) | Pack routing: 10-domain `prompt.audit.cycle.*` |
| `prompt.audit.project.pack` | [library/audit/project/pack.md](library/audit/project/pack.md) | Full project-audit pastes (tech-debt, tests, docs, diagrams, 10-domain cycle) |
| `prompt.audit.sequential-run` | [library/audit/sequential-run.md](library/audit/sequential-run.md) | Sequential `library/audit` run: cycle 1→10, issue/fix/close after each card |
| `prompt.audit.cycle.docs` | [library/audit/cycle/docs.md](library/audit/cycle/docs.md) | Cyclic **docs + scripts/docs** |
| `prompt.audit.cycle.diagrams` | [library/audit/cycle/diagrams.md](library/audit/cycle/diagrams.md) | Cyclic **diagrams + scripts/diagrams** |
| `prompt.audit.cycle.agents-memory` | [library/audit/cycle/agents-memory.md](library/audit/cycle/agents-memory.md) | Cyclic **agents + memory** |
| `prompt.audit.cycle.configs` | [library/audit/cycle/configs.md](library/audit/cycle/configs.md) | Cyclic **project configs** |
| `prompt.audit.cycle.tests` | [library/audit/cycle/tests.md](library/audit/cycle/tests.md) | Cyclic **test layer** |
| `prompt.audit.cycle.tech-debt` | [library/audit/cycle/tech-debt.md](library/audit/cycle/tech-debt.md) | Cyclic **tech-debt** |
| `prompt.audit.cycle.architecture` | [library/audit/cycle/architecture.md](library/audit/cycle/architecture.md) | Cyclic **architecture** (10 categories) |
| `prompt.audit.cycle.telemetry` | [library/audit/cycle/telemetry.md](library/audit/cycle/telemetry.md) | Cyclic **observability / dashboard feed** |
| `prompt.audit.cycle.dashboards` | [library/audit/cycle/dashboards.md](library/audit/cycle/dashboards.md) | Cyclic **dashboard render/design** |
| `prompt.audit.cycle.coderabbit` | [library/audit/cycle/coderabbit.md](library/audit/cycle/coderabbit.md) | Cyclic **full project + CodeRabbit** |
| `prompt.audit.role-auditor` | [library/audit/role-auditor.md](library/audit/role-auditor.md) | Dual-agent Auditor (A) duties |
| `prompt.audit.role-planner` | [library/audit/role-planner.md](library/audit/role-planner.md) | Dual-agent Planner (B) duties |
| `prompt.tests.speed-optimization` | [library/tests/speed-optimization-loop.md](library/tests/speed-optimization-loop.md) | Test speed loop |
| `prompt.tests.fix-retest` | [library/tests/fix-retest-loop.md](library/tests/fix-retest-loop.md) | Run → fix → retest |
| `prompt.tests.cycle` | [library/tests/test-cycle.md](library/tests/test-cycle.md) | Cyclic testing (N cycles, lanes) |
| `prompt.docs.ai-audit-planning` | [library/docs/ai-audit-planning.md](library/docs/ai-audit-planning.md) | Docs/AI surface audit plan |
| `prompt.architecture.review` | [library/architecture/review-assessment.md](library/architecture/review-assessment.md) | Architecture review (v2.3) |
| `prompt.architecture.cycle` | [library/architecture/architecture-cycle.md](library/architecture/architecture-cycle.md) | Cyclic **project architecture** audit (v1.1): **10 categories** → plan → implement |
| `prompt.audit.coderabbit-project-cycle` | [library/audit/coderabbit-project-cycle.md](library/audit/coderabbit-project-cycle.md) | Exhaustive cyclic **project** audit + **CodeRabbit** dual-pass (v1.0, N=10) |
| `prompt.observability.dashboard-panel-audit` | [library/observability/dashboard-panel-audit.md](library/observability/dashboard-panel-audit.md) | Grafana panel audit (5 phases, v1.1) |
| `prompt.observability.bi-dashboard-acceptance` | [library/observability/bi-dashboard-acceptance.md](library/observability/bi-dashboard-acceptance.md) | BI acceptance: visual / layout / data |
| `prompt.observability.dashboard-audit-cycle` | [library/observability/dashboard-audit-cycle.md](library/observability/dashboard-audit-cycle.md) | Exhaustive cyclic audit (v2.0) of every panel × viewport × theme × zoom (Tier-1 100% / Tier-2 200%) — density, typography, color, scroll, whitespace, data, render |
| `prompt.observability.dashboard-operator-playbook` | [library/observability/dashboard-operator-playbook.md](library/observability/dashboard-operator-playbook.md) | Per-panel operator questions, analysis order, 5–10 value-dependent scenarios |
| `prompt.observability.dashboard-v5.pack` | [library/observability/dashboard-v5/pack.md](library/observability/dashboard-v5/pack.md) | V5 residual router (R-A/R-E/R-B landed; R-C PR; R-D/R-F leftover) |
| `prompt.observability.dashboard-v5.implement` | [library/observability/dashboard-v5/implement.md](library/observability/dashboard-v5/implement.md) | Implement leftover V5 — babysit #8987, optional R-D |
| `prompt.observability.dashboard-v5.closeout` | [library/observability/dashboard-v5/closeout.md](library/observability/dashboard-v5/closeout.md) | Close V5 residuals against origin/main |
| `prompt.observability.dashboard-v5.audit-rf` | [library/observability/dashboard-v5/audit-rf.md](library/observability/dashboard-v5/audit-rf.md) | R-F light / 200% / leftover NV cycle |
| `prompt.observability.grafana-audit.master` | [library/observability/grafana-audit/master.md](library/observability/grafana-audit/master.md) | Complete evidence-based read-only Grafana audit |
| `prompt.observability.grafana-audit.visual` | [library/observability/grafana-audit/visual.md](library/observability/grafana-audit/visual.md) | Palette, WCAG contrast, typography, visual encoding |
| `prompt.observability.grafana-audit.layout` | [library/observability/grafana-audit/layout.md](library/observability/grafana-audit/layout.md) | Composition, first viewport, variables, drill-down |
| `prompt.observability.grafana-audit.data-integrity` | [library/observability/grafana-audit/data-integrity.md](library/observability/grafana-audit/data-integrity.md) | Full lineage, exact queries, invariants, reconciliation |
| `prompt.observability.grafana-audit.regression` | [library/observability/grafana-audit/regression.md](library/observability/grafana-audit/regression.md) | Baseline/candidate retest and release gate |
| `prompt.audit.generic-nine.pack` | [library/audit/generic-nine/pack.md](library/audit/generic-nine/pack.md) | Nine-domain generic code/project audit kit (2026-08-11) |

### Domain audit cards (nine-kit intake)

Routing: `prompt.audit.generic-nine.pack` →
[library/audit/generic-nine/](library/audit/generic-nine/README.md).
Short operator-paste cards (v1.2+) with `report.md` + `findings.json` and
kit-specific extras. Archive megaprompts (opt-in only):

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
| All nine one-shot domains | `prompt.audit.generic-nine.pack` |
| One meta cycle | `prompt.audit.grok-cycle` |
| N-iteration audit→issues→fix→CI (single agent) | `prompt.audit.orchestrator` (`N=1` default; ALLOW_* false) |
| Dual-agent cycle + external audit prompt + CR + peer review | `prompt.audit.dual-agent-cycle` (`OUTER_CYCLES=1`; ALLOW_* false) |
| Cyclic 10-domain pack (docs → CR) | `prompt.audit.cyclic-pack` → `prompt.audit.cycle.*` in [library/audit/cycle/](library/audit/cycle/README.md) |
| Sequential audit + issues/fix/close | `prompt.audit.sequential-run` |
| Cyclic project architecture | `prompt.architecture.cycle` |
| Exhaustive project audit + CodeRabbit | `prompt.audit.coderabbit-project-cycle` |
| Issue/PR closeout | `prompt.closeout.grok` |

### Dual-agent cyclic audit

Two roles in one run (**Auditor A** / **Planner B**), external audit prompt
(`AUDIT_PROMPT_SOURCE=file:…` or library id), CodeRabbit then agent, mutual
plan review, two implement streams, peer review, optional role swap.

| Need | Card |
| --- | --- |
| Full cycle paste | `prompt.audit.dual-agent-cycle` |
| Auditor duties only | `prompt.audit.role-auditor` |
| Planner duties only | `prompt.audit.role-planner` |

Fragments: `dual-agent-handoff`, `coderabbit-dual-pass`, `peer-review-gate`,
`orchestrator-guards`. Artifacts → `reports/audit-runs/<run_id>/`.

```bash
python -m scripts.ai.prompts render prompt.audit.dual-agent-cycle \
  --param AUDIT_PROMPT_SOURCE=file:docs/00-project/ai/prompts/library/audit/github-actions.md \
  --param SCOPE=".github/workflows" --param MODE=plan --param OUTER_CYCLES=1
```

Workflow (P3, not in this drop): planned `.grok/workflows/dual-agent-audit-cycle.rhai`.

Shared: `fragments/audit-scale.md` (0–3 + optional 0–5 / score_1_5 maps),
`fragments/finding-schema.md` (JSON contract),
`fragments/bi-check-schema.md` (BI checks),
`fragments/orchestrator-guards.md`, `fragments/reports-output.md`.
Artifacts → `reports/audit/<domain>/` or `reports/audit-runs/<run_id>/`.

### Observability routing

| Need | Card |
| --- | --- |
| Complete evidence-based read-only audit | `prompt.observability.grafana-audit.master` |
| Specialist palette / contrast / typography audit | `prompt.observability.grafana-audit.visual` |
| Specialist composition / navigation audit | `prompt.observability.grafana-audit.layout` |
| Specialist forensic data-integrity audit | `prompt.observability.grafana-audit.data-integrity` |
| Baseline/candidate regression acceptance | `prompt.observability.grafana-audit.regression` |
| **Cyclic** audit → issues → fix → re-verify | `prompt.observability.dashboard-audit-cycle` |
| Per-panel render/query → issues → fix (one shot) | `prompt.observability.dashboard-panel-audit` |
| Acceptance only: a11y, layout, data DQ | `prompt.observability.bi-dashboard-acceptance` |
| Per-panel operator questions + value-dependent scenarios | `prompt.observability.dashboard-operator-playbook` |
| Full BI matrices / multi-tool notes | archive `bi-dashboard-audit-kit-2026-08-11.md` |

Folder index and **sequential run order**:
[library/observability/README.md](library/observability/README.md).
The five-card set lives in
[library/observability/grafana-audit/README.md](library/observability/grafana-audit/README.md).
The earlier `grafana-six` kit is deprecated (successor metadata on each card).

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
  --param SCOPE="grafana/dashboards" --param N=20 --param MODE=audit \
  --param DEPTH=full --param MONITORING=false
python -m scripts.ai.prompts render prompt.observability.grafana-audit.master \
  --param SCOPE="grafana/dashboards" --param MONITORING=false
python -m scripts.ai.prompts render prompt.observability.grafana-audit.data-integrity \
  --param SCOPE="grafana/dashboards" \
  --param TIME_RANGE="2026-08-13T00:00:00Z/2026-08-13T01:00:00Z" \
  --param MONITORING=false
python -m scripts.ai.prompts render prompt.observability.grafana-audit.regression \
  --param BASELINE_REF="<sha>" --param CANDIDATE_REF=HEAD \
  --param BASELINE_REPORT="reports/audit/grafana/<run_id>/report.md" \
  --param FIXED_WINDOWS="2026-08-13T00:00:00Z/2026-08-13T01:00:00Z" \
  --param MONITORING=false
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
python -m scripts.ai.prompts render prompt.audit.dual-agent-cycle \
  --param AUDIT_PROMPT_SOURCE=file:docs/00-project/ai/prompts/library/audit/tech-debt.md \
  --param SCOPE="reports/quality" --param MODE=plan --param OUTER_CYCLES=1
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
