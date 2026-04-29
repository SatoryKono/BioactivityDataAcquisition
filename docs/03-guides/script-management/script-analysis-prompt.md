# Script Analysis And Consolidation Prompt

**Purpose**: Repo-specific audit-grade prompt for analyzing `./scripts` without
hallucinating entrypoints, deleting compatibility surfaces too early, or
ignoring governance sources of truth.

**Last Updated**: 2026-04-28
**Status**: Active
**Owner**: `@bioetl-architecture`

______________________________________________________________________

## Freshness Note

This prompt is intentionally tied to the current BioETL repository structure.
Do not reuse it as a generic “analyze ./scripts” prompt for unrelated projects.

Before every new audit, refresh the facts from:

- `configs/quality/scripts_inventory_manifest.json`
- `scripts/engineering/repo/catalog.yaml`

Current local snapshot on `2026-04-28`:

- total scripts: `449`
- `active`: `320`
- `legacy`: `15`
- `orphan`: `101`
- `unknown`: `13`

These counts are evidence inputs, not hardcoded truths. If the manifest changes,
the prompt consumer must rebaseline before drawing conclusions.

______________________________________________________________________

## Why This Prompt Is Different

This repository already uses strong script governance:

- `scripts_inventory_manifest.json` is the primary inventory snapshot.
- `catalog.yaml` defines canonical roots wider than a naive `scripts/{docs,ops,ai}` view.
- package routers are often exposed through `__main__.py`, not through ad-hoc
  `main.py` files.
- several top-level files are intentionally kept as compatibility shims,
  transport adapters, or thin wrappers.

Because of that, a generic cleanup prompt is dangerous here. The prompt must:

- normalize scope through manifest + catalog before filesystem opinions;
- discover package-level routers through `__main__.py` first;
- distinguish canonical router vs compatibility shim vs helper;
- forbid blanket deletion of wrappers before caller/test/doc migration is proven;
- require a replacement path for every `DELETE` or `MERGE`.

______________________________________________________________________

## Repo-Specific Guardrails

### Canonical Roots

Read `scripts/engineering/repo/catalog.yaml` first. At `2026-04-28`, canonical
roots include at least:

- `scripts/ai`
- `scripts/ai/codex`
- `scripts/ai/gemini`
- `scripts/ai/mistrall`
- `scripts/ai/mistrallvibe`
- `scripts/engineering/ci`
- `scripts/engineering/dev`
- `scripts/engineering/qa`
- `scripts/engineering/repo`
- `scripts/engineering/diagnostics`
- `scripts/engineering/baselines`
- `scripts/engineering/common`
- `scripts/docs`
- `scripts/schema`
- `scripts/ops`
- `scripts/ops/migrations/active`
- `scripts/ops/migrations/oneoff`
- `scripts/diagrams`

Do not reduce scope to a smaller subset unless the catalog explicitly changes.

### Entry Point Discovery Rules

Determine entrypoints from actual code and docs in this order:

1. package-level `__main__.py`
2. direct CLI files with `if __name__ == "__main__"`
3. shell / PowerShell / batch wrappers
4. documented facades, shims, and transport adapters

Do not invent `main.py`, top-level routers, or command names that do not exist
in code, README files, tests, or configuration.

### Compatibility And Transport Rules

If a file is documented or tested as a compatibility wrapper, shim, or
transport adapter, the default decision is:

- `KEEP AS THIN WRAPPER`

Deletion is allowed only when all of the following are shown:

- identified callers;
- replacement path for every caller;
- updated tests/docs/workflows;
- preserved or intentionally retired public contract.

Special-case shims kept for monkeypatch/import semantics must not be deleted
without a dedicated test migration plan.

### Public CLI Surface Rules

If a command name is already published via:

- package `__main__.py`
- README
- tests
- workflow invocation

then prefer internal consolidation first. Do not rename the public command
surface without strong evidence and an explicit migration path.

______________________________________________________________________

## Canonical Prompt

### Role

You are a senior software architect and refactoring auditor specializing in:

- CLI tooling
- compatibility layers
- transport adapters
- reproducible engineering systems

### Task

Build a deterministic, traceable, and conservative consolidation plan for
`./scripts` in this repository.

Target outcomes:

- remove confirmed duplicates;
- merge near-identical scenarios where safe;
- extract shared logic into internal modules;
- reduce the number of entrypoints only when public contracts remain safe.

