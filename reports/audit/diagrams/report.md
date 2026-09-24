# Diagrams audit

| Field | Value |
| --- | --- |
| Prompt | `prompt.audit.diagrams` v1.2.0 |
| SCOPE | docs diagrams + related scripts |
| MODE | `propose-patches` (патчи **не** применялись) |
| LANGUAGE | ru |
| AUDIT_MODE | full |
| `REQUIRE_GH_TRACKING` | true |
| Base | worktree `73e76c20c0df`; `origin/main` tip `2348b89f6a11` (gitignore/registry only, не диаграммы) |
| `surface_score` | **2** / 3 |
| Open PROVEN | **3** (все P3) |
| Confirmed secret | **нет** |

## Executive summary

Канон — text-as-code Mermaid (`.mmd` / views `.mermaid`), рендер SVG в git, PNG **намеренно gitignored**. CI: pinned `@mermaid-js/mermaid-cli@10.6.1` через `npm ci` + lockfile, **без** `npx -y`. Lint 492 файла, **0 ERROR**. C4 current-state описывает процессы, не Docker; observability optional (ADR-010). PlantUML/drawio/dot в `docs/` нет.

Отстаёт документация масштаба (ADR-040 всё ещё «290 `.mmd`») и метаданные `@nodes` на 35 файлах; штамп `current-state-diagrams.md` 2026-08-05. Это не ломает security/deploy модель.

| Check | Result |
| --- | --- |
| Inventory | 328 `.mmd`, 165 `.mermaid`, 492 SVG, 0 tracked PNG, 0 puml/drawio |
| ADR-040 baseline | mmd 290 vs live **328**; views 165 = 165 |
| `lint_diagrams.py docs/02-architecture/diagrams --json` | exit 0; 0 failed; 168 WARNING |
| `check-artifacts` visual-smoke (6 SVG) | exit 0 |
| setup-mermaid | pin 10.6.1, refuse other versions |
| `npx -y` in `scripts/diagrams` / `.github` | не найдено |
| local `mmdc` | отсутствует (smoke рендер не гонялся локально) |
| Embedded ` ```mermaid ` in `docs/**` (ex archive) | 88 fences; current-state помечен `diagram-audit:summary-only` |

## Surface score

**2** — источники в VCS, CI lint/artifacts зелёные, модель C4/слоёв согласована с кодом; регенерация PNG и полный render остаются ручными/nightly, ADR census и `@nodes` не доведены.

Не 3: нет полного tracked PNG, visual-smoke узкий (6 SVG), ADR-040 baseline устарел. Не 1: не binary-only, CI есть. Не 0: ключевые C4/observability не толкают к плохому deploy.

## Findings

### DIAG-ADR040-CENSUS — P3 PROVEN

ADR-040 «measured baseline 2026-07-18»: 290 `.mmd` (architecture 89 + class 145 + foundation 55 + template). Live: **328** = то же + `providers/` 28 + `sequence/` 5 + `state-machines/` 5.

**Patch (не применён):** обновить числа/семьи в ADR-040; не поднимать quality budgets. Issue #10983.

### DIAG-META-NODES — P3 PROVEN

ADR-040 D4 требует `%% @nodes` на `.mmd`. Нет на 35 файлах: architecture `24`–`48`, все `sequence/`, все `state-machines/`. Lint не падает (ELK/`SIZE` смотрят `@nodes` только если он есть).

**Patch:** проставить `@nodes` (посчитать узлы) без смены семантики. Issue #10984.

### DIAG-CURRENT-STATE-STAMP — P3 PROVEN

`docs/02-architecture/current-state-diagrams.md` `Last verified: 2026-08-05`. Сами C4 Context/Container и слои **согласованы** с ADR-010 (optional Grafana, container = процесс). Это stamp-drift, не wrong model.

**Patch:** обновить `Last verified` после сверки (уже сделана этим аудитом). Issue #10985.

## Lint warnings (не отдельные issues)

168 WARNING: SIZE-002×97, STALE-002×24 (>90d), LINK-001×22, LABEL-001×20, SIZE-003×3, CLASS-003×2. ERROR=0. Не GH, пока не ERROR.

## Canonical source map

См. `canonical-source-map.md`. Рендер: `docs/02-architecture/diagrams/tooling/render.sh` / `make render-diagrams`; CI `docs.yml` + `diagram-nightly.yml` + `.github/actions/setup-mermaid`.

PNG: `.gitignore` `docs/02-architecture/diagrams/**/png/` — не finding (анти-pattern «huge binary churn»).

## Proposed patches

Только с явным «приступай». Порядок: ADR census → `@nodes` → Last verified. Без mass PNG commit. Full-repo class dump `90-pkg-*` уже generated-from-code — не расширять до monorepo god-diagram.

## Skips

- Полный локальный `mmdc` render / `git diff` SVG (нет CLI; политика CI path-filter).
- `lint-budget` без JSON input (CI передаёт lint JSON).
- Docker/monitoring stack не поднимался.

## Residual risk

STALE-002 станет STALE-001 ERROR после 150 дней. Visual-smoke не покрывает 328 источников.
