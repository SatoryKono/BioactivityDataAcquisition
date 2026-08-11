---
id: prompt.audit.repo-tree
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [any]
params: [SCOPE, MODE, LANGUAGE, AUDIT_MODE, REQUIRE_GH_TRACKING]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
related_ssot:
  - AGENTS.md
  - .github/root-allowlist.txt
  - docs/00-project/governance/03-file-policy.md
  - docs/00-project/governance/root-local-clutter-cleanup.md
anti_patterns:
  - Mass directory moves without migration plan
  - git clean without -n in audit mode
  - Ignoring root-allowlist SSOT
tags: [audit, repo, hygiene, root, operator]
summary: Repository tree and root hygiene audit against allowlist
max_body_lines: 140
---

# Repo tree / root hygiene audit

Audit the tree for ambiguity, accidental artifacts, generated noise, large
files, and config drift. Prefer structure that matches real
architecture/build/test boundaries. Highest priority: secrets, binaries, and
generated content wrongly under version control.


**Machine outputs:** always pair `report.md` + `findings.json` under `reports/audit/repo-tree/`. For multi-iteration loops use `prompt.audit.orchestrator` and `reports/audit-runs/<run_id>/`.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | repo root + first levels (or path) |
| `MODE` | `audit` \| `propose-patches` |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `false` |

## BioETL facts

- Tracked root **must** match `.github/root-allowlist.txt`
- Scratch: `scripts/**` or `reports/**` — never root `_tmp_*` / `nul`
- `.env` is secret-bearing (env-guardrail)

## Method

1. Inventory root and shallow tree; classify source/test/docs/scripts/config/
   infra/vendor/generated/build/cache/temp/binary/unknown.
2. Diff root tracked files vs root-allowlist.
3. Check `.gitignore`, `.gitattributes`, lockfiles, manifests, tool-version files.
4. Large tracked files; potential credential **signals** (not proof alone).
5. Dry-run only: `git clean -ndX` / `git clean -n` — never delete in audit.
6. Flag competing bootstraps; unclear tests/docs/scripts placement.

## Output

- `reports/audit/repo-tree/report.md`
- `reports/audit/repo-tree/findings.json` (finding-schema)
- optional extras listed below or in method notes
- `surface_score` 0–3 (map any 0–5 dimensions via audit-scale)
- findings per finding-schema; top remediations
- `MODE=propose-patches` / write modes: only after operator approval and ALLOW flags when orchestrated

## Stop

Confirmed secret in tree → P0, do not print secret values, stop and escalate.
No mass renames without operator-approved migration plan.
