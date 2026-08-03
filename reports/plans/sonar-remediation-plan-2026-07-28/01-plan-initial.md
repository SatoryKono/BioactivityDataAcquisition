# Plan: SonarCloud remediation (live 2026-07-28)

**Дата:** 2026-07-28  
**Проект:** `SatoryKono_BioactivityDataAcquisition` (SonarCloud)  
**Задача:** план исправлений по **текущим** открытым issues (не historical only)  
**Качество gate:** `alert_status=ERROR`  
**Артефакты snapshot:**

| Файл | Назначение |
|------|------------|
| `reports/quality/sonar/live-snapshot-20260728-summary.json` | totals, facets, blockers/bugs |
| `reports/quality/sonar/live-issues-20260728-manifest.json` | 725 compact issue keys (ledger) |
| `reports/plans/sonar-issues-remediation-plan-2026-07-27/01-plan-initial.md` | prior plan (750 @ 2026-07-27) |

**Источник baseline:** публичный SonarCloud API  
`GET /api/issues/search?componentKeys=SatoryKono_BioactivityDataAcquisition&resolved=false`  
(повторён 2026-07-28; 725 unique keys).

---

## 1. Live baseline (сейчас)

### 1.1 Measures

| Metric | Value |
|--------|------:|
| Unresolved issues | **725** |
| Bugs | **9** |
| Vulnerabilities | **113** |
| Code smells | **603** |
| Security hotspots | 0 |
| Blocker | **5** |
| Critical | 380 |
| Major | 263 |
| Minor | 77 |
| Remediation effort (sum) | **~8578 min (~143 h)** |
| ncloc | ~853 821 |
| duplicated_lines_density | 1.0% |
| Quality gate | **ERROR** |
| reliability / security rating | 5.0 / 5.0 |
| maintainability (sqale) rating | 1.0 |

### 1.2 Сравнение с прошлыми snapshot

| Дата | Unresolved | Vuln | Bugs | Smells | Blocker | Effort |
|------|----------:|-----:|-----:|-------:|--------:|-------:|
| 2026-07-23 live snapshot | 1257 | 572 | 8 | 677 | 12 | ~6823 min (sqale_index) |
| 2026-07-27 plan baseline | 750 | 123 | 9 | 618 | 10 | ~10455 min |
| **2026-07-28 live (этот план)** | **725** | **113** | **9** | **603** | **5** | **~8578 min** |

**Вывод:** прогресс есть (≈−25 issues vs 07-27, −532 vs 07-23), но gate всё ещё ERROR.  
План 07-27 (RF-001…010) остаётся валидной структурой; **этот документ — rebaseline** под актуальные 725 и новые/сдвинувшиеся blockers.

### 1.3 По анализаторам

| Analyzer | Count |
|----------|------:|
| python (maintainability) | 505 |
| pythonsecurity | 70 |
| powershelldre | 65 |
| shelldre | 33 |
| javascript | 15 |
| docker | 13 |
| shell | 12 |
| githubactions | 7 |
| pythonbugs | 5 |

### 1.4 По path-buckets (top)

| Bucket | Count |
|--------|------:|
| `scripts/engineering/qa` | 242 |
| `scripts/ops/runtime` | 84 |
| `scripts/ops/observability` | 62 |
| `src/bioetl/infrastructure` | 35 |
| `src/bioetl/application` | 29 |
| `scripts/ai/mcp` | 29 |
| `src/memory` | 26 |
| `scripts/docs/checks` | 22 |
| `scripts/engineering/repo` | 19 |
| `src/bioetl/domain` | 19 |
| `src/bioetl/**` (all layers) | ~104 |
| `scripts/**` (dominant) | majority of total |

**Ключевой вывод по scope:** >70% debt — tooling/scripts (qa/ops), не production domain.  
Приоритизация: **security/bugs → src/bioetl correctness → scripts hotspots**.

### 1.5 Top rules (сейчас)

