---
id: prompt.fragment.generic-nine-contract
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Shared contract for the nine-domain generic audit kit (2026-08-11)
---

## Generic nine-kit contract

Source kit: 2026-08-11 07:12 BST, nine standalone evidence-based audits.
Not runtime SSOT. Prefer this repository’s SSOT over generic «не указано».

### Do not invent

Stack, languages, repo size, mono/polyrepo, CI beyond `.github/workflows`,
coverage targets, runtime/OS/browser versions, SLA/SLO, threat model,
compliance, deployment topology, or debt **budget numbers**. Discover from
the checkout; if absent, write `не указано` / `GAP`.

**BioETL overlay:** Python + pytest; GitHub Actions; local-only default
runtime; root allowlist; debt budgets must not increase; AI runtime trees
`.codex/**` ≡ `.junie/**` (plus `.devin/**`).

### Finding form

`ID` → `path:line` → observation → method → expected → actual → impact →
confidence → `surface_score` 0–3 (surface) / `control_maturity` if on a
finding → `P0`–`P3` → remediation → automation.

Always pair `report.md` + `findings.json` under `reports/audit/<domain>/`.
Do not write artifacts to repo root.

### Kit vs cyclic pack

| Need | Card |
| --- | --- |
| One-shot domain | `prompt.audit.docs-content` … `prompt.architecture.review` |
| This kit routing | `prompt.audit.generic-nine.pack` |
| N-iteration fix loop | `prompt.audit.orchestrator` / `prompt.audit.cycle.*` |

Domains are independent. Do not dump pipeline findings into content, or
content findings into pipeline. Full generic megaprompt stays archived.
