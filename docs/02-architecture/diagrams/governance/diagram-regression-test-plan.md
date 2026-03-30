---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

_Дата: 2026-02-27_  
_Статус: Phase 1 + Phase 2 Nightly implemented (2026-02-27)_  
_Связанные документы: diagram-modernization-program.md, diagrams/governance/policy.md, ADR-040_

## 1. Цель

Предотвращать регрессии в диаграммах до merge за счет автоматических проверок и стандартизированного ручного контроля для ограниченного эталонного пула.

## 2. Область тестирования

1. Синтаксис Mermaid (`.mmd`, `.mermaid`).
2. Консистентность рендера, где SVG остаётся primary artifact, а PNG используется как compatibility/export surface.
3. Читаемость текста в узлах и метках.
4. Семантика связей и типизация узлов.
5. Декомпозиция крупных диаграмм и наличие legend.
6. Drift между source-диаграммами и рендерами.

## 3. Уровни тестов

1. L0 Static: lint, policy checks, metadata checks.
2. L1 Render: генерация SVG/PNG, проверка артефактов.
3. L2 Visual smoke: базовая читаемость, наличие текста/лейблов.
4. L3 Governance: гейты CI, drift-контроль, PR-report.
5. L4 Periodic audit: выборочный ручной визуальный аудит.

## 4. Тестовая матрица (план)

| ID | Название теста | Цель | Инструмент | Тип | Частота | Gate |
|---|---|---|---|---|---|---|
| DIAG-T001 | Mermaid syntax valid | Исключить синтаксические ошибки | `scripts/diagrams/validate_mermaid_syntax.sh` | Auto | PR | Hard |
| DIAG-T002 | Diagram lint no ERROR | Проверка правил policy | `scripts/diagrams/lint_diagrams.py` | Auto | PR | Hard |
| DIAG-T003 | Metadata required | Контроль `@version/@date/@type/@level` | `lint_diagrams.py` | Auto | PR | Hard |
| DIAG-T004 | Stale metadata check | Выявление устаревших диаграмм | `lint_diagrams.py` | Auto | PR/Nightly | Soft |
| DIAG-T005 | No forbidden colors | Контраст и палитра | `lint_diagrams.py` | Auto | PR | Hard |
| DIAG-T006 | No emoji labels | Единый стиль | `lint_diagrams.py` | Auto | PR | Hard |
| DIAG-T007 | ELK required for large flowcharts | Стабильность layout | `lint_diagrams.py` | Auto | PR | Hard |
| DIAG-T008 | Orphan nodes controlled | Чистота графа | `scripts/diagrams/prune_orphan_nodes.py --check` | Auto | PR | Soft |
| DIAG-T009 | Render completes | Рендер без падений | `render.sh` | Auto | PR | Hard |
| DIAG-T010 | SVG artifacts exist | Проверка обязательных SVG-артефактов | CI shell check | Auto | PR | Hard |
| DIAG-T011 | PNG compatibility artifacts exist | Проверка PNG там, где они остаются compatibility surface | CI shell check | Auto | Nightly | Soft |
| DIAG-T012 | Required artifacts non-empty | Отсев пустых обязательных артефактов | CI shell check | Auto | PR | Hard |
| DIAG-T013 | Visual smoke manifest pass | Базовая читаемость эталонного пула | `check_diagram_visual_smoke.py` | Auto | PR | Hard |
| DIAG-T014 | SVG text nodes present | Не потерян текст в SVG | `scripts/diagrams/check_svg_text_visibility.py` | Auto | PR | Hard |
| DIAG-T015 | Edge labels present | Не потеряны подписи связей | `scripts/diagrams/check_svg_text_visibility.py` | Auto | PR | Hard |
| DIAG-T016 | Fallback text applied | Совместимость просмотрщиков | `add_svg_text_fallback.py` + check | Auto | PR | Hard |
| DIAG-T017 | Source-render drift | Source изменен -> рендер обновлен | `docs.yml` drift check | Auto | PR | Hard |
| DIAG-T018 | Link style guide compliance | Семантика линий | `scripts/diagrams/check_diagram_quality_gates.py` | Auto | PR | Hard |
| DIAG-T019 | classDef coverage | Типизация узлов | `scripts/diagrams/check_diagram_quality_gates.py` | Auto | PR | Soft |
| DIAG-T020 | Large diagram decomposition | Наличие L1/L2/L3 | `scripts/diagrams/check_diagram_quality_gates.py` | Auto | PR | Hard |
| DIAG-T021 | Legend present for large | Пояснение семантики | `scripts/diagrams/check_diagram_quality_gates.py` | Auto | PR | Hard |
| DIAG-T022 | Label length threshold | Читаемость текста | `scripts/diagrams/check_diagram_quality_gates.py` | Auto | PR | Soft |
| DIAG-T023 | `<br/>` overuse check | Снижение рендер-рисков | `scripts/diagrams/check_diagram_quality_gates.py` | Auto | PR | Soft |
| DIAG-T024 | Click/tooltip fallback | Навигация и перенос длинных пояснений | render smoke + heuristic (planned) | Auto | PR/Nightly | Soft |
| DIAG-T025 | PNG/SVG semantic equivalence | Смысл не теряется между форматами | visual diff + checklist (planned) | Semi-auto | Nightly | Soft |
| DIAG-T026 | Reference pool baseline diff | Быстрый регресс-контроль | snapshot diff (planned) | Auto | PR | Hard |
| DIAG-T027 | Random edge reorder stability | Устойчивость layout | chaos check (planned) | Auto | Nightly | Soft |
| DIAG-T028 | Node growth stability | Устойчивость к росту схем | stress check (planned) | Auto | Nightly | Soft |
| DIAG-T029 | Theme change stability | Устойчивость к CSS/theme | matrix job (planned) | Auto | Nightly | Soft |
| DIAG-T030 | Mermaid minor bump canary | Риск обновления CLI | canary job (planned) | Auto | Nightly/Weekly | Soft |
| DIAG-T031 | Policy docs sync | Согласованность policy/workflow/docs | doc lint + link check | Auto | PR | Soft |
| DIAG-T032 | Team acceptance review | Экспертная оценка читаемости | manual checklist | Manual | Sprint | Soft |
| DIAG-T033 | Class method render integrity | Целостность сигнатур методов в classDiagram | `scripts/diagrams/check_class_method_render_integrity.py` | Auto | PR | Hard |

