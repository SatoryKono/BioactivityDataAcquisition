______________________________________________________________________

Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-26'

______________________________________________________________________

# AI Runtime Mirror Ownership

*Статус: internal-published | Ownership contract for runtime and docs mirrors*

Этот документ фиксирует, какая AI surface является runtime source of truth,
какая является published mirror, и где допустим intentional drift.

## Ownership Matrix

| Surface | Primary role | Source-of-truth status | Editable for behavior | Expected content |
| ----------------------- | --------------------------------- | ---------------------------------------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `.codex/**` | Codex runtime surface | Canonical for tracked runtime behavior on `main` | Yes | live agent registry (`.codex/agents/*.md` tracked), skills, Codex-specific orchestration, runtime settings |
| `.junie/**` | JetBrains Junie runtime surface | Canonical for tracked runtime behavior on `main` (equal peer to `.codex/**`) | Yes, keeping parity with `.codex/**` | `.junie/guidelines.md` (root contract), `.junie/agents/**` (JUNIE-RUNTIME + 9 py-* profiles + README/ORCHESTRATION mirrors), `.junie/skills/**` (mirror of `.codex/skills/**`), `.junie/plans/**` |
| `.devin/agents/**`, `.devin/skills/**` | Devin runtime surface | Canonical for tracked Devin-specific runtime behavior | Yes, subject to Codex–Devin skill parity contracts | `DEVIN-RUNTIME`, custom profile entrypoints, orchestration, and Devin skill adaptations |
| `.gemini/settings.json` | Gemini local config surface | Local-only runtime config; not a tracked behavior tree on `main` | Yes, for machine-local settings only | optional local checkout settings with machine-specific paths |
| `.gemini/agents/**`, `.gemini/skills/**` | Gemini runtime behavior tree | Not present in the current `main` checkout | No tracked source on `main` today | if a future task adds them, they must be verified and documented in the same change |
| `docs/00-project/ai/**` | Published/internal mirror surface | Not canonical for runtime behavior | Only for mirror/index/guidance updates | curated mirrors, navigation, contributor guidance, memory entrypoints, prompt and skill indexes |
| `docs/00-project/ai/rules/cursor/**` | Cursor rules source | Canonical for Cursor AI guidance in-repo | Yes | thematic `.mdc` rules derived from governance stack |
| `docs/00-project/ai/rules/windsurf/**` | Windsurf/Cascade rules mirror | Derived from `cursor/` via sync script | Regenerate via `scripts/ai/sync_windsurf_rules.py` | `.md` rules + workflows for Cascade |
| `.windsurf/**` | Windsurf local deploy surface | Machine-local deploy target | Deploy only | generated from `docs/00-project/ai/rules/windsurf/` |
| `.devin/workflows/**` | Devin Cascade-style workflows | Tracked Devin guidance workflows | Yes (keep parity with Windsurf workflows) | `review`, `post-change`, `pre-commit`, `qodo-sync`, plus specialized audits |
| `.devin/wiki.json` | Devin DeepWiki navigation | Derived discovery layer | Yes for navigation notes | MUST NOT override RULES/ADR/runtime truth |

## Source-of-Truth Rules

1. `.codex/**` is the authoritative source for tracked Codex runtime behavior.
1. `.junie/**` is the authoritative source for tracked JetBrains Junie runtime
   behavior and is an **equal peer** to `.codex/**`. Parity between the two
   runtime trees is a governance contract enforced by
   `scripts/ai/junie/check_junie_mirror.sh` (contract file:
   `scripts/ai/junie/junie-mirror-contract.json`). Automated sync propagates
   in one direction (`.codex/** → .junie/**`); the reverse direction is
   allowed only via a reviewed change that also updates the Codex side in the
   same commit.
1. `.devin/agents/**` and `.devin/skills/**` are authoritative for tracked
   Devin-specific runtime behavior. Shared skill structure remains governed by
   the Codex–Devin mirror contract; Devin-native profile and invocation details
   remain owned by the Devin runtime tree.
1. `.gemini/settings.json` and other optional Gemini local config files are
   machine-local config surfaces, not proof of a tracked Gemini behavior tree
   on `main`.
1. `docs/00-project/ai/**` is a repo-only or internal-published mirror layer for
   discoverability and contributor guidance; it MUST NOT redefine runtime
   behavior on its own.
