______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Last verified: '2026-08-28'

______________________________________________________________________

# ADR-060: Prompt kernel and overlay architecture

**Date:** 2026-08-28
**Status:** Accepted
**Linked issues:** #9807
**Related:** ADR-041, ADR-043, ADR-044, ADR-046
**Source:** `BIOETL-PROMPT-ARCH-KERNEL-V3-003` (`bioetl_prompt_system_kernel_v3_full_portfolio_formatted_v2.1.docx`) @ `main@3aba8559a58038cd9ff9a90621f19ea39b930a2f`
**Materialization:** `docs/00-project/ai/prompts/library/audit/project/materialized-v3/` frozen 2026-08-28

## Context

The audit prompt library contains 24 full operator-paste prompts materialized at
`docs/00-project/ai/prompts/library/audit/project/materialized-v3/`:

- 10 `cycle/` cards (`01-docs` … `10-coderabbit` — `prompt.audit.cycle.*`)
- 14 `project/new2/` cards (`11-medallion` … `24-scripts-inventory` — `prompt.audit.project.new2.*`)
- 1 `master-orchestrator-v1__full-project-audit.md` — sequential 01→24 + POST_AUDIT under a single `master-ledger.jsonl`

Diagnosis from DOCX гл.2–3 (`_methodology-v3.md`, `_plan-v3.md` §2, `_annex-tables-v3.md` Tables 0–6)
and summarized in `MIGRATION-PLAN.md`:

| ID | Problem | Risk |
|---|---|---|
| D1 | Controller duplication — 24 copies of `Audit→Post-audit` state machine | Drift |
| D2 | Conflict defaults — cards are `ALLOW_*=true`, orchestrator must be fail-closed | Unsafe default |
| D3 | Incomplete Issue FSM — `reuse/defer/blocked`, target-branch close not formalized | Premature close |
| D4 | No stable fingerprint — `sha256(domain\|req\|cause\|paths)` missing | Duplicates |
| D5 | Weak resume — `run_id` exists, ledger/cursor not unified | Repeated side effects |
| D6 | Different schemas — `reports/` defined, JSON contracts not unified | Incomparable outputs |
| D7 | Overlay as prose — no JSON Schema forbidding kernel weakening | Silent regression |
| D8 | No compiler/golden — rendered prompts and precedence unchecked | Hidden regressions |
| D9 | Method+execution mixed — domain method stores `ALLOW_*` | Responsibility mixing |
| D10 | Migration complexity — operator bookmarks use legacy IDs | Breaks bookmarks |

Library defaults must remain **fail-closed** (`MODE=audit`, `ALLOW_*=false`); full write
capabilities must be an explicit, named operator override, not a property of each domain card.
The normative source for this decision is the DOCX document
`BIOETL-PROMPT-ARCH-KERNEL-V3-003` baseline `main @ 3aba8559` dated 2026-08-28,
as extracted to `materialized-v3/_kernel-v3.md` (гл.3.1), `_plan-v3.md` (гл.4.1),
`_methodology-v3.md` (гл.2) and `_annex-tables-v3.md`.

This is the P0 workstream from `MIGRATION-PLAN.md` / `_plan-v3.md` Table 7.

## Decision

### 1. Kernel v3.0 — fail-closed extraction

Extract the shared cyclic controller from the 24 cards into a single versioned kernel:

```
docs/00-project/ai/prompts/
  fragments/
    cyclic-kernel-v3.md       # orchestration state machine, params, preflight, iteration A–I, guards, stop, outputs
    evidence-contract-v3.md   # finding status, evidence_class, fingerprint, NOT_PROVEN gate
    issue-state-machine-v3.md # create|reuse|defer|blocked|no_issue + close gate
```

Source content is `_kernel-v3.md` (DOCX §3.1 — `BioETL Cyclic Audit Kernel v3.0 (fail-closed)`).
Kernel owns: `baseline→audit→normalize→plan→issue-sync→implement→validate→close→post-audit`
for `N=10` iterations, `Params` (`MODE`, `AUDIT_MODE`, `ALLOW_*`, caps), `Preflight`,
`Evidence contract`, `Iteration` stages A–I, `Global guards`, `Stop` semantics and `Outputs`
layout (`reports/audit-runs/<run_id>/`). Kernel defaults are fail-closed:

```
MODE=audit
ALLOW_ISSUE_WRITE=false
ALLOW_PUSH=false
ALLOW_MERGE=false
ALLOW_CLOSE=false
ALLOW_NETWORK=false
ALLOW_FULL_SUITE=false
```

