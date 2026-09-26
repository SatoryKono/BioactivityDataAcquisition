# Prompt Library CLI

Operator tooling for `docs/00-project/ai/prompts/` (epic #8513).

```bash
python -m scripts.ai.prompts list
python -m scripts.ai.prompts show prompt.audit.grok-cycle
python -m scripts.ai.prompts render prompt.audit.grok-cycle --param SCOPE="src/bioetl/domain"
python -m scripts.ai.prompts check-registry
python -m scripts.ai.prompts check --write-artifact
python -m scripts.ai.prompts catalog
python -m scripts.ai.prompts new --id prompt.example.demo --class operator-paste
```

Also: `python -m scripts.ai prompts ...` (unified AI surface router).

Windows: `.\.venv-win\Scripts\python.exe -m scripts.ai.prompts ...`

## Checks

| Command | Purpose |
| --- | --- |
| `check-registry` | paths exist, ids unique, status/class enums, include paths |
| `check` | registry + paste hygiene (size, guardrail includes, related_ssot, RULES-dump patterns) |

Optional artifact: `reports/quality/prompts/check.json`.

## Ownership

- Does **not** live under `src/bioetl/`
- Does **not** change runtime agent/skill behavior
- Library cards link to SSOT; they are not governance sources
