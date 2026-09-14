# Agents / runtime audit

*Status: audit-report | domain=`agents-runtime` | prompt=`prompt.audit.agents-runtime`*
*Generated (UTC): 2026-09-14T06:27:53Z*
*MODE=audit AUDIT_MODE=full LANGUAGE=ru REQUIRE_GH_TRACKING=false*

## Surface score

**1 / 3** (domain scale: conflicting instructions + implicit Windows env). Runtime trees `.codex/**` / `.junie/**` are internally consistent; operator kit and Windows command matrix are not.

Not 0: no proven secret-on-stdout, `curl|bash`, or unguarded destructive script. Not 2: RHAI/REGISTRY card-path contradiction is material for the nine-domain kit.

## Instruction scope graph

```
AGENTS.md
  ├─ .codex/agents/CODEX-RUNTIME.md + py-*.md + py-*.toml + .codex/skills/**
  ├─ .junie/agents/JUNIE-RUNTIME.md + guidelines.md + py-*.md + .junie/skills/**  (equal peer; parity contract)
  ├─ .devin/agents/DEVIN-RUNTIME.md + */AGENT.md + .devin/skills/**  (Devin)
  ├─ docs/00-project/ai/**  (mirrors/guides; not behavior SSOT)
  │    ├─ agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md
  │    ├─ grok/  (tracked Grok overlays; install via install_skills.ps1)
  │    └─ prompts/  (operator paste; NOT runtime SSOT)
  ├─ .github/copilot-instructions.md
  └─ scripts/ai/**  (bootstrap/validate/check; RHAI + install_skills.ps1)
```

## What is healthy

- Junie mirror: `.venv-win\Scripts\python.exe scripts\ai\junie\check_junie_mirror.py --check` exit 0. `bash scripts/ai/junie/check_junie_mirror.sh --check` not run (Windows limitation).
- `.junie/agents/CODEX-RUNTIME.md` is an intentional navigation stub, not a drifted Codex map.
- Grok child agents (`docs/00-project/ai/grok/agents/*.md`) forbid MCP `github` / `gh` / `git push`; parent retains GitHub. `install_skills.ps1` matches skills/agents/personas sources and supports `-WhatIf`.
- `.devin/skills/coderabbit-audit` is an allowed Codex–Devin variant (`skills-mirror-contract.json`).
- GitHub MCP wrapper comments and stderr paths do not print token values.
- Prompts library is not treated as runtime SSOT in AGENTS.md or ownership contract.

## Findings (PROVEN)

| id | P | path | observation |
| --- | --- | --- | --- |
| AGT-001 | P1 | `scripts/ai/grok/workflows/nine-domain-audit.rhai:151` | RHAI/generator card_path missing vs REGISTRY.yaml |
| AGT-002 | P2 | `AGENTS.md:98` | Windows: bash-only mirror check; bare `python -m` vs `.venv-win` |
| AGT-003 | P2 | `docs/00-project/ai/prompts/domains.yaml:23` | SSOT path `docs/00-project/ai/AI_RUNTIME_MIRROR_OWNERSHIP.md` missing |
| AGT-004 | P3 | `docs/00-project/ai/grok/README.md:18` | `grok-bootstrap.md` missing; deprecated cycle card listed |
| AGT-005 | P2 | `scripts/ai/grok/install_skills.ps1:35` | installer does not copy tracked `.rhai` workflows |
| AGT-006 | P2 | `scripts/ai/grok/workflows/nine-domain-audit.rhai:263` | `capability_mode: read-only` vs write `report.md` |
| AGT-007 | P3 | `docs/00-project/ai/prompts/library/audit/agents-runtime.md:46` | `prompt.audit.generic-nine.pack` not in REGISTRY |

Proven: 7. P0+P1: 1. Unrelated product WIP on `main` not inspected.

## Top remediations

1. Point RHAI + `generate_project_domain_audit_workflow.py` at live REGISTRY paths (`library/doc/audit.md`, `library/test/system-audit.md`, `library/doc/pipeline.md`, `library/audit/architecture-review.md`) and `prompt.docs.audit`.
2. Add a test: every RHAI `card_path` exists and equals `REGISTRY.yaml`.
3. Document Windows Python mirror check beside the bash line in `AGENTS.md` / POST_CHANGE.
4. Fix `domains.yaml` SSOT path to `agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`.
5. Retarget Grok README; optionally install workflows from `install_skills.ps1` after AGT-001.
6. Narrow RHAI domain-job writes to `reports/audit/**` (parent or reports-only capability).

## Checks

| Check | Result |
| --- | --- |
| `check_junie_mirror.py --check` | pass (exit 0) |
| `check_junie_mirror.sh --check` | skipped (native Windows; no bash invocation) |
| Runtime trees edited | no (audit artifacts only) |
| Destructive agent scripts | not run |

## Out of scope

Product WIP on `main`. Prompts are operator aid, not runtime SSOT — cited only where they contradict REGISTRY or runtime command matrix.