1. If a future task introduces tracked `.gemini/agents/**` or
   `.gemini/skills/**` surfaces, it MUST update this ownership contract,
   `AGENTS.md`, and affected mirrors in the same change set.
1. Canonical project rules still come from:
   - `docs/00-project/NORMATIVE_SOURCES.md`
   - `docs/00-project/RULES.md`
   - `docs/01-requirements/REQUIREMENTS.md`
   - accepted ADRs in `docs/02-architecture/decisions/`

## Precedence Model

Default precedence for AI behavior and guidance:

1. active runtime source for the current agent or skill — equal peers
   `.codex/**` (`.codex/agents/CODEX-RUNTIME.md`) and `.junie/**`
   (`.junie/agents/JUNIE-RUNTIME.md`, with root contract `.junie/guidelines.md`)
1. `.devin/agents/DEVIN-RUNTIME.md` and the selected
   `.devin/agents/*/AGENT.md` profile for Devin sessions
1. a matching tracked `.gemini/**` surface only when that tree exists in the
   current checkout and has been verified in the same change
1. `docs/00-project/RULES.md`
1. `docs/01-requirements/REQUIREMENTS.md`
1. accepted ADRs
1. docs mirrors, memory sheets, and contributor guides

The docs mirror MAY summarize or link to runtime behavior, but it MUST NOT
override the active runtime tree.

## Sync Direction

Default sync direction is:

1. runtime tree changes first (`.codex/**` and `.junie/**` as equal peers;
   tracked `.gemini/**` only when such a tree actually exists on `main`)
1. runtime-mirror parity check: `bash scripts/ai/junie/check_junie_mirror.sh
   --check` (or `--sync` when the mirror side needs regeneration from
   `.codex/**`) whenever `.codex/agents/**`, `.codex/skills/**`,
   `.junie/agents/**`, or `.junie/skills/**` were touched
1. published/internal mirror refresh next (`docs/00-project/ai/**`)
1. validation third
1. governance/index refresh fourth, if the mirror contract changed

This means:

- runtime-specific behavior MUST be edited in the tracked runtime tree first
- docs mirrors SHOULD be updated after runtime changes when they affect
  discoverability, contributor guidance, or published examples
- docs-only edits MAY improve wording, indexes, and navigation, but MUST NOT
  silently override runtime truth

## Mechanical Sync Checklist

1. Identify whether the change touches runtime behavior, contributor guidance,
   memory navigation, or local runtime config strategy.
1. Edit the canonical runtime surface first when behavior changed.
1. Sync the affected docs mirror, guide, or index second.
1. Confirm published examples still point at live runtime entrypoints.
1. Run runtime/doc drift checks third.
1. Run surface-specific validation from `POST_CHANGE_VALIDATION.md`.
1. Report any intentional divergence explicitly, including why it exists and
   who owns the follow-up.

For broad mechanical normalization of Codex runtime source links and docs mirror
governance anchors, use `scripts/ai/sync_ai_governance.py --check` before
applying changes with the same script.

## Allowed Divergence

The following divergence is intentional and not a bug by itself:

- runtime-specific commands, wrappers, and settings may differ between runtimes
- Codex and Devin skill bodies (`SKILL.md`, optional `agents/openai.yaml`) may
  differ only within sanctioned patterns in
  `scripts/ai/codex/skills-mirror-contract.json`; entrypoint sets, catalogs, and
  **all** `references/**` files remain CI-enforced (presence + byte-identical)
- docs mirrors may summarize or normalize runtime concepts for navigation
  purposes instead of reproducing every runtime file verbatim
- local-only Gemini config may exist without a tracked Gemini agent/skill tree
  on `main`

The following divergence is not acceptable:

- mirror docs contradict runtime source about which file is authoritative
- mirror docs describe a tracked Gemini runtime entrypoint that does not exist
  on `main`
- contributor guidance tells users to edit a docs mirror instead of the runtime
  source for behavior changes
- active Codex/Gemini runtime surfaces depend on `.claude/**` as a canonical
  behavior source
- runtime config docs claim portability while a checked-in portable config
  depends on machine-local absolute paths

## Edit Rules

