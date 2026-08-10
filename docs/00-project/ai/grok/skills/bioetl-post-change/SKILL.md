---
name: bioetl-post-change
description: Run BioETL post-change validation after edits — mirrors, inventory hashes, focused tests. Use after write-capable work, before PR/closeout, or /bioetl-post-change.
---

# BioETL post-change validation

Policy SSOT: `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`.
This skill is a checklist, not a second policy.

## When to use

- After any write-capable task on BioETL
- Before opening a PR or closing issues
- After edits under runtime trees or `src/bioetl/**`

## Checklist

1. **Re-scan** impacted code/config/docs/runtime surfaces (search + related tests).
2. **Runtime source first** — change `.codex/**` / `.junie/**` / `.devin/**` before docs mirrors.
3. **Mirror parity** — if `.codex/agents/**`, `.codex/skills/**`, `.junie/agents/**`, or `.junie/skills/**` changed:

   ```bash
   bash scripts/ai/junie/check_junie_mirror.sh --check
   ```

4. **Module coverage inventory** — if `src/bioetl/**/*.py` changed:

   ```powershell
   .\.venv-win\Scripts\python.exe _refresh_module_coverage_inventory.py
   ```

   (or the current canonical refresh entry from POST_CHANGE_VALIDATION)

5. **Focused tests** for the touched surface (prefer project pytest wrappers).
6. **Prompt library** — if `docs/00-project/ai/prompts/**` changed:

   ```powershell
   .\.venv-win\Scripts\python.exe -m scripts.ai.prompts check
   .\.venv-win\Scripts\python.exe -m scripts.ai.prompts catalog
   ```

7. **Report** explicitly: checks run, checks skipped, mirror-sync status.

## Guardrails

- Do not increase tech-debt budgets / exemptions / thresholds
- Do not create or edit `.env` without approval
- Do not treat memory or vendor diagnostics as sole proof for lifecycle advance
