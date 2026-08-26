# Audit diagrams — `prompt.audit.diagrams`

| Field | Value |
| --- | --- |
| domain_id | `diagrams` |
| prompt_id | `prompt.audit.diagrams` |
| version | 1.2.0 |
| MODE | `audit` |
| AUDIT_MODE | `full` |
| LANGUAGE | `ru` |
| REQUIRE_GH_TRACKING | `false` |
| SCOPE | `docs/02-architecture/diagrams/` · `scripts/diagrams/` |
| surface_score | **2** / 3 |
| blocked | `false` |
| debt_outcome | `unchanged` (бюджеты не трогались) |
| generated_at | 2026-08-26 |

Легенда surface_score (kit + `fragments/audit-scale.md`): **3** = text source в VCS, детерминированный pinned render, CI validation, модель совпадает с системой; **2** = диаграммы в целом актуальны, часть regenerate/review ещё ручная; **1** = binary-only / регулярный drift; **0** = ключевая схема достаточно неверна, чтобы сломать security/deploy.

Оценка **2**: канонические `.mmd`/`.mermaid` в git, SVG sibling contract закрыт тестами, Mermaid CLI **10.6.1** pin в `.github/actions/setup-mermaid` + `mmdc_wrapper.sh`, CI lint/render/drift есть. До 3 не дотягивает из‑за stale generated `90-pkg-*`, skill-пути `mmd-diagrams/`, дыр pre-commit и локальных неточностей модели (Grafana, dual 13a, unlabeled security nodes).

## Executive summary

Корпус diagrams — инженерный text-as-code набор с ADR-040 lint, pinned render и PR SVG-drift gate. PNG после DOC-GOV-02 gitignored (правильно в `.gitignore` / `render-retention.md`). Живой lint/render в этой сессии **не запускался** (нет shell tool); выводы по STALE/SIZE сделаны из исходников + кода линтера.

P0 нет. P1: skill всё ещё учит писать в `mmd-diagrams/`; generated `90-pkg-*` старше 150 дней и без CI `--check`.

## Inventory (measured this checkout)

| Family | Sources | Sibling SVG | Class | Notes |
| --- | ---: | ---: | --- | --- |
| `architecture/*.mmd` | 89 | 89 | container/component/sequence/data | Core ADR-040 tree |
| `class-diagrams/*.mmd` | 94 | 94 | class | 19 curated + sandbox + 74 `90-pkg-*` |
| `foundation/*.mmd` | 55 | 55 | mixed historical | TOP-25 + class/sequence |
| `views/*.mermaid` | 165 | 165 | decomposed views | `-full/-overview/-domain/-infra/-dataflow` |
| `providers/**/*.mmd` | 28 | 28 | data/API | 7 providers × 4 flows |
| `sequence/*.mmd` | 5 | 5 | sequence | issue #6544 |
| `state-machines/*.mmd` | 5 | 5 | state | issue #6546 |
| `_template.mmd` | 1 | n/a | template | excluded from lint (`_` prefix) |
| **Total sources** | **442** | **441 SVG** | | Guide still says 404 (DIAG-011) |

Другие форматы в SCOPE: PlantUML / Graphviz / drawio **не найдены**. PNG sibling trees gitignored. Bundles `diagrams/bundles/*.{md,pdf,docx}` — publication artifacts. Embedded Mermaid вне SCOPE живёт в `docs/02-architecture/current-state-diagrams.md` (compact current-state, не SSOT).

Канонический source map: `canonical-source-map.md`. CSV: `diagram-inventory.csv`, `diagram-code-drift.csv`. Render: `render-failures.txt` (live skip).

## Tooling / CI (pinned)

| Surface | Evidence |
| --- | --- |
| Entry | `python -m scripts.diagrams` (`scripts/diagrams/__main__.py`) |
| Lint | `lint/lint_diagrams.py` — SIZE/META/COLOUR/GRAPH/STALE/NBSP; exit 1 on ERROR |
| Budget | `lint/enforce_diagram_quality_budget.py`; nightly `--max-lint-errors 0` |
| Render | `docs/02-architecture/diagrams/tooling/render.sh` + `mmdc_wrapper.sh` (`minlag/mermaid-cli:10.6.1`, `MMDC_REQUIRED_VERSION=10.6.1`) |
| CI pin | `.github/actions/setup-mermaid` `npm ci` from lockfile; refuses unlocked version |
| PR | `.github/workflows/docs.yml` validate-mermaid, render-diagrams, check-diagram-drift (SVG) |
| Nightly | `.github/workflows/diagram-nightly.yml` render + artifacts + STALE-001 issue + budget |
| Dataflow gate | `docs.yml` `generate-dataflows --pipeline chembl_activity --check` |
| Tests | `tests/architecture/test_diagram_corpus_regression_guards.py` sibling SVG; no `mmd-diagrams` sources |
| Pre-commit | lint + prune-orphans for architecture/foundation/class-diagrams + views only (DIAG-007) |
| `npx -y` in diagram CI | **не найден** (антипаттерн kit закрыт на этом контуре) |

