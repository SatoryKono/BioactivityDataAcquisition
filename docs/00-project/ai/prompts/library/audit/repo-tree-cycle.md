---
id: prompt.audit.repo-tree-cycle
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - SCOPE
  - MODE
  - LANGUAGE
  - AUDIT_MODE
  - INCLUDE_PIPELINE
  - STRICT_UNTRACKED
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - BASE_BRANCH
  - REPO
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
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - .github/root-allowlist.txt
  - docs/00-project/governance/03-file-policy.md
  - docs/00-project/governance/root-local-clutter-cleanup.md
  - docs/00-project/ai/prompts/library/audit/repo-tree.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - .github/workflows/root-hygiene.yml
anti_patterns:
  - Mass directory moves without migration plan
  - git clean without -n in pure audit substeps
  - Ignoring root-allowlist SSOT
  - Committing or editing .env without explicit approval
  - Empty form cycles
  - Raising debt budgets to silence hygiene noise
tags: [audit, repo, hygiene, root, cycle, operator]
summary: Cyclic repository hygiene audit — root allowlist, clutter, ignore, fix, re-verify
max_body_lines: 170
---

# Cyclic repository hygiene audit

N-итерационный **аудит гигиены репозитория**: root allowlist, clutter,
generated noise, large files, ignore/config drift → plan → issues → fix →
PR/CI → merge/close → re-verify.

Domain method: `prompt.audit.repo-tree`. Loop shell: `prompt.audit.orchestrator`.

Default **`N=10`**, **`MODE=full`**, **`INCLUDE_PIPELINE=true`**,
**`STRICT_UNTRACKED=true`**, все **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | repo root + first levels (or path cluster) |
| `MODE` | `full` (also: `audit` \| `audit+issues`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `INCLUDE_PIPELINE` | `true` (CI `root-hygiene` + cleanliness tooling) |
| `STRICT_UNTRACKED` | `true` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |

## BioETL anchors (read, do not reinvent)

- Allowlist SSOT: `.github/root-allowlist.txt` (tracked root count ≡ allowlist; expect **37**)
- File policy: `docs/00-project/governance/03-file-policy.md` §0
- Operator guide: `docs/00-project/governance/root-local-clutter-cleanup.md`
- CI job: `.github/workflows/root-hygiene.yml` (required check context `root-hygiene`)
- Cleanup tool: `python -m scripts.engineering.repo.cleanup_root_local_clutter`
- Cleanliness: `python -m scripts.engineering.repo check-cleanliness --strict-untracked`
- Scratch placement: `scripts/**` or `reports/**` — never root `_tmp_*` / `_cr_*` / `nul`
- `.env` / `.env.*`: secret-bearing; never commit (env-guardrail)

## Preflight

1. `git status --porcelain`; SHA; branch; toolchain; `gh auth status` (no tokens).
2. Dirty foreign work → worktree or **read-only** for audit-only phases.
3. `run_id = <UTC>-repo-hygiene-cycle-<shortsha>`
4. Artifacts: `reports/audit-runs/<run_id>/` (mirror: `reports/audit/repo-tree/`).
5. Record baseline: tracked root file count vs allowlist; cleanliness dry-run.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Audit** | Execute `prompt.audit.repo-tree` on SCOPE. Diff tracked root vs allowlist; inventory clutter patterns; ignore gaps; large tracked files; credential **signals** (never print secret values); dry-run `git clean -ndX` / `git clean -n` only. If `INCLUDE_PIPELINE=true`: inspect `root-hygiene` workflow + cleanliness entrypoints; tag findings `root` \| `tree` \| `ignore` \| `pipeline`. If `STRICT_UNTRACKED=true`: run `check-cleanliness --strict-untracked` (or equivalent) and capture exit/output. |
| **B Plan** | Dedupe; P0 secrets/binaries-in-VCS → P1 allowlist/RH breaches → P2 clutter/ignore gaps → P3 local hygiene. Prefer delete/untrack/rehome over expanding allowlist. No debt-budget raises. |
| **C Issues** | Dedupe open issues (`root-hygiene`, `hygiene`, RH labels). Create if `ALLOW_ISSUE_WRITE` + PROVEN. Title: `[repo-hygiene][P#] one checkable outcome`. Cap `MAX_ISSUES_PER_ITERATION`. |
| **D Fix** | Minimal: purge untracked via reviewed cleanup tool; rehome scripts under `scripts/**`/`reports/**`; fix `.gitignore` gaps; never touch real `.env*` without explicit approval. Mass renames only with operator-approved migration plan. |
| **E Validate** | Re-run allowlist count + `check-cleanliness` (strict if enabled); if `ALLOW_PUSH` → PR + required checks (`root-hygiene` among them). Merge if `ALLOW_MERGE` and acceptance met. |
| **F Close** | Close when fixed on target + `ALLOW_CLOSE`. |
| **G Post** | Per finding: `resolved` \| `unchanged` \| `regressed` \| `new` → `iteration-i/delta.md`. |

## Focus checklist (each cycle)

- [ ] Tracked root file count ≡ `.github/root-allowlist.txt` (expect 37)
- [ ] No root `_tmp_*.py`, `/_cr_*.py`, `/_publish_*.py`, ad-hoc root `test_*.py`
- [ ] No Windows `nul` / `NUL` at root
- [ ] No tracked secret `.env*` (only `.env.example` if allowlisted)
- [ ] Untracked caches/logs not proposed as allowlist expansions
- [ ] Large/binary tracked files flagged with path + size evidence
- [ ] `git clean` only with `-n` until fix phase uses reviewed cleanup tool
- [ ] CI `root-hygiene` still meaningful (not weakened)

## Domain method — repo-tree (each A)

1. Inventory root and shallow tree; classify source/test/docs/scripts/config/
   infra/vendor/generated/build/cache/temp/binary/unknown.
2. Diff root tracked files vs root-allowlist.
3. Check `.gitignore`, `.gitattributes`, lockfiles, manifests, tool-version files.
4. Large tracked files; potential credential **signals** (not proof alone).
5. Dry-run only: `git clean -ndX` / `git clean -n` — never delete in pure audit.
6. Flag competing bootstraps; unclear tests/docs/scripts placement.

## Stop

- Confirmed secret in tree → **P0**, do not print values, escalate, stop mutation.
- No mass renames without operator-approved migration plan.
- Do not expand allowlist to hide clutter without strong SSOT rationale.
- Orchestrator hard-stop conditions apply.

## Success

- `findings.json` + `report.md` under `reports/audit-runs/<run_id>/`
- Allowlist integrity restored or explicitly deferred with owner/date
- Cleanliness/strict-untracked green when mutations claimed fixed
- Issues/PR/merge/close when acceptance met
- `final-summary.md` after N or allowed early-stop

## Related

- Domain: `prompt.audit.repo-tree`
- Pack: `prompt.audit.cyclic-pack`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.audit.repo-tree`
- Closeout: `prompt.closeout.grok`