| Rule | Count | Family / fix strategy |
|------|------:|------------------------|
| `python:S3776` | 177 | cognitive complexity → extract pure helpers |
| `python:S1192` | 161 | duplicated string literals → local semantic constants |
| `pythonsecurity:S8707` | 41 | path taint → resolve + `relative_to(allowed_root)` / allowlist |
| `powershelldre:S8677` | 31 | unapproved verbs → rename to approved PowerShell verbs |
| `python:S7503` | 20 | unused async / missing await → drop async or real await |
| `python:S5886` | 19 | return type contract vs implementation |
| `python:S3358` | 19 | nested ternary → if/else blocks |
| `powershelldre:S8657` | 17 | empty catch → contextual error handling |
| `pythonsecurity:S8701` | 16 | OS command taint → argv list + validation, no shell |
| `shelldre:S7677` | 14 | errors to stderr |
| `python:S5332` | 11 | clear-text protocols (http) |
| `python:S6353` | 11 | regex simplification |
| `powershelldre:S3776` | 9 | PS cognitive complexity |
| `python:S1172` | 9 | unused parameters |
| `python:S8786` | 8 | regex backtracking |

### 1.6 Blockers (5) — start here

| Rule | Path | Line | Message (short) |
|------|------|-----:|-----------------|
| `pythonsecurity:S2076` | `scripts/ai/mcp/protocol_smoke.py` | 369 | OS command from user-controlled data |
| `pythonsecurity:S2083` | `scripts/ai/sync_cursor_rules.py` | 39 | path from user-controlled data |
| `pythonsecurity:S2083` | `scripts/ops/observability/grafana/render_nav_bus.py` | 223 | path from user-controlled data |
| `python:S5708` | `src/bioetl/infrastructure/storage/gold/io_delta_runtime.py` | 191 | exception type not BaseException-derived |
| `python:S3516` | `src/bioetl/interfaces/cli/commands/_workflow_run_support.py` | 173 | method always returns same value |

> Note: 07-27 blockers partially closed (setup_mcp, link_warnings, publish_tdx, etc.).  
> **Новые/оставшиеся** — protocol_smoke, sync_cursor_rules, render_nav_bus, io_delta_runtime, _workflow_run_support.

### 1.7 Bugs (9)

| Rule | Path | Notes |
|------|------|-------|
| `powershelldre:S8637` | `scripts/ops/runtime/mcp/start-shared.ps1:32` | reserved `WhatIf` param name |
| `python:S1045` | `scripts/ops/observability/grafana/rerender_grafana_screenshots.py:1130` | duplicate except |
| `python:S1244` ×2 | `scripts/ops/observability/grafana/audit_live_grafana_panels.py:904,914` | float `==` |
| `python:S5708` | `io_delta_runtime.py:191` | same as blocker |
| `pythonbugs:S2583` ×2 | `scripts/engineering/qa/report_debt_governance_gates.py:552,592` | always false |
| `pythonbugs:S2583` ×2 | `src/bioetl/infrastructure/config/contract_registry_loader.py:85,88` | always false/true |

### 1.8 Top vuln files

| Count | Path |
|------:|------|
| 9 | `scripts/ai/mcp/protocol_smoke.py` |
| 7 | `docs/05-operations/Dockerfile` |
| 6 | `scripts/engineering/qa/report_debt_governance_gates.py` |
| 5 | `scripts/engineering/qa/report_architecture_debt_remote_main_baseline.py` |
| 4 | `report_duplication_baseline.py`, `report_adr_enforcement_matrix.py`, `.github/workflows/release.yml` |

### 1.9 Top complexity files (S3776 family)

| Count | Path |
|------:|------|
| 11 | `scripts/engineering/qa/run_observability_closure_campaign.py` |
| 7 | `scripts/ops/observability/grafana/audit_live_grafana_panels.py` |
| 6 | `check_scripts_inventory.py`, `rerender_grafana_screenshots.cjs`, `report_dashboard_inventory.py` |
| 5 | `documentation_cleanup_inventory.py`, `report_compatibility_importer_census.py` |

### 1.10 Top S1192 (duplicated literals) files

| Count | Path |
|------:|------|
| 15 | `scripts/engineering/qa/check_dashboard_visual_semantics.py` |
| 12 | `report_debt_governance_gates.py`, `documentation_cleanup_inventory.py` |
| 9 | `generate_semantic_pipeline_audit.py` |
| 8 | `check_semantic_anchor_parity.py` |

