# Local Skills Catalog (BioETL Core)

The compact canonical registry of BioETL-focused local skills under
`.codex/skills/`. Select a mode within a skill before adding a new route.

## Canonical Rules

- `.codex/skills/` is the canonical source for repository-local skills.
- `docs/00-project/ai/skills/local/` is a generated mirror and must not be edited manually.
- `scripts/ai/codex/skills-mirror-contract.json` defines sanctioned parity with
  `.devin/skills/`: entrypoint and catalog membership must match, shared
  references must be identical, and runtime-specific metadata/content variants
  remain explicit.
- Treat each `SKILL.md` frontmatter (`name`, `description`) as the trigger contract.
- Verify and sync the local docs mirror with:

```bash
bash scripts/ai/codex/check_skills_mirror.sh --check
bash scripts/ai/codex/check_skills_mirror.sh --sync
```

`--sync` regenerates only the transformed docs mirror. Approved cross-runtime
reconciliation uses `python -m scripts.ai.sync.runtime_skills --mode sync
--approved --report <path>`; it preserves sanctioned Devin runtime variants and
emits a machine-readable drift/sync report for owner review.

## Active Skills

| Skill | Primary modes |
| --- | --- |
| `py-audit-bot` | baseline, final, targeted, review, debt, reproducibility |
| `py-config-bot` | configuration, schema, contract |
| `py-debug-bot` | reproduce, isolate, fix |
| `py-doc-bot` | focused docs, broad docs audit, mirror sync |
| `py-plan-bot` | implementation, refactor, release planning |
| `py-test-bot` | focused tests, broad campaign, flake triage |
| `research-workflow` | single-stream, multi-stream research and evidence |
| `new-pipeline` | provider/entity scaffolding |
| `observability-dashboard` | dashboard edit, render, query debug |
| `observability-prometheus` | rule edit, rule test, query debug |
| `technical-designer-mermaid` | diagrams |
| `vcr-record` | HTTP cassette lifecycle |
| `verify-architecture` | quick, category, full checks |
## Consolidation Policy

- Do not create a skill for a mode of an existing workflow.
- Runtime discovery and repository inspection belong in runtime instructions and
  ordinary tools, not standalone skills.
- GitHub PR work uses the available GitHub capability and repository policy.
- Each active project skill provides `agents/openai.yaml` metadata and is
  covered by the Codex skill architecture gate.

## Mirror Doc Index

- [new-pipeline](new-pipeline/SKILL.md)
- [observability-dashboard](observability-dashboard/SKILL.md)
- [observability-prometheus](observability-prometheus/SKILL.md)
- [py-audit-bot](py-audit-bot/SKILL.md)
- [py-config-bot](py-config-bot/SKILL.md)
- [py-debug-bot](py-debug-bot/SKILL.md)
- [py-doc-bot](py-doc-bot/SKILL.md)
- [py-plan-bot](py-plan-bot/SKILL.md)
- [py-test-bot](py-test-bot/SKILL.md)
- [research-workflow](research-workflow/SKILL.md)
- [technical-designer-mermaid](technical-designer-mermaid/SKILL.md)
- [vcr-record](vcr-record/SKILL.md)
- [verify-architecture](verify-architecture/SKILL.md)


## Shared Generic Skills

Additional non-BioETL generic skills may coexist under `.codex/skills/` (for example discovery, decision, and research helpers). They are intentionally excluded from the core catalog above.
