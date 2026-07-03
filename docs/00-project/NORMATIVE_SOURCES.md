______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-03'

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
| Requirements | [REQUIREMENTS.md](../01-requirements/REQUIREMENTS.md) | Тестируемые `REQ-*` требования, синхронизированные с RULES |
| Decisions | [decisions/](../02-architecture/decisions/) | Accepted ADR — точечные архитектурные решения |

Дополнительные индексы (не заменяют RULES):

- [rules-summary.md](rules-summary.md) — краткая выжимка RULES
- [00-map.md](00-map.md) — навигатор документации
- [architecture-index.md](architecture-index.md) — архитектурные entry points

## Precedence для AI runtime

При конфликте инструкций используй порядок из [AGENTS.md](../../AGENTS.md):

1. active runtime source (`.codex/**`, tracked `.gemini/**` when present)
1. [RULES.md](RULES.md)
1. [REQUIREMENTS.md](../01-requirements/REQUIREMENTS.md)
1. accepted ADRs in [decisions/](../02-architecture/decisions/)
1. docs mirrors in `docs/00-project/ai/**` (navigation only)

## Что читать по теме

| Тема | RULES | REQUIREMENTS | ADR |
| ---- | ----- | ------------ | --- |
| Hexagonal / layer boundaries | §1 | REQ-ARCH-* | ADR-005, ADR-048 |
| Medallion Bronze/Silver/Gold | §2 | REQ-DATA-* | ADR-002, ADR-014, ADR-018 |
| Composite pipelines | §2.9 | REQ-COMP-* | ADR-026 |
| DQ contracts | §2.8 | REQ-DQ-* | ADR-027, ADR-045 |
| Control-plane / replay | §2.4, §6.1 | REQ-CTRL-* | ADR-044, ADR-046, ADR-047 |
| HTTP client / retry / rate limit | §4.1.1, §5.1 | REQ-API-* | ADR-032 |
| Observability | §3.2 | REQ-OBS-* | ADR-017, ADR-019 |
| Testing | §4.2 | REQ-TEST-* | ADR-042 |
| Naming / packaging | §4.4, governance | REQ-NAMING-* | ADR-024, ADR-041 |

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