---

## 2. Constraints (non-negotiable)

1. **Не увеличивать** tech-debt budgets / thresholds / exemptions / `sonar.*exclusions`.
2. **Не** закрывать как false-positive / won't-fix без воспроизводимого доказательства + explicit review.
3. **Не** трогать `.env` / `.env.*` без явного per-task approval.
4. Security: фиксировать **trust boundary** (validate/allowlist), не маскировать sink.
5. `src/bioetl/**`: import matrix + после волн — `module-coverage-inventory.json` hash refresh.
6. Behavior-changing fixes → regression tests.
7. Grafana Docker stack **не** поднимать без явного dashboard/render task (ADR-010).
8. Tracking: issue **key** + rule + path (не только line — lines drift).

---

## 3. Waves (executable DAG)

### W0 — Ledger & rebaseline (½ day)

- **Цель:** зафиксировать 725 keys как working ledger.
- **Артефакты (уже созданы):**  
  - `reports/quality/sonar/live-issues-20260728-manifest.json`  
  - `reports/quality/sonar/live-snapshot-20260728-summary.json`
- **DoD:**
  - [x] 725 unique keys
  - [ ] optional: architecture test “manifest paths exist / rule totals match API”
  - [ ] GH epic + children issues (optional, if tracking on GH)

### W1 — Blockers (P0, 1–2 days)

Close **5 BLOCKER** first; partial security co-located in same files.

| # | File | Work |
|---|------|------|
| B1 | `scripts/ai/mcp/protocol_smoke.py` | command construction: argv-only, validate args/paths; close S2076 + cluster vulns (9 in file) |
| B2 | `scripts/ai/sync_cursor_rules.py` | path normalize + root allowlist (`relative_to`) for S2083 |
| B3 | `scripts/ops/observability/grafana/render_nav_bus.py` | path allowlist for S2083; keep nav-bus contract |
| B4 | `src/bioetl/infrastructure/storage/gold/io_delta_runtime.py` | fix exception type expression (S5708) — correctness |
| B5 | `src/bioetl/interfaces/cli/commands/_workflow_run_support.py` | remove constant-return method (S3516) or make branch-real |

**Tests:** path-traversal / command-injection negative cases; gold delta exception path; CLI workflow unit tests.  
**DoD:** Sonar blockers = 0.

### W2 — Bugs (P0, 1 day, parallel with late W1)

| File | Fix |
|------|-----|
| `start-shared.ps1` | rename reserved `WhatIf` → domain param (e.g. `DryRun`) + callers |
| `rerender_grafana_screenshots.py` | merge/reorder except clauses (S1045) |
| `audit_live_grafana_panels.py` | float compare via tolerance/`math.isclose` (S1244) |
| `report_debt_governance_gates.py` | fix dead conditions S2583 (or delete dead branches after characterization) |
| `contract_registry_loader.py` | fix always-true/false conditions — **high value (src)** |

**DoD:** Sonar bugs = 0.

### W3 — Security burn-down (P0/P1, 3–5 days)

**113 vulnerabilities** after W1 remainder.

| Priority cluster | Rules (approx) | Strategy |
|------------------|----------------|----------|
| Path taint | `S8707` (41), residual `S2083` | shared small helper only if contract identical: `safe_resolve(root, user_path)` |
| Command taint | `S8701` (16), residual `S2076` | argv lists, `--` end-of-options, no `shell=True` |
| URL/redirect | `S8705` (6) + related | scheme/host allowlist |
| Clear-text | `python:S5332` / `shell:S5332` | https or documented loopback-only with safe code shape (not suppress) |
| Docker / installs | `docker:S8541`, shell install rules | digest-pinned images; lockfile/digest installs |
| GHA | residual githubactions (~7) | least-privilege, no unverified artifact exec |
| Ops Dockerfiles | `docs/05-operations/Dockerfile` (7 vulns) | pin base digests, drop risky patterns |

**Do not** invent a mega “security utils” package that violates layering.  
Prefer local validation at each CLI/entrypoint.