`scripts/diagrams/core/diagram_paths.py` и `diagram_paths.sh` умеют fallback на `mmd-diagrams/`, но выбирают `diagrams/` если каталог существует — для текущего checkout это безопасно.

## Accuracy / model

- Local-only deploy: `foundation/12-local-deployment-architecture.mmd` — CLI, MemoryLock, local `data/`, без Docker/Redis. Совпадает с ADR-010.
- Observability 22 помечает Grafana как optional; 09/09b — нет (DIAG-006).
- Security 17: unlabeled `HASHED`/`BW`/`SW` (DIAG-005).
- Hexagonal 01: лишний Interfaces-узел `ORCH` (DIAG-014).
- Dual 13a/13b/13c decompositions (DIAG-004).
- Секреты/внутренние URL на диаграммах не найдены (`api_key`/`token` — поля адаптеров и rate-limit, не значения).

## Findings (15 PROVEN)

| ID | P | Status | Path | One-liner |
| --- | --- | --- | --- | --- |
| DIAG-001 | P1 | PROVEN | `.codex/skills/technical-designer-mermaid/SKILL.md:72` | Skill канонит `mmd-diagrams/` |
| DIAG-002 | P1 | PROVEN | `class-diagrams/90-pkg-interfaces-http.mmd:6` | `90-pkg-*` STALE-001, generator `--check` не в CI |
| DIAG-003 | P2 | PROVEN | `diagrams/README.md:35` | README: PNG tracked vs gitignore |
| DIAG-004 | P2 | PROVEN | `architecture/13a-data-storage-ports.mmd` | Две схемы декомпозиции 13a/b/c |
| DIAG-005 | P2 | PROVEN | `architecture/17-security-pii-audit.mmd:38` | Unlabeled HASHED/BW/SW |
| DIAG-006 | P2 | PROVEN | `architecture/09-observability-stack.mmd:72` | Grafana без optional |
| DIAG-007 | P2 | PROVEN | `.pre-commit-config.yaml:234` | Нет sequence/providers/state-machines |
| DIAG-008 | P2 | PROVEN | `architecture/13-port-protocol-contracts.mmd:5` | @date 2026-03-28 → STALE-001 |
| DIAG-009 | P3 | PROVEN | `views/00-legend.mermaid:5` | COLOUR-002 ≠ ADR-040 emoji ban |
| DIAG-010 | P3 | PROVEN | `foundation/12-local-deployment-architecture.mmd:70` | Silver fill #f1f5f9 |
| DIAG-011 | P3 | PROVEN | `governance/DIAGRAM-WORKFLOW-GUIDE.md:20` | 404 vs 442 sources |
| DIAG-012 | P3 | PROVEN | `.github/workflows/docs.yml:506` | Мёртвый png glob в drift |
| DIAG-013 | P3 | PROVEN | `scripts/diagrams/fix_mermaid_operators.py` | Дубль fixer |
| DIAG-014 | P3 | PROVEN | `architecture/01-high-level-hexagonal.mmd:44` | ORCH не package interfaces |
| DIAG-015 | P3 | PROVEN | `class-diagrams/07-…-frontmatter-sandbox.mmd` | Эксперимент в каноническом дереве |

Полные поля: `findings.json`.

## Top remediations

1. Починить skill path `mmd-diagrams/` → `diagrams/` в `.codex` и синхронизировать `.junie` (`check_junie_mirror.sh --check`).
2. Прогнать `generate_package_family_class_diagrams.py` и добавить `--check` в `docs.yml` рядом с `generate-dataflows`.
3. Не поднимать `ERROR_STALE_DAYS` / lint-budget; обновить `@date` только после review содержимого.
4. Свести семейство 13* к одной нумерации; подписать узлы в 17-security.
5. Выровнять README PNG с DOC-GOV-02; расширить pre-commit glob.
6. Пометить Grafana optional в 09/09b как в 22.

## Skipped / NOT_PROVEN checks

| Check | Why skipped |
| --- | --- |
| `python -m memory.tooling.workflow pre-task/post-task` | Нет shell tool в этой сессии |
| `python -m scripts.diagrams lint` / `lint-budget` | Нет shell; STALE-001 выведен статически |
| `bash …/tooling/render.sh` / visual-smoke / check-artifacts | Нет shell; SVG наличие подтверждено list_dir + architecture tests (код), не live render |
| `git status` / SHA | Нет shell |
| Nightly job result on origin | `REQUIRE_GH_TRACKING=false`; статус nightly **NOT_PROVEN** |
| AST drift каждой `90-pkg` vs `src/bioetl` | Без `--check` run; доказан только stale date + отсутствие CI gate |
| fa:fa- icon render in mermaid-cli 10.6.1 | Присутствие иконок PROVEN; визуальный fail **NOT_PROVEN** |

`.env` не читался и не менялся. Техдолг-бюджеты не менялись.

## Guardrails

- MODE=audit: патчи не предлагались к применению.
- Root scratch не создавался.
- Runtime mirrors не редактировались.
