# Consolidation Validation

Date: 2026-03-08
Scope: `docs/00-project/ai/**`

## Commands

```bash
# Baseline policy checks (recommended default)
python3 docs/00-project/ai/agents/policy/check_agent_consolidation.py

# Full template enforcement
python3 docs/00-project/ai/agents/policy/check_agent_consolidation.py --strict
```

## What It Checks

1. Frontmatter exists for each profile.
2. `filename == frontmatter.name`.
3. No banned suffixes (`-pro`, `-master`, `-expert`).
4. Alias profiles contain both markers: `Canonical profile: [...]` and `Planned removal date: YYYY-MM-DD.`.
5. In `--strict` mode only, canonical specialist profiles contain both sections: `Boundary note` and `Operating modes`.

## Exit Code

1. `0`: all checks passed.
2. `1`: one or more policy violations found.
3. `2`: checker failed to run (e.g., missing target directory).
