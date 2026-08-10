---
id: prompt.fragment.evidence-contract
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Minimum evidence format for findings and closeout
---

## Evidence contract

- Every claim needs file-level proof: path, symbol or line range, and
  command/snippet output when applicable.
- Mark `NOT_PROVEN` when evidence is missing; do not invent findings.
- Prefer current checkout + `origin/main` over memory or stale reports.
