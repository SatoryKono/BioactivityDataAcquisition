# Muse workflows registry — audit library

Subordinate execution surface for `docs/00-project/ai/prompts/library/audit/`.
Prompts stay operator-paste templates; SSOT is `.codex/.junie/.devin` + `AGENTS.md` stack.
Workflows use Workflow API V1 (`host.parallel` / `host.agent` / `host.pipeline`)
with evidence schema `{complete, evidence, unresolved}`.

Deprecated prompts have no workflow: `prompt.audit.cyclic-pack` and
`prompt.audit.grok-cycle` redirect to `audit-cycle.js`.

| Prompt id | Prompt file | Muse workflow | Args |
| --- | --- | --- | --- |
| `prompt.audit.agents-runtime` | `library/audit/agents-runtime.md` | `.muse/workflows/audit/audit-domain.js` | `DOMAIN=agents-runtime, SCOPE, MODE, LANGUAGE, AUDIT_MODE, REQUIRE_GH_TRACKING` |
| `prompt.architecture.review` | `library/audit/architecture-review.md` | `.muse/workflows/audit/audit-domain.js` | `DOMAIN=architecture-review, SCOPE, MODE, LANGUAGE, AUDIT_MODE` |
| `prompt.audit.diagrams` | `library/audit/diagrams.md` | `.muse/workflows/audit/audit-domain.js` | `DOMAIN=diagrams, SCOPE, MODE, LANGUAGE, AUDIT_MODE, REQUIRE_GH_TRACKING` |
| `prompt.audit.github-actions` | `library/audit/github-actions.md` | `.muse/workflows/audit/audit-domain.js` | `DOMAIN=github-actions, SCOPE, MODE, LANGUAGE, AUDIT_MODE, REQUIRE_GH_TRACKING` |
| `prompt.audit.repo-tree` | `library/audit/repo-tree.md` | `.muse/workflows/audit/audit-domain.js` | `DOMAIN=repo-tree, SCOPE, MODE, LANGUAGE, AUDIT_MODE, REQUIRE_GH_TRACKING` |
| `prompt.audit.tech-debt` | `library/audit/tech-debt.md` | `.muse/workflows/audit/audit-domain.js` | `DOMAIN=tech-debt, SCOPE, MODE, LANGUAGE, AUDIT_MODE, REQUIRE_GH_TRACKING` |
| `prompt.observability.grafana-audit.master` | `library/audit/grafana-master.md` | `.muse/workflows/audit/grafana-master.js` | `SCOPE, CONTOURS, VIEWPORTS, THEMES, MONITORING, OUTPUT_DIR, LANGUAGE` |
| `prompt.observability.grafana-audit.data-integrity` | `library/audit/grafana-data.md` | `.muse/workflows/audit/grafana-master.js` | contour `data` (`TIME_RANGE, VARIABLES, REFERENCE_SPEC, KNOWN_EVENTS`) |
| `prompt.observability.grafana-audit.layout` | `library/audit/grafana-layout.md` | `.muse/workflows/audit/grafana-master.js` | contour `layout` (`DASHBOARD_PURPOSE, USER_ROLES, USER_JOURNEYS, SERVICE_MAP`) |
| `prompt.observability.grafana-audit.visual` | `library/audit/grafana-visual.md` | `.muse/workflows/audit/grafana-master.js` | contour `visual` (`SCREENSHOTS, TYPOGRAPHY_POLICY, CRITICAL_STATES`) |
| `prompt.observability.grafana-audit.regression` | `library/audit/grafana-regression.md` | `.muse/workflows/audit/grafana-regression.js` | `BASELINE_REF*, CANDIDATE_REF, BASELINE_REPORT*, FIXED_WINDOWS, VARIABLE_MATRIX, LANGUAGE` |
| `prompt.debug.isolate` | `library/audit/debug.md` | `.muse/workflows/audit/debug-isolate.js` | `SCOPE, MODE=debug, LANGUAGE` (read-only; refresh via `prompt.tests.fix-retest`) |
| `prompt.audit.cycle` | `library/audit/cycle.md` | `.muse/workflows/audit/audit-cycle.js` | `DOMAIN, SCOPE, MODE, CYCLE_COUNT, AUDIT_MODE, REQUIRE_GH_TRACKING, REPO, BASE, WORK_BRANCH, LANGUAGE` |
| `prompt.audit.orchestrator` | `library/audit/orchestrator.md` | `.muse/workflows/audit/orchestrator.js` | `N, SCOPE, AUDIT_PROMPT_SOURCE, MODE, ALLOW_*, MAX_ISSUES_PER_ITERATION, BASE_BRANCH, REPO, LANGUAGE` |
| `prompt.architecture.cycle` | `library/audit/architecture.md` | `.muse/workflows/audit/cyclic-audit.js` | `CYCLE_KIND=architecture, N=10, SCOPE, MODE, LAYERS, SCORE_SOURCE, ALLOW_*, LANGUAGE` |
| `prompt.observability.dashboard-audit-cycle` | `library/audit/dashboard.md` | `.muse/workflows/audit/cyclic-audit.js` | `CYCLE_KIND=dashboard, N=20, SCOPE, CONTOURS, VIEWPORT, THEME, ALLOW_*, LANGUAGE` |
| `prompt.audit.sequential-run` | `library/audit/sequential-run.md` | `.muse/workflows/audit/cyclic-audit.js` | `CYCLE_KIND=sequential, N, SCOPE, DEPTH, MONITORING, ALLOW_*, MAX_ISSUES_PER_STEP, LANGUAGE` |
| `prompt.observability.sequential-run` | `library/audit/observability-sequential.md` | `.muse/workflows/audit/cyclic-audit.js` | `CYCLE_KIND=observability-sequential, SCOPE, MONITORING, ALLOW_*, MAX_ISSUES_PER_STEP, LANGUAGE` |
