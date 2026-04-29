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

| Surface                 | Primary role                      | Source-of-truth status                | Editable for behavior                  | Expected content                                                                                |
| ----------------------- | --------------------------------- | ------------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `.codex/**`             | Codex runtime surface             | Canonical for Codex runtime behavior  | Yes                                    | live agent registry, skills, Codex-specific orchestration, runtime settings                     |
| `.gemini/**`            | Gemini runtime surface            | Canonical for Gemini runtime behavior | Yes                                    | live Gemini agent registry, skills, Gemini-specific orchestration, runtime settings             |
| `docs/00-project/ai/**` | Published/internal mirror surface | Not canonical for runtime behavior    | Only for mirror/index/guidance updates | curated mirrors, navigation, contributor guidance, memory entrypoints, prompt and skill indexes |

## Source-of-Truth Rules

1. `.codex/**` is the authoritative source for Codex runtime behavior.
1. `.gemini/**` is the authoritative source for Gemini runtime behavior.
1. `docs/00-project/ai/**` is a repo-only or internal-published mirror layer for
   discoverability and contributor guidance; it MUST NOT redefine runtime
   behavior on its own.
1. Canonical project rules still come from:
   - `docs/00-project/RULES.md`
   - `docs/01-requirements/REQUIREMENTS.md`
   - accepted ADRs in `docs/02-architecture/decisions/`

## Precedence Model

Default precedence for AI behavior and guidance:

1. `docs/00-project/RULES.md`
1. `docs/01-requirements/REQUIREMENTS.md`
1. accepted ADRs
1. runtime maps in `.codex/**` or `.gemini/**`
1. runtime profiles and skills in the same runtime tree
1. docs mirrors and contributor guides

The docs mirror MAY summarize or link to runtime behavior, but it MUST NOT
override the active runtime tree.

## Sync Direction

Default sync direction is:

1. runtime tree changes first (`.codex/**` or `.gemini/**`)
1. published/internal mirror refresh second (`docs/00-project/ai/**`)
1. validation third
1. governance/index refresh fourth, if the mirror contract changed

This means:

- runtime-specific behavior MUST be edited in the runtime tree first
- docs mirrors SHOULD be updated after runtime changes when they affect
  discoverability, contributor guidance, or published examples
- docs-only edits MAY improve wording, indexes, and navigation, but MUST NOT
  silently override runtime truth

## Sync Checklist

1. Edit the canonical runtime surface first.
1. Sync the affected docs mirror or guide second.
1. Run runtime/doc drift checks third.
1. Report any intentional divergence explicitly.

## Allowed Divergence

The following divergence is intentional and not a bug by itself:

- runtime-specific commands, wrappers, and settings may differ between runtimes
- docs mirrors may summarize or normalize runtime concepts for navigation
  purposes instead of reproducing every runtime file verbatim

The following divergence is not acceptable:

- mirror docs contradict runtime source about which file is authoritative
- mirror docs describe a runtime entrypoint that no longer exists
- contributor guidance tells users to edit a docs mirror instead of the runtime
  source for behavior changes
- active Codex/Gemini runtime surfaces depend on `.claude/**` as a canonical
  behavior source

## Edit Rules

- Change runtime behavior:
  edit the matching runtime tree first (`.codex/**` or `.gemini/**`).
- Change published navigation or contributor guidance:
  edit `docs/00-project/ai/**`.
- Change project-wide rules:
  edit governance/RULES/ADR surfaces, not AI mirrors.

## Practical Routing

- Agent orchestration behavior for Codex -> `.codex/agents/**`
- Agent orchestration behavior for Gemini -> `.gemini/agents/**`
- Skill trigger/runtime behavior for Codex -> `.codex/skills/**`
- Skill trigger/runtime behavior for Gemini -> `.gemini/skills/**`
- Human-readable indexes, mirrors, and onboarding pointers -> `docs/00-project/ai/**`

## Related Entry Points

- [AI Documentation Surface](../../README.md)
- [Agent Catalog — BioETL (Mirror)](../README.md)
- [Skills Mirror in docs/](../../skills/README.md)
- [Memory Usage](../guides/MEMORY_USAGE.md)
- [Post-Change Validation](POST_CHANGE_VALIDATION.md)
- [Documentation Publication Policy](../../../governance/06-doc-publication-policy.md)