- Change runtime behavior:
  edit the matching tracked runtime tree first (`.codex/**` or `.junie/**` —
  they are equal peers and MUST stay in parity via
  `scripts/ai/junie/check_junie_mirror.sh`; `.gemini/**` only when the tree
  exists on `main`).
- Change published navigation or contributor guidance:
  edit `docs/00-project/ai/**`.
- Change Gemini local-config classification:
  edit `MCP_LOCAL_RUNTIME_CONFIG.md` and the affected contributor guidance.
- Change project-wide rules:
  edit governance/RULES/ADR surfaces, not AI mirrors.

## Junie Ownership

- Owner: BioETL Team (same as `.codex/**`).
- Runtime source of truth: `.junie/guidelines.md` (root contract) +
  `.junie/agents/JUNIE-RUNTIME.md` (runtime map).
- Tracked subtrees: `.junie/guidelines.md`, `.junie/agents/**`,
  `.junie/skills/**`, `.junie/plans/**`. Selective un-ignore is declared in
  `.gitignore`.
- Machine-local subtrees (MUST remain untracked): `.junie/history/`,
  `.junie/state/`, `.junie/cache/`.
- Mirror contract: `scripts/ai/junie/junie-mirror-contract.json` (parity of
  py-* agent profiles by filename + SHA-256, byte-identical shared agent docs
  `README.md`/`ORCHESTRATION.md`, byte-identical `SKILLS-CATALOG.md`, and
  full byte-identical `.codex/skills/**` ↔ `.junie/skills/**` tree; runtime-
  only files are declared per side, `py-code-bot` is a documented exclusion).
- Enforcement: `bash scripts/ai/junie/check_junie_mirror.sh --check` (read-
  only, exit 1 on drift) and `--sync` (one-way `.codex/** → .junie/**`; never
  writes into `.codex/**`).
- Divergence policy: **not tolerated** for content covered by the contract.
  Any behavior change MUST land in `.codex/**` first, then be propagated via
  `--sync` (or, for coupled cross-runtime changes, in the same commit).
  Reverse-direction fixes require a reviewed change that also updates the
  Codex source in the same commit.

## Practical Routing

- Agent orchestration behavior for Codex -> `.codex/agents/**`
- Agent orchestration behavior for Junie -> `.junie/agents/**` (equal peer;
  parity with `.codex/agents/**` enforced by `check_junie_mirror.sh`)
- Agent orchestration behavior for Gemini -> only when a tracked
  `.gemini/agents/**` tree exists on `main`; otherwise treat Gemini references
  in docs as mirrors or local-only guidance
- Skill trigger/runtime behavior for Codex -> `.codex/skills/**`
- Skill trigger/runtime behavior for Junie -> `.junie/skills/**` (equal peer;
  parity with `.codex/skills/**` enforced by `check_junie_mirror.sh`)
- Skill trigger/runtime behavior for Gemini -> only when a tracked
  `.gemini/skills/**` tree exists on `main`
- Gemini local config classification -> `MCP_LOCAL_RUNTIME_CONFIG.md`
- **Devin orchestration context** -> use `.devin/agents/DEVIN-RUNTIME.md`,
  `.devin/agents/ORCHESTRATION.md`, and the selected
  `.devin/agents/*/AGENT.md` profile. Shared logical behavior and skill
  references remain parity-checked against Codex; Devin-native invocation and
  permissions remain owned by the Devin tree.
- **GitHub Copilot** -> keep path packs thin; do **not** duplicate Codex/Devin
  skills into `.github/prompts` without a measured gap and owner.
- **Cursor onboarding** -> after clone run `bash scripts/ai/cursor/setup_cursor.sh`
  (see `scripts/ai/cursor/README.md`).
- Human-readable indexes, mirrors, and onboarding pointers -> `docs/00-project/ai/**`

## Related Entry Points

- [AI Documentation Surface](../../README.md)
- [Agent Catalog — BioETL (Mirror)](../README.md)
- [Skills Mirror in docs/](../../skills/README.md)
- [Memory Usage](../guides/MEMORY_USAGE.md)
- [Post-Change Validation](POST_CHANGE_VALIDATION.md)
- [MCP Local Runtime Config Strategy](MCP_LOCAL_RUNTIME_CONFIG.md)
- [Documentation Publication Policy](../../../governance/06-doc-publication-policy.md)

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
