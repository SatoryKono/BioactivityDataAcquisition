______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-28'

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

- [DASHBOARD_REQUIREMENTS.md](../01-requirements/DASHBOARD_REQUIREMENTS.md) —
  scoped testable dashboard presentation contract delegated by `RULES.md`
  §3.2.3
- [rules-summary.md](rules-summary.md) — краткая выжимка RULES
- [00-map.md](00-map.md) — навигатор документации
- [architecture-index.md](architecture-index.md) — архитектурные entry points

## Precedence для AI runtime

Канонический порядок разрешения конфликтов для AI runtime живет в
[AGENTS.md](../../AGENTS.md), секция `Canonical Precedence`. Этот индекс не
ведет параллельный нумерованный список precedence. Важно: active runtime
sources — equal peers `.codex/agents/CODEX-RUNTIME.md` и
`.junie/agents/JUNIE-RUNTIME.md` (с root-контрактами `AGENTS.md` и
`.junie/guidelines.md`) — вместе с matching runtime profiles/skills
(`.codex/agents/py-*.md`, `.codex/skills/**`, `.junie/agents/py-*.md`,
`.junie/skills/**`) стоят выше этого normative index; parity между
`.codex/**` и `.junie/**` поддерживается
`scripts/ai/junie/check_junie_mirror.sh`. Docs mirrors в
`docs/00-project/ai/**` остаются navigation/guidance surfaces и не
переопределяют runtime behavior самостоятельно.

## Что читать по теме

| Тема | RULES | ADR |
| ---- | ----- | --- |
| Hexagonal / layer boundaries | §1 | ADR-005, ADR-048 |
| Medallion Bronze/Silver/Gold | §2 | ADR-002, ADR-014, ADR-018 |
| Composite pipelines | §2.9 | ADR-026 |
| DQ contracts | §2.8 | ADR-027, ADR-045 |
| Control-plane / replay | §2.4, §6.1 | ADR-044, ADR-046, ADR-047 |
| Quarantine aggregate constructor surface | §2.6 | ADR-051 |
| Infrastructure config public package root | §1, composition | ADR-052 |
| HTTP client / retry / rate limit | §4.1.1, §5.1 | ADR-032 |
| Observability | §3.2 | ADR-017, ADR-019 |
| Testing | §4.2 | ADR-042 |
| Naming / packaging | §4.4, governance | ADR-024, ADR-041 |

## Version policy

- Не полагайся на hardcoded version literals в mirrors (`AGENT.md`, agent
  profiles, skill docs).
- Для актуальной версии RULES читай header `Version:` в [RULES.md](RULES.md).
- Drift checks: `python -m scripts.docs check-drift --runtime-mirrors --freshness`


## Documentation ownership (DOC-GOV-09)

| Surface | Owner lane | Type | Retirement criterion |
| --- | --- | --- | --- |
| `docs/00-project/RULES.md` | architecture governance | normative | never without ADR/RFC |
| `docs/00-project/NORMATIVE_SOURCES.md` | architecture governance | index | update in place |
| `docs/01-requirements/REQUIREMENTS.md` | product/architecture | normative | versioned revise |
| `docs/02-architecture/decisions/**` | architecture | ADR | supersede, never silent delete |
| `docs/02-architecture/*` layer docs | architecture | architecture | re-verify or archive with banner |
| `docs/03-guides/**` | docs + domain owners | guide | merge/archive when superseded |
| `docs/04-reference/**` | domain/contracts | reference | contract-driven updates |
| `docs/05-operations/**` | ops | runbook/ops | re-verify after runtime change |
| `docs/05-engineering/**` | docs | stub | archive only; no new SSOT |
| `docs/plans/**` | planning | non-normative | one active backlog; archive rest |
| `docs/reports/**` | quality/docs | non-normative thin | bulk → `reports/docs-evidence/` |
| `docs/00-project/ai/**` | AI runtime mirrors | mirror | drift vs `.codex/**` and `.junie/**`; no behavior SSOT |
| `docs/99-archive/**` | docs | archive | retain for history |
| `docs/02-architecture/diagrams/**/*.mmd` | diagram governance | source | ADR-040 lint |
| Diagram `**/png/**` | diagram governance | render artifact | CI/local only (DOC-GOV-02) |

**KPI / gates:** `python -m scripts.docs check-kpi` (weekly workflow
`docs-kpi-weekly.yml`); `python -m scripts.docs check-drift --runtime-mirrors --freshness`.
New docs PRs SHOULD declare owner + type + retirement criterion (see
`docs/03-guides/docs-verification.md`).

## Related AI surfaces

- [AGENTS.md](../../AGENTS.md) — root AI runtime contract (Codex/Junie equal peers)
- `../../.junie/guidelines.md` — JetBrains Junie root contract (equal peer to `AGENTS.md`)
- `../../.codex/agents/CODEX-RUNTIME.md` and `../../.junie/agents/JUNIE-RUNTIME.md` — active runtime maps
- `../../scripts/ai/junie/check_junie_mirror.sh` — `.codex/**` ↔ `.junie/**` parity check
- [MEMORY_USAGE.md](ai/agents/guides/MEMORY_USAGE.md) — memory workflow
- [POST_CHANGE_VALIDATION.md](ai/agents/policy/POST_CHANGE_VALIDATION.md) — post-change protocol
- [AI_RUNTIME_MIRROR_OWNERSHIP.md](ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md) — runtime vs mirror ownership