### 4.1 Описание тестов

1. `DIAG-T001`: проверяет, что Mermaid-файлы валидны синтаксически и рендер не упадет на парсинге.
2. `DIAG-T002`: проверяет lint-правила policy и блокирует ошибки уровня ERROR.
3. `DIAG-T003`: проверяет обязательные метаданные (`@version/@date/@type/@level`).
4. `DIAG-T004`: сигнализирует об устаревших диаграммах по дате обновления.
5. `DIAG-T005`: запрещает неканоничные/deprecated цвета.
6. `DIAG-T006`: запрещает emoji-лейблы в policy-ограниченных местах.
7. `DIAG-T007`: требует ELK для больших flowchart-схем.
8. `DIAG-T008`: проверяет orphan-ноды (узлы без связей).
9. `DIAG-T009`: проверяет, что рендер-пайплайн выполняется без ошибок.
10. `DIAG-T010`: проверяет наличие обязательных SVG артефактов.
11. `DIAG-T011`: проверяет наличие PNG-артефактов для curated compatibility smoke set, а не для всего visual-smoke пула.
12. `DIAG-T012`: проверяет, что обязательные артефакты не пустые.
13. `DIAG-T013`: проверяет smoke-бейзлайн эталонного SVG-пула.
14. `DIAG-T014`: проверяет наличие читаемых text-node в SVG.
15. `DIAG-T015`: проверяет сохранность edge-label в SVG.
16. `DIAG-T016`: проверяет наличие fallback-текста для viewer-совместимости.
17. `DIAG-T017`: проверяет drift между source и render в PR.
18. `DIAG-T018`: проверяет соблюдение style guide по типам стрелок/линий.
19. `DIAG-T019`: проверяет покрытие диаграмм типовыми `classDef`.
20. `DIAG-T020`: проверяет декомпозицию крупных диаграмм (L1/L2/L3-подход).
21. `DIAG-T021`: проверяет наличие legend для крупных схем.
22. `DIAG-T022`: контролирует пределы длины label для читаемости.
23. `DIAG-T023`: контролирует overuse `<br/>` как источник рендер-рисков.
24. `DIAG-T024`: проверяет fallback для длинных подписей через click/tooltip-маркеры.
25. `DIAG-T025`: проверяет смысловую эквивалентность SVG/PNG эвристиками.
26. `DIAG-T026`: проверяет baseline drift по эталонному набору рендеров.
27. `DIAG-T027`: проверяет устойчивость layout к случайному reorder связей.
28. `DIAG-T028`: проверяет устойчивость layout к добавлению новых узлов.
29. `DIAG-T029`: проверяет устойчивость к смене CSS/theme.
30. `DIAG-T030`: canary-проверка на minor-обновление Mermaid CLI.
31. `DIAG-T031`: проверяет синхронность policy/workflow/docs.
32. `DIAG-T032`: ручная экспертная проверка читаемости и понятности.
33. `DIAG-T033`: проверяет соответствие методов между `.mmd` и `svg` без потери/разрыва идентификаторов.

