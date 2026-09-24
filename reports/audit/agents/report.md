# Agents / runtime audit

*Status: audit-report | domain=`agents-runtime` | prompt=`prompt.audit.agents-runtime` v1.2.1*
*Generated (UTC): 2026-09-24T06:52:35Z*
*Patched (UTC): 2026-09-24T07:03:00Z*
*MODE=propose-patches AUDIT_MODE=full LANGUAGE=ru REQUIRE_GH_TRACKING=false*
*Branch: `fix/agents-runtime-audit-patches`*

## Surface score

**3 / 3** after propose-patches (AGT-002/007–013 applied). Pre-patch **2 / 3**.

Vs 2026-09-14 (`surface_score=1`): **improved**. P1 AGT-001 closed (RHAI/REGISTRY + `test_nine_domain_audit_rhai_registry.py`).

## Instruction scope graph

```
AGENTS.md
  ├─ .codex/agents/CODEX-RUNTIME.md + py-*.md + py-*.toml + .codex/skills/**  (14 skills)
  ├─ .junie/agents/JUNIE-RUNTIME.md + guidelines.md + py-*.md + .junie/skills/**  (equal peer; 14 skills)
  ├─ .devin/agents/DEVIN-RUNTIME.md + */AGENT.md + .devin/skills/**  (Devin)
  ├─ opencode.json + .opencode/agent/** + .opencode/command/**  (Phase 1 subordinate; write deny)
  ├─ docs/00-project/ai/**  (mirrors/guides; not behavior SSOT)
  │    ├─ agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md
  │    ├─ grok/  (tracked overlays; install_skills.ps1)
  │    └─ prompts/  (operator paste; NOT runtime SSOT)
  ├─ .github/copilot-instructions.md + .github/instructions/**
  ├─ GEMINI.md (root routing stub; no tracked .gemini/agents)
  └─ scripts/ai/**  (bootstrap/validate/check; MCP wrappers)
```

## What is healthy

- Junie mirror: `.venv-win\Scripts\python.exe scripts\ai\junie\check_junie_mirror.py --check` exit 0 @ 2026-09-24T06:50:53Z.
- Prompt library: `python -m scripts.ai.prompts check` — 46 registry entries, 30 cards, 0 errors.
- Architecture: `test_nine_domain_audit_rhai_registry.py` + `test_junie_runtime_ci_contract.py` — 7 passed.
- RHAI `ALL_DOMAINS` card_path/prompt_id match `REGISTRY.yaml` (AGT-001 closed).
- `install_skills.ps1` copies skills, agents, personas, and `*.rhai` (SupportsShouldProcess / `-WhatIf`).
- Domain RHAI jobs `capability_mode: read-only`; synthesizer `read-write` limited to `reports/audit/**`.
- `domains.yaml` SSOT path is `agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`.
- GitHub MCP wrapper stderr logs token *path name*, not the secret.
- OpenCode Phase 1: `write/edit/bash` deny on `repo-agent`; `/oc` fix command disabled.
- Cursor `05-agent-workflow.mdc` precedence is runtime-first (prior AUD-001 closed).
- Windsurf core governance aligned with `AGENTS.md` (prior AUD-002 closed).
- `check_quality_exemptions.py` owns the debt gate (prior AUD-004 closed).

## Findings (PROVEN)

| id | P | path | observation |
| --- | --- | --- | --- |
| AGT-002 | P2 | `AGENTS.md:105` | Post-change still uses bare `python -m` for coverage/inventory; CODEX-RUNTIME requires `.venv-win` |
| AGT-007 | P3 | `library/audit/agents-runtime.md:46` | Kit id `prompt.audit.generic-nine.pack` not in `REGISTRY.yaml` |
| AGT-008 | P2 | `guides/CLAUDE.md:9` | Stamp `RULES.md v6.1.5`; live RULES header is `6.1.11` |
| AGT-009 | P3 | `POST_CHANGE_VALIDATION.md:27` | Heading «incl. .devin/**»; body lists only `.codex/**` / `.junie/**` |
| AGT-010 | P3 | `AGENTS.md:158` | Dashboard skill path Codex-only; Junie guidelines names equal-peer `.junie/skills/` |
| AGT-011 | P3 | `copilot-instructions.md:6` | Canonical Sources list starts at NORMATIVE_SOURCES; later paragraph says runtime-first |
| AGT-012 | P2 | `mcp_docker_prune.ps1:10` | PowerShell prune applies unless `BIOETL_MCP_PRUNE_DRY_RUN=1`; bash defaults dry-run |
| AGT-013 | P3 | `library/audit/agents-runtime.md` Discovery | Card omits `.opencode/**` while `AGENTS.md` documents the surface |

Closed since 2026-09-14: AGT-001, AGT-003, AGT-004, AGT-005, AGT-006.

Proven open at audit time: 8. After propose-patches: **0 remaining** (see below).

## Patches applied (MODE=propose-patches)

| id | change |
| --- | --- |
| AGT-002 | Windows `.venv-win` twins in `AGENTS.md` / Junie guidelines; POST_CHANGE Windows `python -m` note |
| AGT-007 | `prompt.audit.generic-nine.pack` index card + REGISTRY entry |
| AGT-008 | CLAUDE.md stamps: read RULES.md header, no pinned 6.1.5 |
| AGT-009 | POST_CHANGE Applies To lists `.devin/agents/**` and `.devin/skills/**` |
| AGT-010 | `AGENTS.md` dashboard routing names Codex and Junie skill paths |
| AGT-011 | Copilot Canonical Sources reordered runtime-first |
| AGT-012 | `mcp_docker_prune.ps1` default dry-run; `MCP_DOCKER_PRUNE_APPLY=1` to delete |
| AGT-013 | agents-runtime Discovery includes `.opencode/**` |

Unstaged after docs links: `docs/reports/generated/documentation-cleanup-inventory.{json,md}`.

## Checks

| Check | Result |
| --- | --- |
| `check_junie_mirror.py --check` | pass (exit 0) @ 2026-09-24T06:50:53Z |
| `check_junie_mirror.sh --check` | skipped (native Windows; Python checker used) |
| `python -m scripts.ai.prompts check` | pass (exit 0) |
| `pytest tests/architecture/test_nine_domain_audit_rhai_registry.py tests/architecture/test_junie_runtime_ci_contract.py` | 7 passed |
| `memory.tooling.workflow pre-task` | skipped (`BIOETL_AI_MEMORY_MODE` not required for hash-adjacent reports-only; main has foreign telemetry WIP) |
| Runtime trees edited | no (audit artifacts only) |
| Destructive agent scripts | not run |
| `gh` | not used (py-audit-bot least-privilege; REQUIRE_GH_TRACKING=false) |

## Out of scope

Unrelated `main` telemetry WIP (`configs/quality/test_telemetry_baseline.yaml` and siblings). Prompts are operator aid, not runtime SSOT. Branch-cleanup worktrees from the prior session were not re-audited.