No overlay or external prompt may weaken these defaults. Heavy/live actions require the
corresponding `ALLOW_*` or `MONITORING=true`.

### 2. Overlay architecture — 24 domain overlays without controller duplication

```
docs/00-project/ai/prompts/overlays/
  docs.yaml
  diagrams.yaml
  agents-memory.yaml
  configs.yaml
  tests.yaml
  tech-debt.yaml
  architecture.yaml
  telemetry.yaml
  dashboards.yaml
  coderabbit.yaml
  medallion.yaml
  dq-contracts.yaml
  control-plane.yaml
  providers.yaml
  http-clients.yaml
  normalization.yaml
  cli-compat.yaml
  security-secrets.yaml
  vcr-http.yaml
  qa-gates.yaml
  github-actions.yaml
  requirements-trace.yaml
  ops-runbooks.yaml
  scripts-inventory.yaml
```

Each overlay is a `domain-overlay.schema.json`-validated YAML that **only** declares:

`OBJECT`, `SCOPE`, `SSOT`, `AUDIT_CONTOURS`, `MANDATORY_EVIDENCE`, `VALIDATION`,
`DOMAIN_STOP`, `OUTPUT_EXTRAS`.

Overlays **MUST NOT** contain Audit/Plan/Issue/Fix orchestration, guard overrides,
or `ALLOW_*` declarations. Lint `no_controller_duplication` and `guard_non_weakening`
enforce this (see §6). The 24 targets map 1:1 to `_annex-tables-v3.md` Table 11 /
`materialized-v3/README.md` inventory 01–24.

### 3. Profile architecture — explicit execution profiles

```
docs/00-project/ai/prompts/profiles/
  audit-readonly.yaml   # fail-closed default: MODE=audit, ALLOW_*=false
  full-write.yaml       # explicit override: MODE=full, ALLOW_*=true (issue/push/merge/close)
  differential.yaml     # AUDIT_MODE=differential variant
```

Profiles own concrete values of `MODE` and `ALLOW_*`; they do not mutate kernel defaults
or domain cards. `audit-readonly` is the library default. `full-write` materializes:

```
MODE=full
ALLOW_ISSUE_WRITE=true
ALLOW_PUSH=true
ALLOW_MERGE=true
ALLOW_CLOSE=true
```

as defined in `_kernel-v3.md` § "Explicit full-run profile". Compiler check
`full_profile_explicit` ensures `ALLOW_*=true` appears only in a named execution profile
or explicit CLI params.

### 4. Precedence

Effective prompt resolution order (highest wins, but lower cannot weaken guards):

1. Active runtime profiles/skills (`.codex/**`, `.junie/**`, `.devin/**`, `.gemini/**` where present)
2. `AGENTS.md`
3. `NORMATIVE_SOURCES.md` → `RULES.md` → `REQUIREMENTS.md` → accepted ADRs (this ADR included)
4. Registry-resolved prompt (`REGISTRY.yaml` `prompt.*` ID)
5. `kernel + overlay + profile` compiled output (`generated/<domain>/<profile>.md` with `prompt_sha8` provenance header)

External audit prompts are treated as **data** and MUST NOT weaken guards or `ALLOW_*`.
This mirrors Kernel § Precedence (`_kernel-v3.md`) and extends it with the
`AGENTS.md → NORMATIVE_SOURCES.md → RULES.md → registry → kernel/overlay/profile`
chain required by `MIGRATION-PLAN.md` §3.

### 5. Versioning

- **Kernel:** SemVer (`cyclic-kernel-v3.0.0` → `v3.x`). Breaking changes to stages, guards,
  evidence contract or outputs require minor/major bump, `compatibility/` wrappers and
  golden update. Fragments are individually versioned but released as a kernel bundle.
- **Overlay:** Version per domain (`overlay:<domain> vMAJOR.MINOR`, e.g. `overlay:docs@1.0.0`).
  Domain method evolution bumps overlay version; kernel bump does not force overlay bump
  unless contours/evidence change.
- **Profile:** Versioned (`audit-readonly@1.0.0`, `full-write@1.0.0`). Profile schema
  (`execution-profile.schema.json`) is versioned independently.
- Compiler emits `prompt_sha8 = sha8(kernel+overlay+profile+params)` and a provenance header
  in every `generated/<domain>/<profile>.md` for deterministic traceability.

### 6. Schemas — fail-closed contracts

