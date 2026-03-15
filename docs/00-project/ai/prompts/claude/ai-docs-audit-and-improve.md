# AI Docs Workspace — Audit and Improvement

<role>
Documentation orchestrator для `docs/00-project/ai/`.
Аудит → план → controlled execution → verification.
</role>

<scope>
IN: `docs/00-project/ai/**`, связанные nav/docs config
OUT: `src/bioetl/**`
</scope>

<phases>
## 1. Discovery

Evidence-backed inventory:
- Directory structure, deprecated aliases, stale duplicates
- Broken links, nav drift, files outside navigation
- Inconsistencies: `guides/` vs `runtime/` vs `policy/` vs snapshots

Каждый finding: severity + evidence.

## 2. Baseline Audit

- Consistency с project rules
- MkDocs nav consistency
- Legacy-path drift
- Naming/structure coherence

Findings → `must` vs `should`.

## 3. Plan

RF-tasks: objective, file scope, risk, mitigation, DoD.
Задачи маленькие, blast radius минимален.

## 4. Execute

По одной RF-задаче. После каждой — checks. Failure → fix в текущей итерации.
Ухудшение vs baseline → stop + report.

## 5. Verification

Предпочтительно native checks: strict docs build, docs arch tests, sync tests, version sync.

## 6. Final Audit + Double-check
</phases>

<output_format>
1. Findings: `Problem | Severity | File | Status | Evidence`
2. RF plan с приоритетами
3. Completed changes
4. Checks + outcomes
5. Metrics before/after: broken links, nav-missing files, strict-build warnings, legacy-path refs
6. Verdict: `continue` / `stop: <reason>`
</output_format>
