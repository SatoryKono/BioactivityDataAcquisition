# POST_CHANGE_VALIDATION.md

*Status: internal-published (AI runtime validation policy)*

## Purpose

Define the minimum validation protocol after AI-assisted changes to code,
configs, docs, contracts, prompts, diagrams, and runtime instruction surfaces.

## Applies To

- production code
- tests
- configs
- docs and diagrams
- prompts
- runtime AI files in `.codex/**`, `.gemini/**`, and `AGENTS.md`

## Required Protocol

1. Re-scan impacted surfaces before finalizing.
1. Use memory plus repo search to locate related tests, docs, contracts,
   configs, workflows, and mirrors.
1. Run the smallest sufficient verification set for the touched surface.
1. If runtime behavior changed, update the runtime tree first and the docs
   mirror second.
1. Record executed checks, skipped checks, and unresolved uncertainty in the
   final report.

## Minimum Surface Checks

### Runtime AI files

- verify canonical links and stale-path cleanup
- run `python -m scripts.docs check-drift --runtime-mirrors --freshness`
- run the AI-surface drift check when available in `scripts.docs check-drift`

### Docs, guides, prompts, diagrams

- run `python -m scripts.docs check-links --links --specs --configs`
- run `python -m scripts.docs check-drift --runtime-mirrors --freshness`

### Code and tests

- locate impacted tests before deciding validation scope
- run targeted unit/integration/architecture tests appropriate to the change

### Configs and contracts

- locate related config validators, contract tests, and docs references
- run the narrowest relevant config/contract validation commands

## Final Report Requirements

The closeout MUST include:

1. changed files or change areas
1. checks run
1. skipped checks with reason
1. mirror-sync status when AI runtime files or docs mirrors changed
1. explicit callout if any stale guidance remains for follow-up