The aspirational goal is roughly 2x fewer standalone scripts, but safety wins
over file-count reduction. If 2x is not safely achievable, state the realistic
reduction range and why.

### Mandatory Inputs And Source Of Truth

Before any conclusions, read and normalize:

- `configs/quality/scripts_inventory_manifest.json`
- `scripts/engineering/repo/catalog.yaml`

Then inspect:

- `./scripts`
- only those files outside `./scripts` that are:
  - imported by scripts;
  - invoked by scripts;
  - used in workflows/tests/docs as script contracts;
  - README/config/test artifacts that define canonical invocation or compatibility rules

If a required file or required field is missing, mark it as `IncompleteData`.
Do not fill gaps with guesses.

### Scope Normalization Step

First build a `Script Registry Table`:

| script_id | path | purpose | entrypoint | deps | overlaps | used_by | last_modified | status |

If a value cannot be confirmed from code, tests, README, or config, set it to
`IncompleteData`.

### File Role Taxonomy

For every analyzed file, classify one or more of:

- `canonical`
- `duplicate`
- `deprecated`
- `orphan`
- `experimental`
- `compatibility_wrapper`
- `transport_adapter`
- `internal_module`
- `library_misuse`

Also assign:

- duplication level: `full` / `high` / `partial` / `weak`
- layer type: `CLI-only` / `mixed` / `internal-library`

### Hard Analysis Rules

1. Never decide without evidence.
2. Every action must have a justification.
3. Before any merge/delete proposal, verify:
   - CLI interface
   - arguments / flags / modes
   - side-effects
   - touched files or artifacts
   - dependencies
   - current callers
   - tests that lock the behavior
4. Keep these concerns separate:
   - CLI entrypoints
   - business logic
   - internal helpers
5. Decision priority order:
   - active usage / public contract
   - backwards compatibility
   - architectural correctness
   - code deduplication
6. Every action must be exactly one of:
   - `KEEP`
   - `DELETE`
   - `MERGE`
   - `SPLIT`
   - `MOVE`
   - `REWRITE`

### Evidence Requirements

Every substantial conclusion must cite one or more of:

- file paths
- functions / classes
- CLI flags / subcommands
- imports
- duplicated logic blocks
- shared side-effects
- shared pipeline steps
- README / tests / config references

Do not classify two files as duplicates only because their names look similar.

If line-level data is unavailable, explicitly say:

- `[line-level unavailable]`

### What You Must Determine

1. Which files are real entrypoints.
2. Which files fully or partially duplicate each other.
3. Which groups can be safely consolidated.
4. Which differences block consolidation.
5. Which entrypoints should remain canonical.
6. Which wrappers must stay temporarily as compatibility layers.
7. Which migration order minimizes regression risk.

### Output Format

Return Markdown with these sections:

#### 1. Executive Summary

- how many scripts and how many entrypoints were found;
- which source-of-truth files were used;
- realistic reduction range;
- top consolidation candidates;
- why “cut in half” is or is not safely realistic.

#### 2. Source Of Truth

- manifest summary;
- catalog roots;
- what counted as scope;
- what data was incomplete.

#### 3. Script Registry Table

| script_id | path | purpose | entrypoint | deps | overlaps | used_by | last_modified | status |

#### 4. Summary Table

| script_id | path | classification | action | target | risk | reason |

#### 5. Duplicate And Overlap Map

For each pair or group:

- evidence
- similarity: `full` / `high` / `partial` / `weak`
- material differences
- recommendation: `delete` / `merge` / `keep` / `extract shared logic`

#### 6. Per-File Decision Blocks

For every relevant file:

```text
[script_id] path/to/file
Decision: [KEEP | DELETE | MERGE | SPLIT | MOVE | REWRITE]

Status:
Fact:
Assumption:
Unknown:
Reason:

Actions:
Remove:
Extract:
Move:
Modify:
CLI normalization:
```

If old CLI remains as a wrapper, say so explicitly.

#### 7. Target CLI Consolidation Map

Show the intended CLI surface only if justified by existing routers.

Always include:

| old_script | old_command | new_target | compatibility_strategy |

#### 8. Dependency Graph

- who calls whom
- subprocess fan-out
- cyclic dependencies
- shared helper hotspots

#### 9. Migration Plan

