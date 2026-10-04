---
id: prompt.fragment.evidence-contract-v3
version: 3.1.0
status: active
class: fragment
owner: BioETL Team
summary: Evidence contract v3.1 — freshness, disproof, root-cause identity, finding status gate
---

## Evidence contract v3.1

Every finding is `PROVEN` or `NOT_PROVEN`. Only `PROVEN` may create an
Issue or authorize mutation. A reviewer may later assign a separate
`review_verdict` (`CONFIRMED | DOWNGRADED | REJECTED | NOT_VERIFIABLE`);
that verdict does not replace the finding `status` field.

### Finding fields

| Field | Requirement |
|-------|-------------|
| `finding_id` | unique per run, stable within iteration |
| `root_cause_id` | stable cross-prompt id for one causal defect; shared by symptoms |
| `fingerprint` | finding-specific SHA-256 over domain, requirement, root cause and canonical paths |
| `status` | `PROVEN \| NOT_PROVEN` |
| `review_verdict` | optional independent-review verdict; never used as the primary status gate |
| `evidence_class` | `FACT \| INFERENCE \| GAP \| CONTRADICTION` |
| `evidence_freshness` | `CURRENT \| STALE \| UNBOUND` |
| `priority` | `P0 \| P1 \| P2 \| P3` |
| `requirement_id` | SSOT ID (`REQ-*`/`DASH-*`) or literal `GAP` |
| `claim` | single falsifiable statement |
| `broken_invariant` | rule/contract violated |
| `root_cause` | minimal causal explanation, not symptom |
| `affected_paths` | canonical repo-relative paths |
| `evidence` | see Evidence binding below |
| `attempted_disproof` | what was checked to falsify the claim and result |
| `exception_ref` | sanctioned exception/waiver path or `null` |
| `acceptance` | observable close criteria |
| `validation_commands` | commands that prove acceptance |
| `rollback` | revert plan |
| `owner_surface` | codex/junie/devin/docs/component owner |

### Root-cause identity

`root_cause_id` is the cross-prompt dedupe key. Prefer an existing stable
project/root-cause id. Otherwise compute a deterministic short id from:

```
sha256(requirement_id + "|" + normalized_root_cause + "|" + primary_owner_surface)
```

Rules:

- Symptoms in multiple audit domains share one `root_cause_id` when they arise
  from the same causal defect.
- Do not split one defect merely because it was discovered by different cards.
- Do not merge distinct causes merely because they touch the same file.

### Finding fingerprint

```
fingerprint = hex(sha256(domain + "|" + requirement_id + "|" + root_cause + "|" + canonical_paths_joined))
```

- `canonical_paths_joined` = `",".join(sorted(canonical_paths))`.
- Any change to domain, requirement, root cause, or affected path set yields a
  new finding fingerprint.
- Use `root_cause_id` for cross-domain clustering and `fingerprint` for the
  concrete finding instance.

### Evidence freshness

- `CURRENT` — bound to the audited revision/worktree or to a runtime artifact
  whose provenance explicitly points to that revision.
- `STALE` — valid historical evidence whose producer/source revision differs
  from the audited revision or cannot prove current state.
- `UNBOUND` — revision/provenance is absent or cannot be resolved.

A `PROVEN` finding requires sufficient `CURRENT` evidence. `STALE` or
`UNBOUND` material may guide investigation but cannot independently prove a
current defect.

### Status gate

- `PROVEN` — current evidence binding is sufficient, disproof was attempted,
  and no valid exception neutralizes the claim; eligible for `create|reuse`.
- `NOT_PROVEN` — evidence missing/stale/unbound/insufficient, disproof failed
  to establish the claim, or an unresolved contradiction remains. MUST NOT
  create an Issue and MUST NOT authorize `Implement` mutation.

### Evidence class

- `FACT` — directly observed in repo/CI/runtime artifact.
- `INFERENCE` — derived from FACTs but not directly observed; needs
  corroboration to become FACT.
- `GAP` — SSOT or implementation missing; `requirement_id=GAP`.
- `CONTRADICTION` — FACTs or FACT vs SSOT disagree; blocks `PROVEN` until
  resolved.

### Requirement binding

- Every `PROVEN` finding MUST bind to an existing SSOT `requirement_id`.
- Inventing `REQ-*/DASH-*` IDs, metrics, panels, commands, or schemas is
  forbidden.
- If no SSOT covers the invariant, set `requirement_id=GAP` and keep
  `status=NOT_PROVEN` unless project governance explicitly accepts that GAP as
  actionable.

### Evidence binding

Provide **one or more** current bindings:

1. **Path evidence:** `path + symbol/line range`, e.g.
   `src/etl/bronze/ingest.py:42-58 :: class BronzeIngest`.
2. **Command evidence:** `command + scope + timestamp + exit_code + relevant output`.
3. **Runtime/artifact evidence:** artifact id/path + producer revision +
   generation timestamp + relevant fields.

Rules:

- Prefer current checkout + `origin/BASE_BRANCH` over memory or stale reports.
- File proof MUST be repo-relative and verifiable without external access.
- Command proof MUST include scope, UTC timestamp, exit code, and minimal output.
- Generated reports require provenance/freshness binding before use as current
  facts.
- Missing/non-verifiable evidence -> `NOT_PROVEN`.

### Attempted disproof

Before marking P0/P1/P2 `PROVEN`, attempt at least one plausible falsifier:
sanctioned compatibility seam, generated-source ownership, intentional
exception, alternate call path, runtime flag, or counterexample test. Record
what was checked and why the claim survived.

P3 findings SHOULD also record disproof when the claim could plausibly be an
intentional exception.

### Exception / suppression contract

An intentional exception neutralizes or downgrades a finding only when it has:

- explicit owner;
- scope;
- rationale;
- authoritative path or registry reference;
- expiry/review condition when applicable.

Untracked comments, stale allowlists, broad `type: ignore`, skips/xfails, or
historical docs are not self-authorizing exceptions.
