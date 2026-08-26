# Аудит diagrams

| Поле | Значение |
| --- | --- |
| domain_id | diagrams |
| prompt_id | prompt.audit.diagrams |
| MODE | audit |
| AUDIT_MODE | full |
| LANGUAGE | ru |
| SCOPE | `docs/02-architecture/diagrams/` + `scripts/diagrams/` |
| surface_score | **2** / 3 |
| blocked | false |
| REQUIRE_GH_TRACKING | false |
| Дата | 2026-08-26 |
| Debt outcome | unchanged (только аудит, бюджеты не трогались, `.env` не трогался) |

## Executive summary

Канонический контур диаграмм BioETL в целом зрелый: text-as-code (`.mmd` / `.mermaid`) в VCS, pinned `@mermaid-js/mermaid-cli@10.6.1` через lockfile `npm ci` (без `npx -y` в diagram CI), SVG как publication baseline, PNG gitignored (DOC-GOV-02), lint/render/nightly budget, corpus regression tests на 89/145/55/290/165.

Score не 3, потому что модель на ключевых схемах расходится с кодом/политикой, а derived publication (INDEX/bundle) ссылается на переименованные stems. Это не «бинарный SSOT» и не сломанный рендер, но достаточный drift, чтобы не ставить полный контроль.

P0 нет: local-only / отсутствие Redis/Docker на диаграммах соблюдено; секретов на схемах нет (`api_key` — имена полей).

## Surface score

| Score | Критерий карточки | Факт |
| ---: | --- | --- |
| 3 | Text source + deterministic render + CI + model matches system | Источник и CI есть; **model не полностью matches** |
| **2** | Diagrams current; часть regeneration/review ручная | **Выбрано**: ядро верно, INDEX/bundle и часть labels требуют ручного refresh |
| 1 | Binary-only / unclear source / regular drift | Не применимо: `.mmd` SSOT, PNG не tracked |
| 0 | Key diagram wrong enough for bad security/deploy | Не применимо: local-only не перевёрнут; Gold/Parquet — P1 storage, не P0 security |

## Inventory

| Коллекция | Источники | SVG sibling (list_dir) | Класс |
| --- | ---: | ---: | --- |
| architecture | 89 `.mmd` | 89 | component / data |
| class-diagrams | 145 `.mmd` (curated + `90-pkg-*` ≤30 nodes) | 145 | class |
| foundation | 55 `.mmd` | 55 | context / deploy |
| views | 165 `.mermaid` | 165 | view |
| sequence | 5 | 5 | sequence |
| state-machines | 5 | 5 | state |
| providers | 28 (7×4) | 28 | data |
| template | 1 `_template.mmd` | n/a | — |
| PlantUML / drawio / Graphviz в SCOPE | 0 | — | retired |

Совпадает с ADR-040 / `test_governance_docs_match_active_diagram_counts`. C4: context (`foundation/01`, `12-local-deployment`), container (`architecture/01-*`), component (`13*`, `05*`), data (`03*`, `49-52*`, providers), sequence/state, class slices — не один code-level dump монорепо.

## Что работает

- Entrypoint `python -m scripts.diagrams` (`lint`, `lint-budget`, `checks`, `check-artifacts`, `check-visual-smoke`, `nightly`).
- Pin 10.6.1: `.github/actions/setup-mermaid/package.json`, отказ unlocked version, Docker `minlag/mermaid-cli:10.6.1`.
- PR `docs.yml`: syntax, lint, render, visual-smoke, quality-gates, `generate-dataflows --check`, package-family `--check`.
- Nightly: render + `--require-png` compatibility + budget `--max-lint-errors 0` + STALE-001 issue.
- PNG `/docs/02-architecture/diagrams/**/png/` в `.gitignore`.
- Medallion canonical `architecture/03-medallion-data-flow.mmd` показывает Gold как Delta Lake (в отличие от foundation/12).
- `90-pkg-*` режутся на slices (`@nodes 30`), не один huge class dump.

## Findings (PROVEN, max 12)

| ID | P | Суть |
| --- | --- | --- |
| DIAG-001 | P1 | `foundation/12-local-deployment`: Gold «Delta/Parquet», quarantine/lineage «Parquet» vs Delta + JSONL |
| DIAG-002 | P1 | INDEX/bundle/descriptions ссылаются на отсутствующие `13a/13b/13c-port-contracts-*.svg`; live = `13g/13h/13i` |
| DIAG-003 | P2 | `13g` адаптеры PA/UA/CRA/OAA/SSA/PCA без подписей |
| DIAG-004 | P2 | `17-security` HASHED/BW/SW без node declarations |
| DIAG-005 | P2 | drift gate + pre-commit не покрывают sequence/state-machines/providers |
| DIAG-006 | P2 | `09-observability` Grafana не optional |
| DIAG-007 | P2 | smoke baseline `foundation/01-full-system-component` Updated 2026-03-28 → STALE-001 (151d) |
| DIAG-008 | P2 | README «48 core», нет 49–52 chembl dataflow |
| DIAG-009 | P3 | cheatsheet `diagram_lint` — несуществующие команды |
| DIAG-010 | P3 | `policy.md` last verified 2026-03-29 / hex case vs ADR-040 |
| DIAG-011 | P3 | PR lint hint «update diagram budget»; lint-budget только nightly |
| DIAG-012 | P3 | `13h` SVG показывает голые id SW/GW/NOMW при подписанном .mmd |

Полные поля: `findings.json`.

## Top remediations

1. Исправить подписи storage на `foundation/12-local-deployment-architecture.mmd` (Gold Delta-only, quarantine Delta, lineage JSONL).
2. Перегенерировать `architecture/svg/INDEX.md`, `bundles/architecture.bundle.md`, description cards под stems `13g/13h/13i`.
3. Подписать адаптеры в `13g-port-contracts-data-sources.mmd`; развязать chained edges в `13h`.
4. Дописать HASHED/BronzeWriter/SilverWriter в `17-security-pii-audit.mmd`.
5. Расширить `check-diagram-drift` и pre-commit regex на `sequence/`, `state-machines/`, `providers/`.
6. Пометить Prometheus/Grafana как optional на `09-observability-stack.mmd`.
7. Re-verify + bump `%% Updated:` у smoke baseline и остальных `@date 2026-03-28` **без** увеличения `ERROR_STALE_DAYS`.
8. Добавить 49–52 в README; починить cheatsheet; убрать «update the accepted diagram budget» из `docs.yml`.

## Skipped / NOT_PROVEN

В этой сессии нет shell-инструмента. Не запускались:

- `python -m scripts.diagrams lint|lint-budget|check-artifacts|check-visual-smoke|check-quality-gates`
- `generate-dataflows --check`
- `render.sh` (намеренно: пишет product SVG/PNG)
- memory `pre-task` / `post-task`

Текущий lint error_count поэтому **не утверждается**. STALE-001 для `01-full-system-component` выведен из даты и константы 150d, не из JSON lint-отчёта.

Секреты на диаграммах не найдены. `npx -y` в diagram CI нет.

## Guardrails

- Техдолг-бюджеты не повышались.
- `.env` не создавался и не менялся.
- Product code / `.mmd` не редактировались (MODE=audit).
- Артефакты только под `reports/audit/diagrams/`.
