# [AI runtime][P1] Make skill mirror CI truthful and enforce sanctioned Codex-Devin parity

## Summary

Turn the current false-green AI skill mirror check into a deterministic
validator and add an explicit, reviewable parity contract for the Codex and
Devin skill trees.

## Current Evidence

Verified on tracked `main`:

- `.codex/skills/**` and `.devin/skills/**` each contain the same 37 directories
  with a `SKILL.md` entrypoint.
- The trees are not byte-identical and should not be assumed to be: the current
  inventory has 111 Codex files, 63 Devin files, 48 Codex-only supporting
  files, and 40 content differences among common paths.
- `scripts/ai/codex/check_skills_mirror.sh --check` only verifies that
  `.codex/skills` and `docs/00-project/ai/skills/local` exist, then prints
  `[OK]`; it does not compare, generate, or validate any files.
- Documentation advertises both `--check` and `--sync`, while the script ignores
  all arguments.
- `.github/workflows/skills-consistency.yml` invokes that false-green check but
  does not watch `.devin/skills/**`.
- `scripts/docs/checks/check_drift.py` scans both runtime roots for selected
  policy tokens, but that is not a skill inventory/parity contract.

## Problem

The CI job name and command imply mirror consistency, but the command cannot
detect a removed skill, a stale catalog, a missing required reference bundle,
or an unsanctioned Codex/Devin divergence. This weakens the closure claims from
the previous AI mirror cleanup issues and allows silent runtime capability
drift.

Byte-for-byte mirroring is not a safe default because the two runtimes can have
intentional format-specific metadata and supporting files. The repository needs
a small explicit contract that distinguishes required parity from sanctioned
runtime-specific differences.

## Proposed Scope

1. Define the parity contract for `.codex/skills/**`, `.devin/skills/**`, and
   `docs/00-project/ai/skills/local/**`:
   - required skill entrypoint set
   - required catalog entries
   - shared reference files that must match
   - runtime-specific files that are intentionally optional or transformed
2. Replace the no-op implementation in
   `scripts/ai/codex/check_skills_mirror.sh` with truthful `--check` and `--sync`
   behavior, or replace it with a Python validator/generator and keep the shell
   entrypoint as a thin compatibility facade.
3. Make `--check` read-only, deterministic, and actionable at file level.
4. Update `.github/workflows/skills-consistency.yml` path filters to include
   `.devin/skills/**`, the parity contract, and validator tests.
5. Add focused tests proving the checker fails for:
   - a missing Devin `SKILL.md`
   - an unexpected skill entrypoint
   - stale catalog membership
   - a changed file classified as required-identical
6. Preserve explicit runtime-specific variants instead of forcing accidental
   byte equality.

## Non-Goals

- Do not make docs mirrors authoritative over `.codex/**`.
- Do not restore a tracked Gemini runtime tree.
- Do not silently copy Codex-only `agents/openai.yaml` files into Devin without
  confirming Devin ownership and format support.
- Do not increase any technical-debt budget, exemption, or hotspot threshold.
- Do not edit `.env` files.

## Acceptance Criteria

- `check_skills_mirror.sh --check` fails on a controlled parity violation and
  reports the exact missing, extra, or mismatched path.
- `--sync` either performs the documented generated-mirror operation or is
  removed from docs and CLI usage; it may not remain an ignored argument.
- The 37-skill Codex/Devin entrypoint set is protected by a deterministic test.
- Intentional runtime-specific files are represented by a reviewed contract,
  not by implicit omission.
- `skills-consistency.yml` runs when `.devin/skills/**` changes.
- Existing docs-mirror generation/ownership checks continue to pass.
- Debt outcome for touched AI runtime/tooling files is `improved` or
  `unchanged`, never `worsened`.

## Validation

```bash
bash scripts/ai/codex/check_skills_mirror.sh --check
bash scripts/ops/support/skills/check_ai_skills_layout.sh
uv run python -m pytest tests/unit/scripts -q -k "skills and mirror"
uv run python -m scripts.docs check-drift --runtime-mirrors --freshness
git diff --check
```

Add a negative fixture/test that mutates a temporary mirror tree and proves the
check returns non-zero without changing the working tree.

## Related Work

- #3426 — runtime-to-mirror checklist (closed)
- #3492 — AI runtime policy drift gates (closed)
- #6113 — duplicate AI skill reference cleanup (closed)
- #6177 — generator-owned skill mirror duplicates (closed)

This issue addresses the still-reproducible false-green checker and Devin
parity gap; it does not reopen the completed documentation cleanup scopes.

## Metadata

- Priority: P1
- Suggested labels: `ai-runtime`, `governance`, `testing`, `technical-debt`
- Suggested assignee: `@SatoryKono`
- Assignee confidence: high (CODEOWNERS plus recent file history)

