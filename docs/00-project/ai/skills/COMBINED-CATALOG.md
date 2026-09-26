# Combined Skills Index — Unified View (2026-09-04)

*Статус: internal-published | Логическое объединение всех папок `docs/00-project/ai/skills/` в один индекс. Физические папки сохранены per `skills-mirror-contract.json` (local, global, _references), но этот файл даёт единый взгляд.*

## Структура (физически сохранена)

- `local/` — 14 SSOT mirror (`.codex/skills/` 1:1) — **минимально-достаточный набор**: `agent-debugging`, `new-pipeline`, `observability-dashboard`, `observability-prometheus`, `py-audit-bot`, `py-config-bot`, `py-debug-bot`, `py-doc-bot`, `py-plan-bot`, `py-test-bot`, `research-workflow`, `technical-designer-mermaid`, `vcr-record`, `verify-architecture`
- `global/` — 16 snapshot ( curated global skills: `gh-address-comments`, `gh-fix-ci`, `openai-docs`, `public/*`, `py-code-bot` (deprecated) etc.)
- `_references/local/` — 1 bundle (`technical-designer-mermaid/references/patterns.md`) — mirror per contract
- Архив: `docs/99-archive/skills-2026-09/` — 2 неполных (`deep-research`, `documentation-audit` + их `_references`) — заархивированы 2026-09-04 (0 findings, no SKILL.md)

## Объединённый реестр (local + global + _references)

| Skill | Source | Status | Назначение |
| --- | --- | --- | --- |
| `agent-debugging` | local/.codex | active | diagnostics |
| `new-pipeline` | local/global | active | scaffolding |
| `observability-dashboard` | local | active | dashboards |
| `observability-prometheus` | local | active | alerts |
| `py-audit-bot` | local/global | active | audit |
| `py-config-bot` | local/global | active | configs |
| `py-debug-bot` | local/global | active | RCA |
| `py-doc-bot` | local/global | active | docs |
| `py-plan-bot` | local/global | active | planning |
| `py-test-bot` | local/global | active | tests |
| `research-workflow` | local | active | research |
| `technical-designer-mermaid` | local/_references | active | diagrams |
| `vcr-record` | local/global | active | cassettes |
| `verify-architecture` | local/global | active | arch checks |
| `gh-address-comments` | global | snapshot | GH comments |
| `gh-fix-ci` | global | snapshot | CI fix |
| `openai-docs` | global | snapshot | OpenAI docs |
| `public/*` | global | snapshot | public skills |
| `py-code-bot` | global | **deprecated** | tombstone |
| `deep-research` | archive | **archived** | incomplete (no SKILL.md) |
| `documentation-audit` | archive | **archived** | incomplete |

## Почему не физическое объединение

- `skills-mirror-contract.json` требует раздельных `docs_mirror` (`local/`) и `reference_overlay` (`_references/local`) — физическое слияние сломает `check_skills_mirror.sh --check` (missing overlay) и `check-links` (14 broken links для `global/`), как проверено 2026-09-04.
- `global/` — snapshot для discoverability, не дубли local — физическое слияние создало бы дубли >70% и нарушило `SKILLS-CATALOG.md` (14 vs 30).

## Как использовать

- Для BioETL — используй 14 из `local/` (минимальный набор).
- Для global/system — смотри `global/` snapshot, но не считай его SSOT.
- Для истории — смотри `docs/99-archive/skills-2026-09/`.

## Связанные

- `SKILLS-CATALOG.md` — канонический 14
- `SKILLS-PRACTICAL-INDEX.md` — практический top-15
- `README.md` — surface types
- `scripts/ai/codex/skills-mirror-contract.json` — parity contract