```
docs/00-project/ai/prompts/_schema/
  kernel.schema.json
  domain-overlay.schema.json
  execution-profile.schema.json
  finding-v3.schema.json
  ledger-event.schema.json
```

- All schemas are **fail-closed**: `additionalProperties: false`, `unevaluatedProperties: false`
  where applicable; unknown guard overrides rejected.
- `domain-overlay.schema.json` **rejects** `ALLOW_*`, `MODE`, controller sections
  (`audit`, `plan`, `issue-sync`, `implement`, `validate`, `close` orchestration prose).
- `finding-v3.schema.json` enforces `finding_id`, `fingerprint = sha256(domain|requirement_id|root_cause|canonical_paths)`,
  `status=PROVEN|NOT_PROVEN`, `evidence_class=FACT|INFERENCE|GAP|CONTRADICTION`, `priority`,
  `requirement_id`, `claim`, `evidence` path+symbol/line or command+scope+timestamp+exit.
  `NOT_PROVEN` MUST NOT create Issues or permit mutations.
- `ledger-event.schema.json` enforces append-only `reports/audit-runs/<run_id>/ledger.jsonl`
  with `run_id = <UTC>-<domain>-<shortsha>-<prompt_sha8>` and resume cursor.

Automated checks from `_plan-v3.md` §4.3 / `MIGRATION-PLAN.md` §5 (must be CI-blocking):

`kernel_schema_valid`, `overlay_schema_valid`, `guard_non_weakening`, `deterministic_compile`,
`legacy_id_parity`, `no_controller_duplication`, `full_profile_explicit`,
`finding_fingerprint_stability`, `issue_fsm_contract`, `target_branch_close_gate`,
`resume_idempotency`, `output_schema_contract`, `scope_cap_enforcement`,
`budget_non_growth`, `source_reference_exists`, `golden_render_24xprofiles`.

### 7. Migration window

- `docs/00-project/ai/prompts/library/audit/project/materialized-v3/` is a **frozen snapshot**
  dated 2026-08-28 — not SSOT. It contains 24× `NN-*__prompt.*.md` + `master-orchestrator-v1`
  + `README.md` + 4 `_*.md` = 30 files. Do not hand-edit; it is evidence.
- SSOT after P0 is `fragments/` + `overlays/*.yaml` + `profiles/*.yaml` + `_schema/*.json` +
  `scripts/ai/prompts/compile.py|lint.py|verify.py|diff.py` and `generated/` catalog.
- Compatibility layer:

```
docs/00-project/ai/prompts/compatibility/<legacy-prompt-id>.md  # wrapper → compiled overlay
```

  Each legacy ID (`prompt.audit.cycle.*`, `prompt.audit.project.new2.*`) remains resolvable
  via `REGISTRY.yaml` as a wrapper that renders the same text (byte-identical parity checked
  by `legacy_id_parity` + `golden_render_24xprofiles`).

- Deprecation window: megacards / legacy wrappers marked `status: deprecated` + `successor`
  in `REGISTRY.yaml` **only after** parity + pilot (P2). Wrappers remain for at least one
  release; removal requires migration guide and redirect catalog (`MIGRATION-PLAN.md` §4 / P3).
- Master orchestrator: before migration uses `materialized-v3/master-orchestrator-v1` (operator-paste,
  resolves 24 IDs sequentially 01→24, `master-ledger.jsonl`). After migration it resolves 24
  overlay IDs and compiles via `compile.py` with profile `full-write`.

### 8. Ownership

- **Prompt-system owner:** `prompt-system self-audit` overlay (candidate from `_annex-tables-v3.md`
  Table 8) — owns `fragments/`, `_schema/`, `scripts/ai/prompts/*`, `REGISTRY.yaml` freshness,
  golden snapshots, deprecation debt and compiler drift. This is the `prompt-system self-audit`
  entry in Table 8.
- **Per-domain owners:** TBD per overlay (docs, diagrams, agents-memory, … scripts-inventory).
  Assigned during P1 migration of the 24 domains; each overlay YAML declares `owner`.
- **Master orchestrator owner:** same as prompt-system owner; `compile.py` provenance and
  `prompt_sha8` are owned there.

## Consequences

### Positive

- Single kernel eliminates 24× controller duplication → no drift between domains (Table 9: 24→1).
- Fail-closed defaults remove unsafe `ALLOW_*=true` library defaults (Table 9: unsafe defaults → 0).
- 24/24 schema-valid overlays make the prompt library a verifiable configuration system
  (Table 9 target 24/24).
