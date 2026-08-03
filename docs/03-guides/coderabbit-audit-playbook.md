______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# CodeRabbit Audit Playbook

Repeatable strategy for auditing BioETL with CodeRabbit: continuous PR review
plus scoped CLI deep audits. Complements architecture tests, import-linter,
scorecard/debt gates, and basedpyright — CodeRabbit is **not** the sole SSOT.

## Precedence

1. Code / domain contracts / config  
2. Accepted ADRs + RULES  
3. Architecture tests and quality gates  
4. CodeRabbit findings (must map to evidence above)

On conflict: **code wins**. Do not raise tech-debt budgets to silence findings.

## Two modes

| Mode | Trigger | Tooling | Purpose |
| --- | --- | --- | --- |
| **PR App** | every PR | CodeRabbit GitHub App + `.coderabbit.yaml` | Diff review (assertive) |
| **CLI scoped** | epic / re-audit / release | CodeRabbit CLI (~0.7.x) | Residual risks beyond one PR |

CI workflow: `.github/workflows/coderabbit.yml`  
- Trusted: `push` to `main` / `workflow_dispatch`  
- Skips CLI if `CODERABBIT_API_KEY` missing (App-only fallback)  
- Never runs untrusted `pull_request` with the secret

Config: [`.coderabbit.yaml`](../../.coderabbit.yaml) (`profile: assertive`).

---

## Hard constraints

1. **~300 file cap** per CLI review — always split scopes; count files first.  
2. **Windows host** — prefer **WSL** or Linux runner for CLI; App works on GitHub.  
3. **Rate limits** — sequential scopes; backoff between runs.  
4. **Worktree** — use a clean worktree if GitHub Desktop / other git thrash holds `index.lock`.  
5. **Artifacts** — write under `reports/grok/` or `reports/quality/coderabbit/` (gitignore allowlist); not bulk `docs/reports/evidence`.  
6. **Secrets** — never commit API keys or edit `.env*` without explicit approval.

---

## File-count preflight

```bash
# files in a scope (tracked)
git ls-files 'src/bioetl/domain' | wc -l
git ls-files 'src/bioetl/application' | wc -l
git ls-files 'src/bioetl/infrastructure' | wc -l
git ls-files 'src/bioetl/composition' | wc -l
git ls-files 'grafana' 'docs/03-guides/dashboards' | wc -l
```

If a scope approaches 300, split further (e.g. `application/core` vs
`application/services/control_plane`).

---

## CLI install and auth

```bash
# Linux/WSL — follow current CodeRabbit install docs; CI mirrors:
# https://cli.coderabbit.ai/install.sh (verify content before bash; see workflow)

coderabbit --version
coderabbit auth login --api-key "$CODERABBIT_API_KEY"
```

Local: export key from a secret store; do not put it in tracked files.

---

## Prompt contract (every scoped run)

Paste or adapt:

```text
You are reviewing BioETL (hexagonal + DDD + medallion + local-only ADR-010).

Rules:
- Domain must stay I/O-free; DI only in composition.
- Prefer evidence: path + symbol + broken invariant.
- Do not propose increasing quality/debt budgets.
- Do not treat Docker/monitoring as required default.
- DQ hard_fail is multi-default (hierarchical 0.50 vs Silver-request 0.20).
- Ignore pure style nits unless they hide correctness risk.
- Skip themes already closed in ARCH-CR / DOC-GOV unless you prove regression.

Output for each finding:
1) severity (critical|major|minor|trivial)
2) path
3) claim (one sentence)
4) why it matters (invariant)
5) suggested fix class (code|test|config|docs)
6) acceptance check (command or test name if possible)
```

---

## Standard scope matrix (architecture residual)

| Scope id | Paths | Focus |
| --- | --- | --- |
| `domain` | `src/bioetl/domain/**` | pure domain, ports, aggregates |
| `app-core` | `src/bioetl/application/core/**` | batch/lifecycle hotspots |
| `app-cp` | `src/bioetl/application/services/control_plane/**` | manifest/ledger/replay |
| `infra` | `src/bioetl/infrastructure/**` | async I/O, adapters, HTTP |
| `composition` | `src/bioetl/composition/**` | DI-only, factories |
| `interfaces` | `src/bioetl/interfaces/**` | thin CLI/HTTP |
| `tests-arch` | `tests/architecture/**` | gate honesty |
| `cfg-quality` | `configs/quality/**` | budgets, no growth |
| `docs-norm` | `docs/00-project/**`, `docs/02-architecture/decisions/**` | SSOT drift only |

