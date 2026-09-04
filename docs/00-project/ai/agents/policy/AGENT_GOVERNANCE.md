______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-04'

______________________________________________________________________

# Agent Governance — Consolidated (Naming, Consolidation, Validation, Templates)

*Статус: active | Single source for agent policy after Wave 7. Replaces 4 docs-only files: `AGENT_CONSOLIDATION_MATRIX_2026-03-08.md`, `AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md`, `CONSOLIDATION_VALIDATION.md`, `SPECIALIST_PROFILE_TEMPLATE.md` (now archived to `docs/99-archive/` — see deprecation notice below).*

> **Canonical runtime SSOT:** `.codex/agents/` (6 `py-*` + `ORCHESTRATION.md` + `CODEX-RUNTIME.md`) and equal peer `.junie/agents/` (parity via `scripts/ai/junie/check_junie_mirror.sh`). This doc is governance mirror, not runtime SSOT. See `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`.

## 1. Naming Policy (from AGENT_NAMING_POLICY 2026-03-08)

### 1.1 Namespaces

- `py-*` — reserved for BioETL core orchestration. Pattern `py-{role}-{type}` where `type=bot|swarm|orchestrator`.
- `sp-*` — generic specialist catalog (docs-only, now 0 active after Wave 7). Pattern `sp-{domain}-{role}`.

### 1.2 Global Rules

1. Lowercase kebab-case only.
1. `filename == frontmatter.name`.
1. Banned suffixes: `-pro`, `-master`, `-expert`.
1. Guide docs (`AGENT.md`, `CLAUDE.md`, `CODEX.md`, `GEMINI.md`, `README.md`) outside naming policy.

### 1.3 Rename Matrix (P1/P2, docs-only scope)

| From | To | Status |
| --- | --- | --- |
| `postgres-pro` | `sp-postgres-engineer` | done (alias) |
| `electron-pro` | `sp-electron-engineer` | done |
| `wordpress-master` | `sp-wordpress-engineer` | done |
| `qa-expert` | `sp-qa-engineer` | done |
| `m365-admin` | `sp-microsoft-365-admin` | done |
| `architecture-techdebt-automation` | `py-audit-bot` (canonical) | done — `py-audit-bot` is architecture-debt SSOT, old file is generator-only compat |
| `ml-engineer` / `machine-learning-engineer` | `sp-ai-engineer` | alias retired 2026-06-30 |
| `mobile-app-developer` | `sp-mobile-developer` | alias retired |
| `agent-organizer` / `multi-agent-coordinator` / `task-distributor` | `sp-workflow-orchestrator` | alias retired |

## 2. Consolidation Matrix (Waves 1-7)

### Canonicalization Rules

1. `py-*` remain dedicated BioETL runtime orchestrators.
1. `sp-*` are generic catalog; if two `sp-*` overlap >70% keep one canonical.
1. Deprecated profile must contain `Canonical profile: [...]` and `Planned removal date: YYYY-MM-DD.`

### Waves 1-5 (summary)

- **W1:** 8 deprecated -> canonical alias routing (`sp-agent-organizer` etc -> `sp-workflow-orchestrator`, `sp-ml-engineer` -> `sp-ai-engineer` etc), expanded 3 canonical profiles.
- **W2:** `sp-business-analyst` -> `sp-project-manager`, hardened boundaries (`sp-code-reviewer` secondary to `py-audit-bot`).
- **W3:** escalation contract `sp-debugger` <-> `sp-error-coordinator`, added `Planned removal 2026-06-30`.
- **W4:** added canonical/alias templates, checker `check_agent_consolidation.py`, split `default`/`--strict`.
- **W5:** normalized `Boundary note` + `Operating modes`, `--strict` PASS.

### Wave 6 (2026-03-12)

| Area | Change | Status |
| --- | --- | --- |
| Full consolidation | Deleted 77 generic agents | done |
| Mirror sync | Deleted 77 `sp-*` mirrors | done |
| Alias retirement | All aliases removed | done |
| Retained | 12 `sp-*` kept | done |

### Wave 7 (2026-09-04) — Minimal Sufficient Set

| Area | Change | Status |
| --- | --- | --- |
| Docs-only specialists | Archived 12 `sp-*` from `docs/00-project/ai/agents/agents/` to `docs/99-archive/agents-sp-2026-09/` | done |
| Checker evidence | `findings=12 missing frontmatter` + `rg subagent_type 0 hits` | done |
| Mirror sync | `agents/README.md` archived notice | done |
| Governance | Minimal set 6 `py-*` confirmed per `AGENTS.md` | done |

**Final Inventory After Wave 7:** `py-* 6 + sp-* 0 (12 archived) + service 2 = 8` in `docs/00-project/ai/agents/agents/`.

## 3. Validation

### Commands

```bash
python docs/00-project/ai/agents/policy/check_agent_consolidation.py
python docs/00-project/ai/agents/policy/check_agent_consolidation.py --strict
```

### What It Checks

1. Frontmatter exists.
1. `filename == frontmatter.name`.
1. No banned suffixes.
1. Alias has `Canonical profile` + `Planned removal date`.
1. `--strict` only: canonical `sp-*` has `Boundary note` + `Operating modes`.

Exit 0 PASS, 1 violations, 2 missing dir. After Wave 7: `checked_files=0, findings=0`.

## 4. Specialist Profile Templates

### Canonical

```md
---
name: sp-<domain>-<role>
description: "One-sentence trigger."
tools: Read, Write, Edit, Glob, Grep
model: sonnet
---

You are a senior <role> ...

Boundary note (YYYY-MM-DD):
- owns ...
- must not own ...
- canonical for adjacent ...

Operating modes:
- mode-1
- mode-2

When invoked: ...
<Role> checklist: ...
Integration: ...
```

### Deprecated Alias

```md
---
name: sp-<alias>
description: "Deprecated alias. Use sp-<canonical>."
---

Canonical profile: `sp-<canonical>.md`

Planned removal date: YYYY-MM-DD.
```

## 5. Deprecation Notice

The 4 source files are superseded by this doc and will be archived to `docs/99-archive/agents-policy-2026-09/` in next commit:

- `AGENT_CONSOLIDATION_MATRIX_2026-03-08.md`
- `AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md`
- `CONSOLIDATION_VALIDATION.md`
- `SPECIALIST_PROFILE_TEMPLATE.md`

Update links: `AGENT_GOVERNANCE.md` is the single entry point. See `AI_RUNTIME_MIRROR_OWNERSHIP.md` for runtime vs mirror ownership.

## 6. Env File Guardrail

- Любой `.env` файл считается secret-bearing. MUST NOT create/edit without explicit approval.

## Related

- `AGENTS.md`, `docs/00-project/NORMATIVE_SOURCES.md`, `.codex/agents/ORCHESTRATION.md`, `scripts/ai/junie/check_junie_mirror.sh`