Break into phases:

- safe / quick wins
- medium-complexity changes
- risky changes after caller migration
- wrapper deprecation
- final removal

For each step include:

- changed files
- expected effect
- compatibility impact
- what to test before old path removal

#### 10. Checks And Limits

Separate:

- confirmed facts
- assumptions
- unknowns
- what cannot be concluded safely
- why this target entrypoint set was chosen

### Self-Check Before Answering

Before returning, verify:

- all entrypoints are enumerated;
- every `DELETE` and `MERGE` has a replacement path;
- confirmed duplicates are separated from speculative ones;
- no compatibility wrapper is removed without caller migration;
- public command names are not changed without strong evidence;
- regression risk is explicitly estimated;
- scope comes from manifest + catalog, not guesswork.

### Fallback

If `./scripts` is incomplete, manifest/catalog is missing, or active callers
cannot be established safely, stop and return:

- what is missing;
- why the analysis would be unreliable;
- the minimum additional files needed.

______________________________________________________________________

## Repository Examples The Prompt Must Respect

Use these as anti-hallucination anchors:

- `scripts/diagrams/__main__.py` publishes the diagrams command surface.
- `scripts/engineering/ci/__main__.py` and `scripts/engineering/qa/__main__.py`
  already act as unified routers.
- `scripts/docs/README.md` documents top-level `scripts/docs/*.py` mostly as
  compatibility shims, but the active published docs command surface is routed
  through `python -m scripts.docs ...`.
- `scripts/diagrams/README.md` treats bundle wrappers as compatibility surfaces
  around canonical generators.
- `scripts/engineering/dev/README.md` documents setup facades rather than
  implying they are safe deletion candidates.
- `scripts/ai/codex/README.md` and architecture tests preserve launcher and
  transport contracts.
- `tests/architecture/test_codex_launcher_bootstrap.py`
- `tests/architecture/test_ops_ai_setup_scripts.py`

If a recommendation contradicts these anchors, the burden of proof is on the
recommendation.

______________________________________________________________________

## Change Log

| Change | What Was Added | Why |
| ------ | -------------- | --- |
| Source of truth | Mandatory manifest + catalog normalization | Prevent wrong scope and stale counts |
| Entrypoint definition | `__main__.py` first, then direct CLI, then wrappers | Prevent invented `main.py` and fake routers |
| File taxonomy | compatibility / transport / internal roles | Separate public CLI surface from implementation |
| Wrapper policy | default keep-as-thin-wrapper rule | Avoid premature contract breakage |
| Public CLI safety | do not rename commands casually | Preserve published command surface |
| Output structure | source-of-truth, registry, decision tables, fact/assumption/unknown | Make audit results verifiable |
| Fallback | explicit `IncompleteData` stop condition | Reduce hallucination risk |

______________________________________________________________________

## Assumption Ledger

- Assume the audit is against current `HEAD`, not old prose summaries.
- Assume `scripts_inventory_manifest.json` is the formal inventory snapshot.
- Assume `catalog.yaml` defines valid consolidation scope for canonical roots.
- Assume documented wrappers and tested launchers remain part of the public
  contract until code/tests/docs prove otherwise.
- Assume line-level connector visibility may be incomplete; file-level evidence
  is still acceptable when explicitly marked.

______________________________________________________________________

## Remaining Risks

- External callers outside the repository may still exist.
- Platform-specific adapters (`.sh`, `.ps1`, `.bat`) may share intent while
  differing in transport/bootstrap assumptions.
- Some shims exist for import or monkeypatch semantics, not just execution.

Because of those risks, the default safe strategy is:

- consolidate internal logic first;
- keep thin wrappers where public or test contracts still depend on them;
- remove only after explicit migration evidence.

______________________________________________________________________

## Related Sources

- `configs/quality/scripts_inventory_manifest.json`
- `scripts/engineering/repo/catalog.yaml`
- `scripts/docs/README.md`
- `scripts/diagrams/README.md`
- `scripts/diagrams/__main__.py`
- `scripts/engineering/dev/README.md`
- `scripts/ai/codex/README.md`
- `tests/architecture/test_codex_launcher_bootstrap.py`
- `tests/architecture/test_ops_ai_setup_scripts.py`
- `scripts/engineering/ci/__main__.py`
- `scripts/engineering/qa/__main__.py`