**DoD:** vulnerabilities = 0; security workflows green.

### W4 — Cognitive complexity (P1, 5–8 days)

**~192** issues: `python:S3776` (177) + PS/JS variants.

**File clusters (order):**

1. `run_observability_closure_campaign.py` (11)
2. Grafana tooling: `audit_live_grafana_panels.py`, `rerender_grafana_screenshots.cjs`, dashboard audits
3. QA inventory/reports: `check_scripts_inventory`, `report_dashboard_inventory`, `documentation_cleanup_inventory`, compatibility census
4. `scripts/ops/runtime/docker/runtime_manager.py`, cleanup_repository
5. Remaining scripts then `src/bioetl` residual complexity

**Method per hotspot:**

1. Characterization / golden for CLI output  
2. Extract pure functions / typed result objects  
3. Keep deterministic ordering and public schemas  
4. Ruff + targeted pytest  

**DoD:** S3776 family = 0; complexity budgets not increased.

### W5 — Duplicated literals & identical impl (P1, 3–4 days)

- `python:S1192` (161) — top: visual semantics, debt gates, docs cleanup inventory  
- Rare `S4144` / identical branches  

**Rules:** constants next to semantic owner; no global dumping ground; no god-utils.

**DoD:** S1192 family = 0.

### W6 — Remaining Python smells (P2, 3–5 days)

Includes: `S7503` async, `S5886` returns, `S3358` nested ternary, `S6353`/`S8786` regex, `S1172` unused params, `S107` too many params (parameter objects only if domain-stable), etc.

Batch by **rule family**, commit by **file owner cluster**.

**DoD:** open python maintainability/security/bugs for project = 0 (after W3–W5).

### W7 — PowerShell + Shell (P2, 2–3 days)

- Approved verbs (`S8677`)  
- Non-empty catch (`S8657`)  
- stderr (`S7677`), `[[ ]]`, default `case`, safe installs  
- Windows CI / `pwsh` parse gates required before merge  

**DoD:** powershelldre + shelldre + shell = 0.

### W8 — JS / GHA / Docker residual (P2, 1–2 days)

- JS optional chaining / existence / complexity leftovers  
- GHA permissions / artifact verification  
- Docker sort RUN / pin digests  

**DoD:** javascript + githubactions + docker analyzers = 0.

### W9 — Closeout & re-scan (P0 gate, 1 day)

1. Re-query Sonar API → `total=0` (or only reviewed accepted exceptions with ledger).  
2. Any **new** issues from refactors → add to ledger and fix same wave.  
3. `module-coverage-inventory` hash if `src/bioetl` touched.  
4. Architecture / debt scorecard gates; budgets non-increasing.  
5. Quality gate status = OK on server analysis of tip commit.  

**DoD:**  
- [ ] `resolved=false` total = 0  
- [ ] Quality gate green  
- [ ] Debt outcome per wave: improved or unchanged  
- [ ] No secret / allowlist / budget regressions  

---

## 4. DAG

```text
W0 ledger
  │
  ▼
W1 blockers ──► W2 bugs
  │                │
  └────► W3 security ◄──┘
           │
           ├─► W7 shell/PS
           ├─► W8 JS/GHA/Docker
           ▼
         W4 complexity
           ▼
         W5 duplicated strings
           ▼
         W6 remaining Python
           │
           ▼
         W9 closeout re-scan
```

**Практический порядок:**  
`W0 → W1 → W2 → W3 → W4 → W5 → (W6 ‖ W7 ‖ W8) → W9`

Параллель: W7/W8 после W3; W6 после W5.

---

## 5. Suggested PR / commit slicing

| PR | Scope | Risk |
|----|--------|------|
| PR-A | W1 blockers + tests | high |
| PR-B | W2 bugs (src + scripts) | high |
| PR-C… | W3 security by trust-boundary cluster (mcp / qa / docker / gha) | high |
| PR-D… | W4 complexity per file cluster | medium |
| PR-E… | W5 S1192 by file | medium |
| PR-F | W6 leftovers | medium |
| PR-G | W7 PS/shell | medium |
| PR-H | W8 JS/GHA/Docker | medium |
| PR-I | W9 ledger + inventory + docs closeout | low |