### Example CLI invocations

CLI compares commits/branches; for monorepo path focus use a **sparse worktree**
or review after staging only the scope (preferred: separate worktree per scope
checkout of the same SHA).

```bash
export AUDIT_TS=$(date -u +%Y%m%d_%H%M)
export OUT=reports/grok
mkdir -p "$OUT"

# Diff-oriented (trusted CI style): base main
coderabbit review --base=main --plain \
  | tee "$OUT/review_coderabbit_${SCOPE}_${AUDIT_TS}.log"

# Against explicit commit (re-audit delta)
coderabbit review --base-commit=<sha-before-wave> --plain \
  | tee "$OUT/review_coderabbit_${SCOPE}_${AUDIT_TS}.log"
```

Historical split logs: `reports/grok/review_coderabbit_arch_*_20260728_*.jsonl`.

---

## Pipeline (one CLI campaign)

```text
0 Freeze baseline SHA + scorecard + open epics
1 Plan scopes (file counts < 300)
2 Run CR per scope → log/jsonl under reports/
3 Normalize findings table (id, sev, path, claim, epic, dupe-of)
4 Triage: P0 now | P1 issue | P2 backlog | reject
5 Write issue pack under .github/ISSUES/
6 Publish GH issues (optional) + implement
7 Re-run CR only on fixed scopes
8 Closeout note + tag audit/coderabbit-YYYYMMDD
```

### Severity → action

| Severity | Action |
| --- | --- |
| critical / security / layer break | same-day P0 issue |
| major correctness | P1 issue with acceptance |
| missing tests | P1–P2; attach hotspot family |
| minor | fix in flight or drop |
| trivial / style | drop |

### Finding template (markdown)

```markdown
### CR-{SCOPE}-{NN}
- Severity:
- Path:
- Claim:
- Evidence (code/test/ADR):
- Epic link: (e.g. #6925)
- Dupe of: (prior issue or none)
- Acceptance:
- Status: open|reject|done
```

---

## Active epic checklists (2026-07-28 open set)

### A. Project Diagnostics / types — epic #6925

CodeRabbit **supports** explanation and risk; **basedpyright is ground truth**.

| Issue | Role | CR scope hint |
| --- | --- | --- |
| #6926 | Snapshot + regen recipe | none first — produce baseline JSON |
| #6927 | Protocol parameter renames | `domain/ports/**`, NoOp, prometheus, pubmed |
| #6928 | config_dq / bootstrap_logger / runner_merge returns | composition + config_dq + runner |
| #6929 | Uninit attrs — entity + batch_writer | `application` entity/batch_writer mixins |
| #6930 | Uninit attrs — observer + runner | observer/runner mixins |
| #6931 | Attr access + arg types CP/adapters | `control_plane/**`, adapters |
| #6932 | Invalid cast residual | files from basedpyright `reportInvalidCast` |
| #6933 | Import cycles | cycle report + composition/domain edges |
| #6934 | Incompatible overrides | override diagnostics set |
| #6935 | Warning budget IDE vs CI mypy | policy doc + CI config only |

**Order:**

```text
#6926 baseline → CR on hot paths (optional) → #6927–#6932 fixes
→ #6933–#6934 → #6935 policy → re-snapshot → close #6925
```

**Commands (types ground truth — adjust to repo entrypoints):**

```bash
# Prefer project-documented basedpyright / mypy wrappers when present
# Example shapes — replace with make/uv targets used in CI:
basedpyright src/bioetl -p pyrightconfig.json  # if configured
# or
python -m basedpyright src/bioetl

# After a fix wave, regenerate snapshot artifact into reports/quality/
# (path defined by #6926 acceptance)
```

**CR add-on for types wave:**

```bash
# After snapshot: review only packages with highest error density
# Split: domain | application | infrastructure | composition
coderabbit review --base=main --plain | tee reports/grok/review_coderabbit_types_${AUDIT_TS}.log
```