## 5. Минимальный стартовый набор (обязательный до rollout)

1. DIAG-T001, T002, T007, T009, T010, T012, T013, T017.
2. Эталонный SVG-пул: минимум 5 диаграмм из `manifests/visual-smoke.txt`.
3. Curated PNG compatibility pool: отдельный небольшой набор в `manifests/png-compatibility.txt`.
3. Авто-отчет в PR: статус обязательных тестов + ссылки на primary SVG artifacts.

## 6. Кандидаты в эталонный пул

1. `diagrams/foundation/01-full-system-component.mmd`
2. `diagrams/foundation/30-port-adapter-mapping.mmd`
3. `diagrams/views/01-full-system-component-full.mermaid`
4. `diagrams/views/30-port-adapter-mapping-full.mermaid`
5. `diagrams/views/31-pipeline-run-lifecycle-infra.mermaid`

## 7. План внедрения тестов после согласования

### Phase 1 (быстрый запуск)
1. Включить минимальный стартовый набор в PR pipeline.
2. Ввести единый markdown/JSON report по результатам.
3. Зафиксировать baseline для эталонного пула.

### Phase 2 (усиление)
1. Добавить custom checks: line-style, classDef, legend, decomposition.
2. Добавить fallback-тесты SVG текста и edge-label.
3. Включить nightly visual regression job.

### Phase 3 (устойчивость)
1. Canary на обновление Mermaid minor-version.
2. Chaos-тесты устойчивости layout к reorder и росту узлов.
3. Квартальный аудит + пересмотр порогов.

## 8. DoD для тестового workflow

1. Все hard-gate тесты в PR обязательны и блокируют merge при fail.
2. Primary SVG artifacts доступны в CI для review; PNG публикуются там, где нужен compatibility/export surface.
3. Есть автоматический отчет с метриками читаемости.
4. Есть documented playbook для быстрого восстановления при регрессии.

## 9. Реализовано в Phase 1

1. Добавлен `scripts/diagrams/check_diagram_quality_gates.py` (DIAG-T018..T023).
2. Добавлен source-manifest `manifests/quality-gates.txt` для эталонного пула.
3. Расширен `.github/workflows/docs.yml`:
   - запуск `check_diagram_artifacts.py` (DIAG-T010/T011/T012);
   - запуск quality-gates после render/smoke/check_svg_text_visibility;
   - публикация `diagram-quality-report.json/.md` как CI artifact;
   - автопубликация markdown-отчета в `GITHUB_STEP_SUMMARY` для PR review.
4. Добавлены архитектурные тесты `tests/architecture/test_diagram_quality_gates.py`.
5. Добавлены архитектурные тесты `tests/architecture/test_diagram_artifact_check.py` и workflow wiring test.
6. DIAG-T014/T015 переведены из planned в implemented через `check_svg_text_visibility.py`.
7. Добавлен nightly pipeline `.github/workflows/diagram-nightly.yml`:
   - `run_diagram_nightly_suite.py` (DIAG-T024..T029);
   - mermaid minor canary matrix (DIAG-T030);
   - nightly artifacts + step summary.

## 10. Текущие ограничения и follow-up

1. DIAG-T024..T030 переведены в nightly workflow `.github/workflows/diagram-nightly.yml`, но пока не являются PR hard-gate.
2. DIAG-T025 реализован эвристикой (aspect/text parity), без pixel-level visual diff.
3. DIAG-T026 использует git-baseline drift; отдельное baseline storage still pending.
4. Для DIAG-T030 canary версия задана матрицей (`10.6.1` stable + `11.4.0` canary, allow-failure).

## 11. Как запускать проверки

1. Полный pre-merge профиль:

```bash
scripts/diagrams/run_diagram_checks.sh --profile pr
```

2. Nightly-профиль локально (включая DIAG-T024..T029):

```bash
scripts/diagrams/run_diagram_checks.sh --profile nightly
```

3. Быстрый локальный цикл:

```bash
scripts/diagrams/run_diagram_checks.sh --profile quick
```

4. Проверка только одной диаграммы:

```bash
scripts/diagrams/run_diagram_checks.sh --profile pr \
  --diagram docs/02-architecture/diagrams/foundation/30-port-adapter-mapping.mmd
```

5. Для single-file быстрой проверки:

```bash
scripts/diagrams/run_diagram_checks.sh --profile quick \
  --diagram docs/02-architecture/diagrams/foundation/30-port-adapter-mapping.mmd
```

Примечание: для `DIAG-T001`/`DIAG-T009` нужен рабочий `mmdc` + браузер Puppeteer (`chrome-headless-shell`).
