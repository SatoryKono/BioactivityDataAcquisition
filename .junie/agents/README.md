## Canonical Sources

- Runtime contract and precedence: `AGENTS.md`
- Normative source index: `docs/00-project/NORMATIVE_SOURCES.md`

Load only the role- and risk-relevant sources selected by those contracts.

# BioETL Codex agent catalog

Status: active navigation. Runtime behavior is owned by the matching files in
this directory; documentation mirrors are non-authoritative.

## Entry points

- Root contract and precedence: `AGENTS.md`
- Codex runtime map: `CODEX-RUNTIME.md`
- Risk routing and workflow: `ORCHESTRATION.md`
- Native discovery metadata: `py-*.toml`
- Role behavior: `py-*.md`
- Skill discovery/entry contracts: `.codex/skills/**`

## Active roles

| Role | Sandbox | Responsibility |
| --- | --- | --- |
| `py-audit-bot` | read-only | Audit, review, debt, reproducibility |
| `py-config-bot` | workspace-write | Config, schema, generated artifacts |
| `py-debug-bot` | read-only | Reproduction, root cause, remediation guidance |
| `py-doc-bot` | workspace-write | Docs, ADR, mirrors, diagrams |
| `py-plan-bot` | read-only | Scoped dependency-aware plans |
| `py-test-bot` | workspace-write | Test selection, evidence, test changes |

Descriptors inherit the parent model. The active catalog is derived from
`scripts/ai/codex/native_runtime_contract.py`; do not maintain a separate
literal count in downstream docs or memory.

V1/V2 work may route directly through the root agent. V3/V4 work follows the
orchestration and post-change gates. Roles never broaden user authorization.

## Editing contract

Edit canonical runtime sources first, then synchronize Codex/Junie and docs
mirrors using the repository checks. Do not change an `.env` file without
explicit per-task approval, expose secrets, or increase a technical-debt
budget, exemption, threshold, or hotspot cap.
