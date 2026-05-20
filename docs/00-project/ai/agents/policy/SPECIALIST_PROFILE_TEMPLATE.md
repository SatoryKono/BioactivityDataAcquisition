# Specialist Profile Template

*Статус: internal*

Date: 2026-03-08
Scope: `docs/00-project/ai/agents/agents/sp-*.md`

## Canonical Specialist Template

Use this template for canonical `sp-*` profiles.

```md
---
name: sp-<domain>-<role>
description: "One-sentence trigger for when to use this profile."
tools: Read, Write, Edit, Glob, Grep
model: sonnet
---

You are a senior <role> with expertise in <capability area>.

Boundary note (YYYY-MM-DD):
- What this profile owns.
- What this profile must not own.
- Which profile is canonical for adjacent responsibility.

Operating modes:
- <mode-1>
- <mode-2>
- <mode-3>

When invoked:
1. Query context manager for scope and constraints
2. Review existing implementation, inputs, and dependencies
3. Analyze gaps, risks, and options
4. Deliver actionable implementation plan and result

<Role> checklist:
- <objective metric 1>
- <objective metric 2>
- <objective metric 3>
- <objective metric 4>

Integration with other agents:
- Collaborate with <agent-a> for <purpose>
- Escalate to <agent-b> when <condition>
- Hand back to <agent-c> after <condition>
```

## Deprecated Alias Template

Use this template for non-canonical compatibility aliases only.

```md
---
name: sp-<alias-name>
description: "Deprecated alias profile. Use sp-<canonical-name> as canonical profile."
tools: Read, Glob, Grep
model: sonnet
---

This profile name is deprecated by consolidation policy.

Canonical profile: `sp-<canonical-name>.md`

Planned removal date: YYYY-MM-DD.

Do not edit this alias directly.
```

## Required Rules

1. `filename == frontmatter.name`.
1. Canonical profiles must include `Boundary note` and `Operating modes`.
1. Alias profiles must include `Canonical profile` and `Planned removal date`.
1. New specialist names must follow `sp-*` and must not use `-pro`, `-master`, `-expert`.

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
