> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/vcr-record/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "vcr-record"
description: "Record, validate, update, and clean VCR cassettes for BioETL HTTP tests with placement, determinism, and secret-safety checks."
---

# VCR Record

## Objective

Manage VCR cassette lifecycle for provider integration tests.

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Canonical runtime entrypoint: this `SKILL.md`
- Shared wrapper contract: [../py-audit-bot/references/wrapper-contract.md](../py-audit-bot/references/wrapper-contract.md)
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Trigger Scope

Use this wrapper for cassette recording, cassette refresh, missing-cassette
triage, cassette cleanup, or secret-safety review around HTTP integration tests.

## Workflow

1. Follow the shared wrapper contract.
1. Adapt shell examples to the current environment when needed.
1. Always include cassette validation and secret sanitization checks.
1. Prefer repository-local commands (`uv run ...`) consistent with project standards.
1. Keep cassette updates scoped to the provider/entity and test path requested.

## Expected Output

- Cassettes recorded, updated, cleaned, or explicitly left unchanged.
- Record mode used.
- Secret-safety validation result.
- Focused test result.

## Validation

Use the VCR placement and targeted pytest checks relevant to the cassette:

```bash
python -m scripts.engineering.qa.vcr check-placement
```

Then run the provider integration test that consumes the cassette.

## Fallback

If network recording is unavailable, do not synthesize cassettes. Report the
missing cassette path and the exact record-mode command to run later.
