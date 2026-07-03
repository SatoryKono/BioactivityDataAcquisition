---
trigger: always_on
description: "Core BioETL governance and invariants"
---

# BioETL Core Governance

**Canonical references:** `AGENTS.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

- Follow RFC 2119 semantics from `docs/00-project/RULES.md`: MUST/SHOULD/MAY are normative.
- Preserve deterministic outputs: stable ordering, canonical serialization, UTC timestamps.
- Use atomic file writes for artifacts (`tmp` then `os.replace`) where applicable.
- Do not introduce silent breaking changes in public CLI/API/schema contracts.
- For breaking changes, require explicit migration notes and version/changelog updates.
- Source of truth priority: YAML configs + Pandera/domain schemas + active docs in `docs/00-05`.
- Keep architecture boundaries from `AGENTS.md` import matrix; avoid cross-layer violations.
- Never expose secrets in code, docs, configs, tests, or logs.
