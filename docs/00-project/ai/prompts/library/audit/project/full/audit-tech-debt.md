<!-- GENERATED full paste. Source id: prompt.audit.tech-debt. Do not edit by hand. -->
<!-- Regenerate: python -m scripts.ai.prompts render prompt.audit.tech-debt --param N=10 --param MODE=full --param LANGUAGE=ru -->

<!-- prompt-id: prompt.audit.tech-debt version: 1.2.0 -->
<!-- included fragments -->
## Read (do not restate)

1. `AGENTS.md` (precedence, mirrors, env ban, debt budgets)
2. `docs/00-project/NORMATIVE_SOURCES.md`
3. Relevant accepted ADRs only as needed for SCOPE
4. `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` when AI/memory surfaces are in SCOPE

## Git / safety

- Do not edit or delete others' uncommitted work
- No `reset --hard`, no force-push
- Never commit to `main`; use `fix/<slug>` (or worktree if main is dirty)
- Push feature branch only; open PR to `main`
- Prefer evidence-only close when product root cause is already fixed on origin/main

## Tech-debt budgets

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ** tech-debt / quality budgets, exemptions, hotspot
  thresholds, or family caps.
- Debt may only decrease or stay unchanged. Do not silence gates by raising limits.

## Env guardrail

- Do **not** create, edit, rename, move, overwrite, or delete any `.env` /
  `.env.*` file without **explicit per-task user approval**.
- Reading `.env` is permitted. Tokens and secrets must not appear in commits,
  reports, logs, or issue comments.

## Evidence contract

- Every claim needs file-level proof: path, symbol or line range, and
  command/snippet output when applicable.
- Mark `NOT_PROVEN` when evidence is missing; do not invent findings.
- Prefer current checkout + `origin/main` over memory or stale reports.

## Language

- Answer the operator in **Russian** by default when the session is in Russian.
- Keep code, commands, paths, identifiers, and API field names in their valid
  original form.

## Audit scale

### Surface score (higher = better control maturity)

| Score | Quality | Meaning |
| --- | --- | --- |
| 3 | good | Checks reproducible; material risks closed; automation present |
| 2 | acceptable | Core mechanism correct; local non-critical gaps |
| 1 | weak | Material gaps, manual stages, drift, or weak enforcement |
| 0 | unacceptable | Mechanism missing, systemically broken, or direct risk |

Use **one** `surface_score` (0–3) per audited surface/domain in summaries and
closeout. Do **not** put the same 0–3 number on individual findings without
labeling it `control_maturity` and repeating this legend.

### Optional dimension scorecard (0–5)

Some campaign kits rate dimensions (completeness, freshness, …) on **0–5**.
If you use that scorecard, also emit `surface_score` via:

| Dimension avg (0–5) | surface_score |
| --- | ---: |
| ≥ 4.5 | 3 |
| ≥ 3.0 | 2 |
| ≥ 1.5 | 1 |
| &lt; 1.5 | 0 |

Or map a single dimension: `surface_score = min(3, floor(dim * 3 / 5))`.
Always state which mapping you used.

### BI check score_1_5 (1–5, higher = better)

Used by BI dashboard acceptance checks (`fragments/bi-check-schema.md`):

| score_1_5 | surface_score (typical) |
| ---: | ---: |
| 5 | 3 |
| 4 | 3 or 2 |
| 3 | 2 |
| 2 | 1 |
| 1 | 0 |

Kit priorities `high|medium|low` map to P0–P3 per bi-check-schema (not 1:1 with
score). A wrong KPI can be score 1 + priority high even if the layout looks fine.

### Priority (lower number = worse)

| Priority | Meaning | Typical criteria |
| --- | --- | --- |
| P0 | blocking | Compromise, data loss, RCE, secret leak, dangerous deploy, critically wrong instruction |
| P1 | high | High defect/incident probability, release integrity break, critical path uncontrolled |
| P2 | medium | Material maintenance cost, instability, architecture/docs drift |
| P3 | low | Local hygiene, convenience, formatting, low-risk optimization |

### Severity mapping (BioETL closeout / issues)

| Priority | BioETL severity |
| --- | --- |
| P0 | Critical |
| P1 | High |
| P2 | Medium |
| P3 | Low |

In JSON findings, prefer field name **`priority`** for P0–P3. If a kit uses
`"severity": "P0"`, treat it as priority and still set BioETL `severity`.

## Finding schema

Each finding **must** include:

