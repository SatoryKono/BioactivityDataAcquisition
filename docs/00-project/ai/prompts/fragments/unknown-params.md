---
id: prompt.fragment.unknown-params
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Do not invent repo parameters; prefer known BioETL SSOT
---

## Unknown parameters

Before analysis, treat the following as **unknown** unless proven from the
checkout or an explicit operator param:

- tech stack / primary languages
- mono vs polyrepo
- CI platforms beyond what exists under `.github/workflows`
- coverage thresholds
- supported runtime/OS/browser versions
- SLA/SLO, threat model, compliance requirements
- deployment topology
- technical-debt **budget numbers** (limits may exist in quality config —
  read them; never raise them)

**BioETL overlay:** when this repository’s SSOT already defines a fact, use it
instead of leaving «не указано». Examples: Python + pytest; GitHub Actions;
local-only default runtime; debt budgets must not increase
(`fragments/debt-budget-ban.md`); root allowlist
(`.github/root-allowlist.txt`); AI runtime trees `.codex/**`, `.junie/**`,
`.devin/**`.
