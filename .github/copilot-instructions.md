# BioETL Instructions for GitHub Copilot

Use this file as a strict operating profile for code suggestions in this repository.

## Canonical Sources

- `docs/00-project/NORMATIVE_SOURCES.md` (normative stack index)
- `docs/00-project/RULES.md` (project constitution, RFC2119 requirements)
- `docs/01-requirements/REQUIREMENTS.md` (functional/non-functional requirements)
- ADRs in `docs/02-architecture/decisions/`
- `AGENTS.md` (assistant workflow constraints)
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

If guidance conflicts, prioritize canonical sources over this file.
For AI runtime behavior conflicts, follow the runtime-source-first precedence
defined in `AGENTS.md`.

Architecture, Medallion, DI, domain purity, testing, and API rules live in
`docs/00-project/RULES.md` §1–§4. Read RULES instead of relying on summaries
below.

## AI Runtime Notes

- `.codex/**` and `.junie/**` are equal-peer tracked runtime sources on `main`;
  changes covered by their parity contract must update both surfaces.
- `.devin/agents/**` and `.devin/skills/**` are the tracked Devin-specific
  runtime sources.
- `.gemini/settings.json` may exist as a machine-local config surface, but a
  tracked `.gemini/agents/**` or `.gemini/skills/**` tree is not part of the
  current `main` checkout unless added and verified in the same change.
- `docs/00-project/ai/**` is a mirror/guidance layer, not the runtime behavior source.
- Do not rely on `.claude/**` as a canonical behavior source for Codex/Gemini work.

## Copilot Session Guardrails

- The GitHub review body and all inline review comments produced through
  `gh pr review` or an equivalent GitHub API **MUST** be written in Russian,
  regardless of the surrounding conversation language.
- Preserve hexagonal import boundaries and composition-root DI (see RULES §1).
- Preserve Medallion invariants: Bronze append-only, Silver/Gold Delta Lake
  (see RULES §2).
- Never increase technical-debt budgets or hotspot thresholds.
- Never hardcode secrets or weaken assertions to green tests.

## Anti-Patterns (MUST NOT Suggest)

- Layer boundary violations for quick fixes.
- Service locator pattern.
- Hardcoded secrets, tokens, or credentials.
- `print()` for runtime logging (use logger ports/structlog adapters).
- Blocking I/O inside async code.
- Replacing strict typing with broad `Any` to silence type errors.
- CodeQL `c-cpp` / `build-mode: autobuild` (Python-only advanced setup, `build-mode: none`).

## Hallucination Prevention (MUST)

- Do not invent files, modules, classes, commands, or Make targets.
- Before referencing a path/command/API, verify it exists in the repo context.
- If uncertain, state uncertainty and suggest verification steps.
- Keep code changes minimal and evidence-based; avoid speculative refactors.

## Path-Scoped Instructions

Layer/path adapters live under `.github/instructions/*.instructions.md` and
apply only to matching globs (domain, application, infrastructure, composition,
configs, tests). Prefer those packs for path-local guidance; keep this root file
as the global profile.

**Non-goal:** do not invent a Copilot skill registry or copy `.codex/skills/**`
/ `.devin/skills/**` bodies into `.github/prompts` unless a measured gap,
owner, and maintenance cost are documented in the same change.

## Suggestion Quality Checklist

- Includes type annotations for public interfaces.
- Preserves architecture constraints and naming conventions from RULES.
- Adds/updates tests when behavior changes.
- Uses memory plus repo search to identify related tests, docs, contracts, and
  configs before narrowing the validation scope.
- Mentions required verification commands (`make lint`, `make test`, architecture tests).
- After markdown link or `Owner:` / `Status:` / `Class:` header changes, includes
  `python -m scripts.docs generate-cleanup-inventory --update` in the same
  changeset (`--check` reads the working tree, not HEAD).
- Includes migration notes when introducing breaking changes.
