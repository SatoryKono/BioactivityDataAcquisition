---
status: archived
class: mirror
note: Runtime snapshot only — not paste SSOT. Prefer .codex/** / .junie/** / .devin/**. Epic #8513 / #8517.
---

# JUNIE-RUNTIME.md — Runtime Map For BioETL Agents (JetBrains Junie)

## Evaluation Metadata
- **Category:** Runtime Agentry
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** .junie/agents/JUNIE-RUNTIME.md

## Evaluation Breakdown
- Clarity: 9/10 (weight: 0.15)
- Completeness: 8/10 (weight: 0.15)
- Specificity: 8/10 (weight: 0.12)
- Context: 9/10 (weight: 0.10)
- Guardrails: 9/10 (weight: 0.10)
- Maintainability: 8/10 (weight: 0.08)
- Reusability: 7/10 (weight: 0.08)
- Error Handling: 9/10 (weight: 0.08)
- Validation: 9/10 (weight: 0.07)
- Documentation: 9/10 (weight: 0.07)

## Original Content

# JUNIE-RUNTIME.md — Runtime Map For BioETL Agents (JetBrains Junie)

This file is the JetBrains Junie equivalent of `.codex/agents/CODEX-RUNTIME.md`.
Junie and Codex are equal-peer tracked AI runtime trees for BioETL; runtime
behavior changes MUST be synchronized via
`scripts/ai/junie/check_junie_mirror.sh`.

## Canonical Sources

Read before planning or editing:

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `AGENTS.md`
- `.junie/guidelines.md`

## Purpose

Map logical BioETL `py-*` profiles onto the native JetBrains Junie runtime
roles used in this repository. Content parity with
`.codex/agents/CODEX-RUNTIME.md` is enforced by
`scripts/ai/junie/check_junie_mirror.sh --check`; the two runtime maps MUST
keep identical logical mappings, only runtime-specific labels (Codex
`default`/`worker` vs Junie-native roles) MAY differ and are declared in
`scripts/ai/junie/junie-mirror-contract.json`.

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- Keep code, commands, file paths, identifiers, API field names, and other
  technical literals in their valid original form.

## Technical Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- This includes scorecard budgets, exemption limits, hotspot thresholds, hotspot family caps, and equivalent budget surfaces.

## Memory Provenance

Before invoking `python -m memory.tooling.workflow pre-task` or `post-task`,
identify the active runtime explicitly:

```bash
BIOETL_AI_RUNTIME=junie \
BIOETL_AI_AGENT=<active-profile-or-junie> \
BIOETL_AI_MODEL=<model-id-if-known> \
python -m memory.tooling.workflow <pre-task-or-post-task> ...
```

`BIOETL_AI_RUNTIME` and `BIOETL_AI_AGENT` MUST be non-empty. Set
`BIOETL_AI_MODEL` when the runtime exposes a stable model identifier; otherwise
omit it rather than guessing. Generated episodic records bind this actor
identity to repository, commit, branch, worktree, task, and source references.

## Recommended Mapping

Junie exposes its own role vocabulary; below is the logical → Junie mapping.
The `codex_role` column mirrors `.codex/agents/CODEX-RUNTIME.md` so parity is
inspectable.

| Logical profile           | Junie role | codex_role         |
| ------------------------- | ---------- | ------------------ |
| `py-audit-bot`            | default    | default            |
| `py-architecture-debt-bot`| default    | default            |
| `py-plan-bot`             | default    | default            |
| `py-test-bot`             | default    | default or worker  |
| `py-config-bot`           | worker     | worker             |
| `py-debug-bot`            | worker     | worker             |
| `py-doc-bot`              | worker     | worker             |
| `py-test-swarm`           | default    | default            |
| `py-review-orchestrator`  | default    | default            |

## Common Task Routing

Use the smallest existing skill that matches the request:

| Request template | Mutation default | Route | Minimum validation |
| --- | --- | --- | --- |
| Diagnose without fixing | read-only | `py-debug-bot` | reproduction and evidence only |
| Implement a focused fix | write in requested scope | direct implementation; `py-config-bot` when configs change | targeted lint/tests |
| Review the current diff | read-only | `py-review-orchestrator` or `code-review` | diff inspection; no external writes |
| Investigate and fix CI | write only after root cause | GitHub CI workflow / `py-debug-bot` | failed checks plus targeted regression |
| Prepare a PR | branch/commit/push authorized by request | `create-pr` | repository quality gates for touched scope |
| Audit architecture debt | read-only | `py-architecture-debt-bot` | architecture/debt gates; budgets MUST NOT increase |

Templates do not broaden user authority. Diagnosis and review stay read-only
unless the user also asks for implementation. Load the selected skill and
relevant sources/tests; do not load every ADR or the whole repository by
default.

## Risk-Based Validation

| Tier | Typical scope | Minimum checks |
| --- | --- | --- |
| V1 | docs-only | targeted links/drift and mirror sync |
| V2 | focused Python/tooling | targeted Ruff plus related unit tests |
| V3 | config/runtime contract | schema/contract checks plus related tests |
| V4 | architecture or broad change | architecture gates, lint/type checks, and relevant broad tests |

Every closeout reports checks run, skipped checks with exact reasons/follow-up,
runtime/docs mirror status, and debt outcome (`improved`, `unchanged`, or
`worsened`). A lower tier cannot bypass an applicable architecture,
determinism, security, or technical-debt gate. `worsened` cannot be hidden by
raising a budget or exemption limit.

## Related Runtime Surfaces

- `.junie/guidelines.md` (root Junie contract)
- `.junie/agents/ORCHESTRATION.md`
- `.junie/agents/README.md`
- `.junie/skills/`
- `.codex/agents/CODEX-RUNTIME.md` (equal-peer Codex runtime map)
- `.codex/agents/ORCHESTRATION.md`
- `.codex/agents/README.md`
- `.codex/skills/`
- `scripts/ai/junie/check_junie_mirror.sh` (parity enforcement)
- `scripts/ai/junie/junie-mirror-contract.json` (parity contract)

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` файл без explicit per-task user approval.

## Error Recovery Strategies (для улучшения обработки ошибок)

### Junie-Specific Failure Recovery

#### Недоступность JetBrains IDE integration
```text
Если JetBrains IDE integration недоступна:
1. Логируй ошибку с уровнем ERROR и контекстом
2. Продолжай с доступными IDE features
3. Документируй недоступные IDE features
4. Предложи альтернативные процедуры
```

#### Частичная инициализация Junie runtime
```text
При частичной инициализации Junie runtime:
1. Логируй предупреждение с уровнем WARNING
2. Определи критические Junie components
3. Продолжай с доступными Junie components
4. Документируй ограничения
```

#### Codex–Junie parity conflicts
```text
При конфликтах Codex–Junie parity:
1. Логируй конфликт с уровнем ERROR
2. Примени parity contract из junie-mirror-contract.json
3. Документируй разрешение конфликта
4. Предложи clarification для parity updates
```

### Error Logging с уровнями severity

```text
ERROR: Критическая ошибка, блокирующая Junie runtime инициализацию
WARNING: Предупреждение, не блокирующее Junie runtime инициализацию
INFO: Информационное сообщение о Junie runtime состоянии
DEBUG: Отладочная информация для Junie runtime troubleshooting
```

## Enhanced Guardrails (для усиления ограничений)

### Codex–Junie Parity Contract

```text
Для Codex–Junie parity contract:
1. Проверять parity между Codex и Junie runtime sources
2. Валидировать parity через check_junie_mirror.sh
3. Документировать parity violations
4. Предлагать mitigation для parity issues
```

### Junie-Specific Features

```text
Для Junie-specific features:
1. Проверять compatibility с Codex runtime
2. Валидировать Junie-specific behaviour consistency
3. Документировать Junie-specific differences
4. Предлагать mitigation for incompatibilities
```

### Junie State Consistency

```text
Для Junie state consistency:
1. Проверять consistency между Junie state и canonical sources
2. Валидировать Junie state transitions
3. Проверять consistency между Junie and Codex runtime states
4. Документировать state inconsistencies
```

### Junie–Codex Synchronization

```text
Для Junie–Codex synchronization:
1. Проверять synchronization status через parity contract
2. Валидировать synchronization completeness
3. Проверить synchronization consistency
4. Документировать synchronization issues
```

## Junie Validation Gates (для улучшения валидации)

### Junie Runtime State Validation

```text
Для проверки Junie runtime состояния:
1. Проверить Junie runtime initialization status
2. Валидировать Junie runtime configuration integrity
3. Проверить Junie runtime source availability
4. Валидировать Junie runtime precedence resolution
```

### Self-Consistency Checks

```text
Для self-consistency checks:
1. Проверить consistency между Junie runtime configuration и canonical sources
2. Валидировать consistency between Junie and Codex runtime sources
3. Проверить consistency between Junie runtime state and expected behaviour
4. Документировать inconsistencies
```

### Junie–Codex Mirror Parity Validation

```text
Для валидации Junie–Codex mirror parity:
1. Проверить parity через check_junie_mirror.sh
2. Валидировать parity contract compliance
3. Проверить parity consistency across all runtime sources
4. Документировать parity violations
```

### Junie State Integrity Validation

```text
Для валидации Junie state integrity:
1. Проверить hash integrity для critical Junie runtime files
2. Валидировать structure integrity для Junie runtime directories
3. Проверить content integrity for Junie runtime configuration
4. Документировать integrity violations
```
