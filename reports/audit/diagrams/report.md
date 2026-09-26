# Аудит домена diagrams

| Поле | Значение |
| --- | --- |
| `domain_id` | `diagrams` |
| `prompt_id` | `prompt.audit.diagrams` |
| `run_id` | `20260926T084327Z-e1c184857e46-nine` |
| Baseline | `origin/main` @ `e1c184857e46` |
| Worktree | `.worktrees/nine-domain-audit-9f71c6444175` |
| MODE | read-only audit |
| Дата | 2026-09-26 |

## surface_score: **2** / 3

**Легенда:** 3 — текстовый источник в VCS, детерминированный render, CI, модель совпадает с системой; 2 — актуальные диаграммы, часть регрессии/регенерации вручную; 1 — drift или неясный источник; 0 — опасная ошибка deploy/security.

### Краткий вывод

Корпус диаграмм инженерно зрелый: **329** `.mmd`, **165** `.mermaid`, **493** tracked SVG, канон в `docs/02-architecture/diagrams/`, рендер через `render.sh` + `mmdc_wrapper.sh` с pin **10.6.1** и lockfile-backed `setup-mermaid`. На PR работают syntax validation, incremental lint, drift gate для изменённых источников и точечный render dataflow ChEMBL.

Главный разрыв — **автоматизация Phase 2**: job `render-diagrams` в `docs.yml` и `diagram-nightly.yml` отключены (`if: false`, #11196), поэтому DIAG-T013/T018–T023/T026 и extended visual smoke **не выполняются в CI**, хотя regression plan и README tooling описывают их как PR/nightly hard gates. Regression pool покрывает **6** SVG (`visual-smoke.txt`) при ~**494** lint-файлах.

Локальный lint (`python -m scripts.diagrams lint docs/02-architecture/diagrams`): **493** файлов, **0** ERROR, **24** STALE-002 (>90d), **27** LINK-001, **100** SIZE-002 (warnings).

`blocked`: **false** (нет PROVEN P0/P1).

## Инвентарь (SCOPE)

| Метрика | Значение |
| --- | --- |
| `.mmd` | 329 |
| `.mermaid` | 165 |
| `.svg` (tracked) | 493 |
| `.png` (tracked) | 0 (DOC-GOV-02 / gitignore) |
| `.md` (derived/index) | 394 |
| `scripts/diagrams/**` | 48 файлов |
| DrawIO / binary-only | не найдено |

## Сильные стороны

- ADR-040 governance, manifests, pre-commit `lint-diagrams` / orphan checks.
- Pinned Mermaid CLI; отказ от `npx -y` в `scripts/diagrams/**`.
- PR `check-diagram-drift`: re-render изменённых `.mmd` и `git diff --exit-code` sibling SVG.
- Architecture tests на diagram workflows и quality gate scripts.

## Top remediations

1. Явно пересмотреть SSOT `diagram-regression-test-plan.md` vs фактический CI (#11196): пометить DIAG-T013/T018–T026 как manual/local или восстановить budgeted job (workflow_dispatch / path-scoped).
2. Периодически гонять `scripts/diagrams/run_diagram_checks.sh --profile pr` локально или в dispatch job; расширить `visual-smoke.txt` по приоритету архитектурных семейств.
3. Обновить `@date` / описания для кластера architecture **24–31** (24× STALE-002) или подтвердить актуальность содержимого.
4. Синхронизировать `scripts/diagrams/README.md` и `docs/02-architecture/diagrams/README.md` (Last verified **2026-07-28**) с текущими CI gates.
5. Закрыть LINK-001 на observability / bootstrap / reproducible-run семействах (semantic arrow mix).

## Выполненные проверки

| Проверка | Результат |
| --- | --- |
| `python -m scripts.diagrams lint docs/02-architecture/diagrams --json` | OK, 0 errors |
| `python -m scripts.diagrams check-artifacts` | OK, 6 entries |
| Инспекция `docs.yml`, `diagram-nightly.yml`, `setup-mermaid`, `mmdc_wrapper.sh` | см. findings |
| Render smoke в CI | не запускался (read-only; jobs disabled) |

## Артефакты

- `reports/audit/diagrams/findings.json`
- Копия: `reports/audit-runs/20260926T084327Z-e1c184857e46-nine/diagrams/`
