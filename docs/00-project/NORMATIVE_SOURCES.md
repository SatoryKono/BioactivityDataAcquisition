______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-16'

______________________________________________________________________

# BioETL Normative Sources Index

Единая входная точка к полному нормативному стеку проекта. AI-инструкции,
contributor guides и runtime profiles **MUST** ссылаться на этот индекс вместо
дублирования правил.

## Полный нормативный стек

BioETL не использует один монолитный файл «всех правил». Полный свод образуют
три обязательных слоя:

| Слой | Файл | Назначение |
| ---- | ---- | ---------- |
| Constitution | [RULES.md](RULES.md) | Архитектура, Medallion, DQ, composite, API/retry, determinism, observability, testing, naming, governance (RFC 2119) |
| Decisions | [decisions/](../02-architecture/decisions/) | Accepted ADR — точечные архитектурные решения |

Дополнительные индексы (не заменяют RULES):

- [rules-summary.md](rules-summary.md) — краткая выжимка RULES
- [00-map.md](00-map.md) — навигатор документации
- [architecture-index.md](architecture-index.md) — архитектурные entry points

## Precedence для AI runtime

Канонический порядок разрешения конфликтов для AI runtime живет в
[AGENTS.md](../../AGENTS.md), секция `Canonical Precedence`. Этот индекс не
ведет параллельный нумерованный список precedence. Важно: active runtime source
и matching runtime profiles/skills стоят выше этого normative index; docs
mirrors в `docs/00-project/ai/**` остаются navigation/guidance surfaces и не
переопределяют runtime behavior самостоятельно.

## Что читать по теме

| Тема | RULES | ADR |
| ---- | ----- | --- |
| Hexagonal / layer boundaries | §1 | ADR-005, ADR-048 |
| Medallion Bronze/Silver/Gold | §2 | ADR-002, ADR-014, ADR-018 |
| Composite pipelines | §2.9 | ADR-026 |
| DQ contracts | §2.8 | ADR-027, ADR-045 |
| Control-plane / replay | §2.4, §6.1 | ADR-044, ADR-046, ADR-047 |
| HTTP client / retry / rate limit | §4.1.1, §5.1 | ADR-032 |
| Observability | §3.2 | ADR-017, ADR-019 |
| Testing | §4.2 | ADR-042 |
| Naming / packaging | §4.4, governance | ADR-024, ADR-041 |

## Version policy

- Не полагайся на hardcoded version literals в mirrors (`AGENT.md`, agent
  profiles, skill docs).
- Для актуальной версии RULES читай header `Version:` в [RULES.md](RULES.md).
- Drift checks: `python -m scripts.docs check-drift --runtime-mirrors --freshness`

## Related AI surfaces

- [AGENTS.md](../../AGENTS.md) — root AI runtime contract
- [MEMORY_USAGE.md](ai/agents/guides/MEMORY_USAGE.md) — memory workflow
- [POST_CHANGE_VALIDATION.md](ai/agents/policy/POST_CHANGE_VALIDATION.md) — post-change protocol
- [AI_RUNTIME_MIRROR_OWNERSHIP.md](ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md) — runtime vs mirror ownership