Prefer **≤1–3 hot files per PR** for security; complexity PRs can be one cluster.

---

## 6. Validation gates

### Per PR / cluster

```bash
uv run ruff check <changed>
uv run ruff format --check <changed>
# targeted tests for changed surface
uv run pytest <targeted> -q --timeout=120
```

### Surface-specific

```bash
bash -n <shells>
pwsh -NoProfile -Command "& { $null = [System.Management.Automation.Language.Parser]::ParseFile(...) }"
node --check <js>
# docker: hadolint / build smoke if Dockerfile touched
```

### After src/bioetl changes

```bash
python _refresh_module_coverage_inventory.py   # or project-canonical equivalent
uv run pytest tests/architecture/test_module_coverage_inventory.py -q
# architecture hash guard when feasible
```

### Final

```bash
# full quality gate (project canonical)
uv run python -m scripts.engineering.ci quality-gate
# Sonar server analysis on tip + API:
# GET .../issues/search?resolved=false → total=0
```

**Важно:** local green ≠ closed until **SonarCloud** shows total 0 on the published analysis of that commit.

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| 725 issues → mega-diff | wave/PR slicing + key ledger |
| Security helper changes behavior | characterization + malicious inputs first |
| Complexity extract breaks CLI schemas | golden/contract tests + deterministic sort |
| PowerShell not verified in Linux CI | mandatory Windows job before merge |
| Line drift | track by issue key |
| New issues from refactors | W9 full re-query; fix in same program |
| Temptation to raise exclusions/budgets | **forbidden** |
| Dirty worktree / concurrent waves | isolate worktree per PR |

---

## 8. Effort estimate (rough)

| Wave | Hours (eng) | Notes |
|------|------------:|-------|
| W0 | 2–4 | mostly done |
| W1 | 8–16 | security + 2 src |
| W2 | 4–8 | 9 bugs |
| W3 | 24–40 | 100+ vulns, many scripts |
| W4 | 40–64 | 177 complexity |
| W5 | 16–24 | 161 literals |
| W6 | 16–24 | long tail |
| W7 | 12–20 | PS/shell + Windows |
| W8 | 6–12 | thin residual |
| W9 | 4–8 | re-scan/governance |
| **Total** | **~130–220 h** | aligns with ~143 h Sonar effort ± overhead |

---

## 9. Definition of Done (program)

- [ ] All 725 baseline keys closed by fix **or** explicitly reviewed exception with evidence
- [ ] Vuln / Bug / Smell open counts = 0 on SonarCloud
- [ ] New issues introduced by waves also closed
- [ ] Quality gate **OK**
- [ ] No debt budget / exclusion growth
- [ ] `src/bioetl` inventory hash current if touched
- [ ] Closeout comment on tracking epic with before/after measures table

---

## 10. Immediate next actions (recommended)

1. **Publish GH epic** “SonarCloud remediation 2026-07-28 (725)” with children W1–W9 (optional but useful).  
2. **Start W1 PR-A:** five blockers + tests; re-run Sonar or wait for next analysis.  
3. **W2** same day if capacity: `contract_registry_loader` + debt gates dead conditions.  
4. Keep `live-issues-20260728-manifest.json` as closeout checklist (check off keys as PRs merge).

---

## 11. Out of scope / non-goals

- Raising Sonar exclusions to greenwash metrics  
- Mass `NOSONAR` without per-case review  
- Full Grafana live stack for pure code smells  
- Merging unrelated DOC-GOV / RH / architecture dirty worktree into Sonar PRs  

---

*Generated from live SonarCloud API 2026-07-28; supersedes numeric baseline of 2026-07-27 plan while preserving RF wave structure.*

---

## Progress log

| Date | Wave | Commit / PR | Notes |
|------|------|-------------|-------|
| 2026-07-28 | W1–W2 | `b823068c93` / #6936 | Blockers + bugs closed in code |
| 2026-07-28 | W3 | `df522d62c9` / #6936 | Path/command taint bulk + Docker/GHA pins |
| — | W4–W9 | pending | Complexity, literals, PS/shell, re-scan |

