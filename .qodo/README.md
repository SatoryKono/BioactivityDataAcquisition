# Qodo governance source of truth

Qodo agent guidance, review configuration, and compliance workflows are
maintained under `/.qodo/`. The former repository-root files
(`.pr_agent.toml`, `best_practices.md`, and `pr_compliance_checklist.yaml`)
were consolidated here so the configuration has one tracked source of truth.

Do not recreate duplicate Qodo policy files at the repository root. Changes to
architecture, security, secret handling, or technical-debt guardrails must be
made in the files under this directory and reviewed together with `AGENTS.md`
and the normative project sources.

The `workflows/` copy is the workflow-facing entrypoint; policy content must
remain equivalent to the canonical files in this directory.
