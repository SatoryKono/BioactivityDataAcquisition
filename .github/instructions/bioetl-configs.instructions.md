---
applyTo: "configs/**"
---

# BioETL Configs (Copilot)

Canonical sources:

- `docs/00-project/RULES.md` (config/schema governance)
- `configs/README.md`
- Pandera / contract YAMLs under `configs/contracts/**`
- `AGENTS.md` env/secret guardrails

## MUST

- Keep secret-valued fields as placeholders / `${ENV_VAR}` / secret-manager refs only.
- Preserve deterministic ordering and schema-compatible evolution.
- Align entity/pipeline/DQ YAML with existing field registry patterns.

## MUST NOT

- Commit real tokens, passwords, or private URLs.
- Silently break CLI/API/schema contracts without versioning + migration notes.
- Increase quality/debt budgets in `configs/quality/**` without explicit burn-down.
