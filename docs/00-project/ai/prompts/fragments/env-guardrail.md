---
id: prompt.fragment.env-guardrail
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Secret-bearing .env surface guardrail
---

## Env guardrail

- Do **not** create, edit, rename, move, overwrite, or delete any `.env` /
  `.env.*` file without **explicit per-task user approval**.
- Reading `.env` is permitted. Tokens and secrets must not appear in commits,
  reports, logs, or issue comments.
