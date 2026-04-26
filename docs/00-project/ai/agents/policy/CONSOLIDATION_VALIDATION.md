# Consolidation Validation

*Статус: internal-published (Internal / Extended)*

Date: 2026-03-08
Scope: `docs/00-project/ai/agents/agents/sp-*.md`

## Commands

```bash
# Baseline policy checks (recommended default)
python3 docs/00-project/ai/agents/policy/check_agent_consolidation.py

# Full template enforcement
python3 docs/00-project/ai/agents/policy/check_agent_consolidation.py --strict
```

## What It Checks

1. Frontmatter exists for each profile.
1. `filename == frontmatter.name`.
1. No banned suffixes (`-pro`, `-master`, `-expert`).
1. Alias profiles contain both markers: `Canonical profile: [...]` and `Planned removal date: YYYY-MM-DD.`.
1. In `--strict` mode only, canonical specialist profiles contain both sections: `Boundary note` and `Operating modes`.

## Exit Code

1. `0`: all checks passed.
1. `1`: one or more policy violations found.
1. `2`: checker failed to run (e.g., missing target directory).