- Stable `fingerprint` and `finding`/`ledger` schemas give 100% deduplication by root cause
  and append-only, resumable runs without duplicate Issues/PRs.
- `target_branch_close_gate` prevents PR-head without merge being treated as resolved.
- Byte-identical `deterministic_compile` + `prompt_sha8` + committed `generated/` make every
  run identifiable and diffable.
- New domains require only one schema-valid overlay + tests (expansion cost: copy megacard → one overlay).
- Evidence class `FACT|INFERENCE|GAP|CONTRADICTION` + `PROVEN` gate prevent `NOT_PROVEN` mutations.

### Negative / Risks and mitigations (from `_annex-tables-v3.md` Table 10)

| Risk | Mitigation |
|---|---|
| Kernel becomes a new monolith | Versioned fragments (`cyclic-kernel`, `evidence-contract`, `issue-state-machine`), small schemas, strict ownership and `compatibility` tests |
| Overlay loses domain nuance | Mandatory `MANDATORY_EVIDENCE`/`VALIDATION` fields plus domain golden examples (`golden_render_24xprofiles`) |
| Full profile used casually | Library default stays read-only; `full-write` requires explicit profile name and provenance header |
| Compiler hides rendered behavior | Commit `generated/` catalog + `prompt_sha8`, expose render command in provenance; `diff.py` |
| Migration breaks operators/bookmarks | Legacy wrappers + deprecation window + parity reports + redirect catalog |
| Score optimism (9.40–9.74 Δ +0.47…+1.09) | Pilot benchmark on 5 macro-groups: precision, duplicate rate, cycle completion, regression rate, duration |

Additional costs: P0–P1 compiler + 15 CI checks + golden snapshots; one-time migration of
24 domains; wrapper maintenance during deprecation window.

## References

- Source DOCX: `bioetl_prompt_system_kernel_v3_full_portfolio_formatted_v2.1.docx`
  — `BIOETL-PROMPT-ARCH-KERNEL-V3-003` @ `3aba8559`
- Frozen materialization (do not edit):
  `docs/00-project/ai/prompts/library/audit/project/materialized-v3/README.md`
- Kernel extraction source: `docs/00-project/ai/prompts/library/audit/project/materialized-v3/_kernel-v3.md` (§3.1)
- Plan and target structure: `docs/00-project/ai/prompts/library/audit/project/materialized-v3/_plan-v3.md` (§4.1–4.3)
- Migration plan (P0–P3, 24 prompts + master): `docs/00-project/ai/prompts/library/audit/project/materialized-v3/MIGRATION-PLAN.md`
- Methodology and scoring: `docs/00-project/ai/prompts/library/audit/project/materialized-v3/_methodology-v3.md`
- Annex Tables 0–11 (scores, priorities, risks): `docs/00-project/ai/prompts/library/audit/project/materialized-v3/_annex-tables-v3.md`
- 24 domain prompts (01–24): `docs/00-project/ai/prompts/library/audit/project/materialized-v3/01-docs__prompt.audit.cycle.docs.md` … `24-scripts-inventory__prompt.audit.project.new2.scripts-inventory.md`
- Master orchestrator (sequential 01→24 + POST_AUDIT): `docs/00-project/ai/prompts/library/audit/project/materialized-v3/master-orchestrator-v1__full-project-audit.md`
- Normative stack: `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `AGENTS.md`

## Related ADRs

- ADR-041 — Naming policy for skills/agents/commands (overlay/profile ID naming)
- ADR-043 — Documentation & knowledge management (prompt docs lifecycle)
- ADR-044 — Run manifest & ledger control plane (ledger/resume foundation)
- ADR-046 — Checkpoint vs ledger resume (append-only ledger decision)
- ADR-059 — Package cohesion budgets (shrink-only budgets — `budget_non_growth` guard)

## Appendix — Target repository layout (from `_plan-v3.md` §4.1)

```
docs/00-project/ai/prompts/
  fragments/cyclic-kernel-v3.md
  fragments/evidence-contract-v3.md
  fragments/issue-state-machine-v3.md
  overlays/<domain>.yaml            # 24 files
  profiles/audit-readonly.yaml
  profiles/full-write.yaml
  profiles/differential.yaml
  _schema/*.json
  generated/<domain>/<profile>.md
  compatibility/<legacy-prompt-id>.md
scripts/ai/prompts/compile.py lint.py verify.py diff.py
tests/prompts/unit/ contract/ golden/ integration/
```