| Field | Rule |
| --- | --- |
| `id` | Stable short id (e.g. `DOCS-012`) |
| `path` | Existing file; prefer `path:line` or line range |
| `observation` | One factual claim |
| `method` | Command, test, or inspection method |
| `expected` | Expected state |
| `actual` | Observed state |
| `impact` | User/runtime/security/ops impact |
| `confidence` | Band `high` \| `medium` \| `low`; optional float `confidence_score` in 0..1 |
| `status` | `PROVEN` \| `NOT_PROVEN` |
| `priority` | `P0` \| `P1` \| `P2` \| `P3` |
| `severity` | Critical / High / Medium / Low (map from priority) |
| `remediation` | Concrete next step |
| `effort` | `S` \| `M` \| `L` \| `XL` when known |
| `automation` | Prevention (CI/hook/test) or `n/a` |
| `automated_fix_possible` | boolean; does **not** authorize applying a fix |

Rules:

- No file-level proof → `NOT_PROVEN` (do not open a GitHub issue).
- Do not invent stack, SLA, coverage targets, or threat models; mark unknown.
- Prefer current checkout + `origin/main` over memory or stale reports.
- Never put secret values in findings, issues, PR bodies, or logs.

## findings.json (machine-readable)

Write UTF-8 JSON array (or `{"findings":[...]}`) under the domain report dir.
Recommended object shape:

```json
{
  "id": "AREA-001",
  "priority": "P1",
  "severity": "High",
  "confidence": "high",
  "confidence_score": 0.9,
  "status": "PROVEN",
  "category": "string",
  "evidence": [
    {
      "path": "path/to/file",
      "line": 42,
      "command": "safe diagnostic command",
      "observation": "what was observed"
    }
  ],
  "expected": "desired or documented state",
  "actual": "observed state",
  "impact": "specific impact",
  "root_cause": "known root cause or unspecified",
  "remediation": "smallest safe remediation",
  "effort": "S",
  "dependencies": [],
  "validation": ["exact command or assertion"],
  "automated_fix_possible": false
}
```

Companion human report: `report.md` (executive summary, surface_score, top gaps).

## Unknown parameters

Before analysis, treat the following as **unknown** unless proven from the
checkout or an explicit operator param:

- tech stack / primary languages
- mono vs polyrepo
- CI platforms beyond what exists under `.github/workflows`
- coverage thresholds
- supported runtime/OS/browser versions
- SLA/SLO, threat model, compliance requirements
- deployment topology
- technical-debt **budget numbers** (limits may exist in quality config —
  read them; never raise them)

**BioETL overlay:** when this repository’s SSOT already defines a fact, use it
instead of leaving «не указано». Examples: Python + pytest; GitHub Actions;
local-only default runtime; debt budgets must not increase
(`fragments/debt-budget-ban.md`); root allowlist
(`.github/root-allowlist.txt`); AI runtime trees `.codex/**`, `.junie/**`,
`.devin/**`.

## Reports output

### Domain audits

- Write under `reports/audit/<domain>/` (create as needed).
- Canonical pair: `report.md` + `findings.json`.
- Examples:
  - `reports/audit/docs-content/`
  - `reports/audit/tests/`
  - `reports/audit/tech-debt/`
  - `reports/audit/repo-tree/`
  - `reports/audit/gha/`
  - `reports/audit/agents/`
  - `reports/audit/diagrams/`
  - `reports/audit/docs-pipeline/`
  - `reports/audit/architecture/` — one-shot or latest mirror of architecture cycle
  - `reports/audit-runs/<run_id>/` — cyclic architecture audit
    (`prompt.architecture.cycle`)
  - `reports/audit/bi-dashboard/` — acceptance: `report.md`, `checks.json`,
    `findings.json` (optional subdirs `visual/`, `layout/`, `data/`)
  - `reports/audit/grafana-panels/` — engineering panel loop outputs when used
  - `reports/audit/dashboard-cycle/<run_id>/` — cyclic dashboard audit
    (`prompt.observability.dashboard-audit-cycle`, render/density/fill + BI)
  - `reports/audit/test-cycle/<run_id>/` — cyclic testing
    (`prompt.tests.cycle`)
  - `reports/audit/project-domain/<run_id>/` — nine-domain project audit rollup
    (workflow `project-domain-audit`)
### Orchestrated multi-iteration runs

- Use `reports/audit-runs/<run_id>/` (not `.audit-runs/` at repo root).
- Suggested layout:
  - `run.json`
  - `iteration-<i>/audit.md`, `findings.json`, `plan.json`, `issues.jsonl`,
    `execution.jsonl`, `summary.md`
  - `final-summary.md`

### Forbidden

- Repo-root `audit/`, `.audit-runs/`, or loose `*-audit.md` / `findings.json`
- Root `_tmp_*.py`, `/_cr_*.py`, Windows device names (`nul` / `NUL`)
- Tracked root files outside `.github/root-allowlist.txt` (RH5/RH6)

Prefer `scripts/**` or `reports/**` for any helper scratch.

## Shell portability

- Primary operator OS for BioETL is **Windows**. Prefer
  `.\.venv-win\Scripts\python.exe` for Python; never Linux `.venv` from Win.