Triage rule: if basedpyright is silent and CR complains about types only →
usually **reject** or convert to test/docs; if both fire → **fix**.

---

### B. Optional Grafana Scenes — epic #6915 (DSS-00)

Monitoring is **optional** (ADR-010). Do not require Docker monitoring for
core Local-Only runtime.

| Issue | Role | CR scope hint |
| --- | --- | --- |
| #6915 | Meta / ADR-gated shell | architecture boundary docs + ADR-053 |
| #6916 | Scaffold package + 6 routes | new Scenes app package only |
| #6917 | Shared components | Context / Verdict / Action rail |
| #6918 | JSON ↔ Scenes parity tests | tests + dashboard JSON contracts |
| #6919 | UID aliases / dual-path docs | provisioning docs + UIDs |
| #6920 | Live render evidence 7 UIDs | host render skill; evidence only |
| #6921 | JSON residual Trust Safety Gate | `grafana/dashboards` targeted panels |
| #6922 | JSON residual DQ Now funnel | same |
| #6923 | Domain viz P3 | tracking only until contract |
| #6924 | ADR-gated cutover metrics | process/ADR, not runtime default |

**Order:**

```text
#6915 boundary → #6916 scaffold → #6917 components → #6918 parity tests
→ #6919 docs/UIDs → #6920 evidence (host) → #6921–#6922 JSON residuals
→ #6923–#6924 only if still needed
```

**Commands:**

```bash
# Count dashboard surface
git ls-files 'grafana/dashboards' | wc -l

# CR scoped to observability UX (keep under 300 files)
git ls-files 'grafana' 'docs/03-guides/dashboards' 'docs/03-guides/grafana-dashboard-configuration.md'

coderabbit review --base=main --plain \
  | tee reports/grok/review_coderabbit_dss_${AUDIT_TS}.log

# Render evidence when host ready (do not start monitoring stack unless asked)
# Use skill: .codex/skills/grafana-dashboard-render/
```

**CR must flag:** dual SSOT (JSON vs Scenes), Local-Only regression, secret
leakage in provision, missing parity tests for shared panels.

---

## Cadence

| When | What |
| --- | --- |
| Every PR | GitHub App only |
| Weekly while epic open | 1–2 CLI scopes on active epic |
| After large merge train | Full architecture split (matrix above) |
| Release / scorecard dip | Split CLI + debt gates + arch tests |

---

## Issue pack + closeout

1. Write `.github/ISSUES/<EPIC>-CODERABBIT-<DATE>-ISSUE-PACK.md`.  
2. Optional publish JSON under `reports/quality/`.  
3. Implement; keep commits selective (no drive-by).  
4. Re-run CR on **same scopes**.  
5. Close GH issues with SHA + evidence paths.  
6. Tag: `audit/coderabbit-YYYYMMDD`.

### Closeout checklist

- [ ] FINAL.md: tool version, SHA, scopes, severity counts  
- [ ] De-dupe vs prior ARCH-CR / DOC-GOV / epic issues  
- [ ] No quality budget growth  
- [ ] Relevant gates green (arch / debt / types / docs)  
- [ ] Secrets not committed  

---

## Related history

- Architecture CR FINAL: `reports/grok/review_coderabbit_architecture_audit_20260728_1203_FINAL.md`  
- Issue pack: `.github/ISSUES/ARCH-CR-2026-07-28-ISSUE-PACK.md`  
- Re-audit pack: `.github/ISSUES/CODERABBIT-REAUDIT-2026-07-27-ISSUE-PACK.md`  
- Workflow: `.github/workflows/coderabbit.yml`  
- Dashboard skills: `.codex/skills/grafana-dashboard-render/`, `grafana-dashboard-extension/`  
- Docs verification: [docs-verification.md](docs-verification.md)  
- CI map: [../05-operations/ci-workflow-map.md](../05-operations/ci-workflow-map.md)  

---

## Anti-patterns

- One CLI run on entire monorepo (hits file cap / noisy).  
- Opening issues for every trivial nit.  
- Treating CR as proof of runtime behavior without tests.  
- Auditing types without basedpyright snapshot.  
- Forcing Grafana/Scenes as required for Local-Only product path.  
- Re-opening closed architecture epics without regression evidence.
