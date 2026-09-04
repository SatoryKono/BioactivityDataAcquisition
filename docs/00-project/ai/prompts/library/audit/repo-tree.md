---
id: prompt.audit.repo-tree
version: 1.2.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- SCOPE
- MODE
- LANGUAGE
- AUDIT_MODE
- REQUIRE_GH_TRACKING
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
- fragments/audit-scale.md
- fragments/finding-schema.md
related_ssot:
- AGENTS.md
- .github/root-allowlist.txt
- docs/00-project/governance/03-file-policy.md
- docs/00-project/governance/root-local-clutter-cleanup.md
anti_patterns:
- Mass directory moves without migration plan
- git clean without -n in audit mode
- Ignoring root-allowlist SSOT
tags:
- audit
- repo
- hygiene
- root
- operator
summary: Repository tree and root hygiene audit against allowlist
max_body_lines: 140
---
# Repo tree / root hygiene audit

**Kit:** prompt 4 of `prompt.audit.generic-nine.pack`.
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

## Surface score (this domain)

| Score | Meaning |
| --- | --- |
| 3 | Root minimal; generated/cache excluded; tree matches real boundaries |
| 2 | Small historical clutter without material impact |
| 1 | Noise, duplication, source/generated mix, or unclear ownership |
| 0 | Secrets, dangerous binaries, uncontrolled generated files, or broken reproducibility |

P0: secrets/keys. P1: supply-chain/build artifacts. P2: structural
ambiguity. P3: cosmetic. No mass moves without a migration plan.

## Output

- `reports/audit/repo-tree/report.md` + `findings.json`
- kit extras: `root-inventory.csv`, `large-files.csv`, `ignore-gaps.txt`,
  `generated-files.csv`, `current-vs-target-tree.md`
- `surface_score` 0–3; remediations; `MODE=propose-patches` only with approval

## Stop

Confirmed secret in tree → P0, do not print secret values, stop and escalate.
No mass renames without operator-approved migration plan.
