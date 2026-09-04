---
status: archived
class: mirror
note: Runtime snapshot only — not paste SSOT. Prefer .codex/** / .junie/** / .devin/**. Epic #8513 / #8517.
---

# CODEX-RUNTIME.md — Runtime Map For BioETL Agents

## Evaluation Metadata
- **Category:** Runtime Agentry
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** .codex/agents/CODEX-RUNTIME.md

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

# CODEX-RUNTIME.md — Runtime Map For BioETL Agents

## Canonical Sources

- Runtime contract and precedence: `AGENTS.md`
- Normative source index: `docs/00-project/NORMATIVE_SOURCES.md`
- Project rules: `docs/00-project/RULES.md`
- Requirements: `docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `docs/02-architecture/decisions/`
- Memory policy: `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

Load only the role- and risk-relevant sources selected by those contracts.

## Purpose

Map logical BioETL `py-*` profiles onto the native Codex runtime roles used in this repository.

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- Keep code, commands, file paths, identifiers, API field names, and other technical literals in their valid original form.

## Technical Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- This includes scorecard budgets, exemption limits, hotspot thresholds, hotspot family caps, and equivalent budget surfaces.

## Memory Provenance

Before invoking `python -m memory.tooling.workflow pre-task` or `post-task`,
identify the active runtime explicitly:

```bash
BIOETL_AI_RUNTIME=codex \
BIOETL_AI_AGENT=<active-profile-or-codex> \
BIOETL_AI_MODEL=<model-id-if-known> \
python -m memory.tooling.workflow <pre-task-or-post-task> ...
```

`BIOETL_AI_RUNTIME` and `BIOETL_AI_AGENT` MUST be non-empty. Set
`BIOETL_AI_MODEL` when the runtime exposes a stable model identifier; otherwise
omit it rather than guessing. Generated episodic records bind this actor
identity to repository, commit, branch, worktree, task, and source references.

## Native Project Discovery

- `.codex/config.toml` contains portable trusted-project settings only.
- `.codex/agents/py-*.toml` exposes the six governed profiles to native Codex
  custom-agent discovery. Each thin descriptor routes to its matching Markdown
  profile, skill, and memory sheet; the parent model is inherited.
- `.codex/skills/**` is the sole project-local skill discovery and behavioral
  source.
- Validate these surfaces with
  `python3 scripts/ai/codex/doctor.py static --no-write`.

## Common Task Routing

Use the smallest existing skill that matches the request:

| Request template | Mutation default | Route | Minimum validation |
| --- | --- | --- | --- |
| Diagnose without fixing | read-only | `py-debug-bot` | reproduction and evidence only |
| Implement a focused fix | write in requested scope | direct implementation; `py-config-bot` when configs change | targeted lint/tests |
| Review the current diff | read-only | `py-audit-bot` (`review`) | diff inspection; no external writes |
| Diagnose CI failure | read-only | `py-debug-bot` | reproduction, root cause, remediation guidance |
| Implement diagnosed CI remediation | write in requested scope | direct parent implementation | failed check plus targeted regression |
| Prepare a PR | branch/commit/push authorized by request | direct parent workflow | repository quality gates for touched scope |
| Audit architecture debt | read-only | `py-audit-bot` (`debt`) | architecture/debt gates; budgets MUST NOT increase |

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

- `.codex/agents/ORCHESTRATION.md`
- `.codex/agents/README.md`
- `.codex/config.toml`
- `.codex/agents/py-*.toml`
- `.codex/skills/`

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` файл без explicit per-task user approval.

## Error Recovery Strategies (для улучшения обработки ошибок)

### Runtime Failure Recovery

#### Недоступность канонических источников
```text
Если канонические источники недоступны:
1. Логируй ошибку с уровнем ERROR и контекстом
2. Продолжай с доступными источниками
3. Документируй недоступные источники
4. Предложи альтернативные процедуры
```

#### Частичная инициализация runtime
```text
При частичной инициализации runtime:
1. Логируй предупреждение с уровнем WARNING
2. Определи критические компоненты
3. Продолжай с доступными компонентами
4. Документируй ограничения
```

#### Runtime precedence conflicts
```text
При конфликтах precedence:
1. Логируй конфликт с уровнем ERROR
2. Примени канонический precedence из AGENTS.md
3. Документируй разрешение конфликта
4. Предложи clarification для future updates
```

### Error Logging с уровнями severity

```text
ERROR: Критическая ошибка, блокирующая runtime инициализацию
WARNING: Предупреждение, не блокирующее runtime инициализацию
INFO: Информационное сообщение о runtime состоянии
DEBUG: Отладочная информация для runtime troubleshooting
```

## Enhanced Guardrails (для усиления ограничений)

### Runtime Precedence Conflicts

```text
При конфликтах runtime precedence:
1. Приоритет: active runtime source > NORMATIVE_SOURCES.md > RULES.md > REQUIREMENTS.md > ADRs > docs mirrors
2. Docs mirrors не могут переопределять runtime behaviour
3. При конфликте между active runtime sources: применить explicit resolution
4. Документировать все precedence resolutions
```

### Cross-Runtime Compatibility

```text
Для cross-runtime compatibility:
1. Проверять compatibility между Codex, Junie, Devin runtime sources
2. Валидировать runtime behaviour consistency
3. Документировать runtime-specific differences
4. Предлагать mitigation для incompatibilities
```

### Runtime Source Validation

```text
Для валидации runtime sources:
1. Проверять существование всех referenced files
2. Валидировать структуру runtime configuration
3. Проверять consistency между runtime sources
4. Документировать validation results
```

### Runtime State Consistency

```text
Для runtime state consistency:
1. Проверять consistency между runtime state и canonical sources
2. Валидировать runtime state transitions
3. Проверять consistency между different runtime instances
4. Документировать state inconsistencies
```

## Runtime Validation Gates (для улучшения валидации)

### Runtime State Validation

```text
Для проверки runtime состояния:
1. Проверить runtime initialization status
2. Валидировать runtime configuration integrity
3. Проверить runtime source availability
4. Валидировать runtime precedence resolution
```

### Self-Consistency Checks

```text
Для self-consistency checks:
1. Проверить consistency между runtime configuration и canonical sources
2. Валидировать consistency между different runtime sources
3. Проверить consistency между runtime state and expected behaviour
4. Документировать inconsistencies
```

### Runtime Source Integrity Validation

```text
Для валидации runtime source integrity:
1. Проверить hash integrity для critical runtime files
2. Валидировать structure integrity для runtime directories
3. Проверить content integrity for runtime configuration
4. Документировать integrity violations
```

### Runtime Precedence Resolution Validation

```text
Для валидации precedence resolution:
1. Проверить правильность применения precedence rules
2. Валидировать consistency между precedence resolution и AGENTS.md
3. Проверить отсутствие conflicts в precedence resolution
4. Документировать precedence validation results
```
