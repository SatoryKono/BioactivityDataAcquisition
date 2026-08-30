---
id: prompt.fragment.evidence-contract-v3
version: 3.0.0
status: active
class: fragment
owner: BioETL Team
summary: Evidence contract v3 — finding schema, fingerprint, status gate, evidence binding
---

## Evidence contract v3

Every finding is `PROVEN` or `NOT_PROVEN`. Only `PROVEN` may create an Issue or allow mutation.

### Finding fields

| Field | Requirement |
|-------|-------------|
| `finding_id` | unique per run, stable within iteration |
| `fingerprint` | `sha256(domain\|requirement_id\|root_cause\|canonical_paths)` — canonical_paths sorted, repo-relative, de-duplicated |
| `status` | `PROVEN \| NOT_PROVEN` |
| `evidence_class` | `FACT \| INFERENCE \| GAP \| CONTRADICTION` |
| `priority` | `P0 \| P1 \| P2 \| P3` |
| `requirement_id` | SSOT ID (`REQ-*`/`DASH-*`) or literal `GAP` when no SSOT covers the invariant |
| `claim` | single falsifiable statement |
| `broken_invariant` | rule/contract violated |
| `root_cause` | minimal causal explanation (not symptom) |
| `affected_paths` | canonical repo-relative paths |
| `evidence` | see Evidence binding below |
| `acceptance` | observable close criteria |
| `validation_commands` | commands that prove acceptance |
| `rollback` | revert plan |
| `owner_surface` | codex/junie/devin/docs owner |

### Fingerprint

```
fingerprint = hex(sha256(domain + "|" + requirement_id + "|" + root_cause + "|" + canonical_paths_joined))
```

- `canonical_paths_joined` = `",".join(sorted(canonical_paths))`.
- Any change to domain, requirement, root cause, or affected path set yields a new fingerprint.
- Used to dedupe findings against open/closed Issues and PRs by root cause.

### Status gate

- `PROVEN` — evidence binding present and sufficient; eligible for `create|reuse`.
- `NOT_PROVEN` — evidence missing, stale, or insufficient; MUST NOT create an Issue and MUST NOT authorize `Implement` mutation. Record as `GAP` or `INFERENCE` and request missing evidence.

### Evidence class

- `FACT` — directly observed in repo/CI (file, command output, check).
- `INFERENCE` — derived from FACTs but not directly observed; needs corroboration to become FACT.
- `GAP` — SSOT or implementation missing; `requirement_id=GAP`.
- `CONTRADICTION` — two FACTs or FACT vs SSOT disagree; blocks `PROVEN` until resolved.

### Requirement binding

- Every `PROVEN` finding MUST bind to an SSOT `requirement_id`.
- Inventing `REQ-*/DASH-*` IDs, metrics, panels, commands, or schemas is forbidden.
- If no SSOT covers the invariant, set `requirement_id=GAP` and keep `status=NOT_PROVEN` unless project explicitly accepts GAP as actionable.

### Evidence binding

Provide **one** of:

1. **Path evidence:** `path + symbol/line range` — e.g., `src/etl/bronze/ingest.py:42-58 :: class BronzeIngest`.
2. **Command evidence:** `command + scope + timestamp + exit_code + relevant output` — e.g., `make lint (SCOPE=src/etl) @ 2026-08-30T12:00:00Z exit:1 :: <trimmed output>`.

Rules:

- Prefer current checkout + `origin/BASE_BRANCH` over memory or stale reports.
- File proof MUST be repo-relative and verifiable without external access.
- Command proof MUST include scope, wall-clock timestamp (UTC), exit code, and the minimal relevant output slice.
- Missing or non-verifiable evidence -> `NOT_PROVEN`.