- Example commands may use `bash` + `rg` (Git Bash / CI). Mark GNU-only flags
  (e.g. `xargs -r`) and provide a portable alternative when the check is
  mandatory.
- Do not assume `npm` / `go` / `cargo` until manifests prove that stack.
- Destructive git (`clean` without `-n`, `reset --hard`) is forbidden in audit
  mode unless the operator explicitly approves.

## Generic nine-kit contract

Source kit: 2026-08-11 07:12 BST, nine standalone evidence-based audits.
Not runtime SSOT. Prefer this repository’s SSOT over generic «не указано».

### Do not invent

Stack, languages, repo size, mono/polyrepo, CI beyond `.github/workflows`,
coverage targets, runtime/OS/browser versions, SLA/SLO, threat model,
compliance, deployment topology, or debt **budget numbers**. Discover from
the checkout; if absent, write `не указано` / `GAP`.

**BioETL overlay:** Python + pytest; GitHub Actions; local-only default
runtime; root allowlist; debt budgets must not increase; AI runtime trees
`.codex/**` ≡ `.junie/**` (plus `.devin/**`).

### Finding form

`ID` → `path:line` → observation → method → expected → actual → impact →
confidence → `surface_score` 0–3 (surface) / `control_maturity` if on a
finding → `P0`–`P3` → remediation → automation.

Always pair `report.md` + `findings.json` under `reports/audit/<domain>/`.
Do not write artifacts to repo root.

### Kit vs cyclic pack

| Need | Card |
| --- | --- |
| One-shot domain | `prompt.audit.docs-content` … `prompt.architecture.review` |
| This kit routing | `prompt.audit.generic-nine.pack` |
| N-iteration fix loop | `prompt.audit.orchestrator` / `prompt.audit.cycle.*` |

Domains are independent. Do not dump pipeline findings into content, or
content findings into pipeline. Full generic megaprompt stays archived.

# Technical debt audit

**Kit:** prompt 3 of `prompt.audit.generic-nine.pack`.
Build an evidence-backed debt register: concrete code/config signals → risk →
change cost → paydown order. Separate deliberate tradeoffs, historical
constraints, maintainability debt, obsolete deps, test debt, and architecture
drift. **Never increase** debt/quality budgets (see debt-budget-ban).
Prioritize by probability × blast radius, not TODO count.


**Machine outputs:** always pair `report.md` + `findings.json` under `reports/audit/tech-debt/`. For multi-iteration loops use `prompt.audit.orchestrator` and `reports/audit-runs/<run_id>/`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | path cluster or theme |
| `MODE` | `audit` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `false` |

## Method

1. Collect markers in SCOPE: TODO/FIXME/HACK/XXX/WORKAROUND/TEMP/DEPRECATED,
   lint/type/test suppressions, compatibility shims, disabled checks, dead
   flags, oversized modules, cycles (use project tooling when available).
2. For top items: history/blame age, owner, blast radius, tests protecting
   refactor, whether debt blocks security patch or feature.
3. Classify: code, tests, dependencies, architecture, data/schema, CI,
   observability, documentation, security, operational.
4. Read existing quality/debt budgets and registries; report **trend** without
   proposing higher limits.
5. Optional Sonar/analyzer metrics = signal only, not architecture substitute.

## Surface score (this domain)

| Score | Meaning |
| --- | --- |
| 3 | Debt identified with owner/risk/effort; new code does not worsen baseline |
| 2 | Main debt controlled; some items informal |
| 1 | Suppressions/workarounds without systemic management |
| 0 | Critical accumulated issues ignored or make change unsafe |

## Output

- `reports/audit/tech-debt/report.md` + `findings.json`
- kit extras: `technical-debt-register.csv` (id,path,line,type,evidence,age,risk,blast_radius,effort,owner,priority),
  `debt-heatmap.md`, top-20, quick wins vs strategic vs dependency debt
- `surface_score` 0–3; remediations; `MODE=propose-patches` only with approval

## Priority hints

- P0: security, data integrity, release correctness
- P1: high incident/feature-block probability
- P2: material cost-of-change
- P3: local cleanup

## Stop

Any remediation that **raises** a budget/exemption → reject. Propose only
debt-reducing or budget-neutral changes.

## Applied params

- ALLOW_CLOSE: true
- ALLOW_ISSUE_WRITE: true
- ALLOW_MERGE: false
- ALLOW_PUSH: true
- BASE_BRANCH: main
- DEPTH: full
- INCLUDE_PIPELINE: true
- LANGUAGE: ru
- MODE: full
- MONITORING: false
- N: 10
- REPO: SatoryKono/BioactivityDataAcquisition
- SCOPE: 
- WORK_BRANCH: fix/audit-project-<shortsha>
