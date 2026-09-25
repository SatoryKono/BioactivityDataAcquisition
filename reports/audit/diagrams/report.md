# Аудит диаграмм (prompt.audit.diagrams)

HEAD `32d77a51e556de60d6dc0daf871a442becc709c5`. Режим audit, full. Каталог требований не содержит `REQ-*` на диаграммы: `requirement_id=GAP`. Статус `PROVEN` только при файле или команде на этом SHA.

**surface_score: 2.** Текст диаграмм в git, SVG-соседи на месте, Mermaid CLI закреплён на 10.6.1, lint без ошибок. Срез `90-pkg-*` не совпадает с AST, а nightly-проверка этого среза выключена `if: false`. Это не score 3 («модель совпадает с системой») и не score 1: канонический корпус не бинарный и не разъезжается целиком.

Предыдущий closeout (328 `.mmd`, score 3, 0 PROVEN) на этом SHA не копировался. Счёт 328 подтверждён заново. Score 3 не подтверждён.

## Census (2026-09-25)

| Семейство | .mmd | .mermaid | sibling svg |
| --- | ---: | ---: | ---: |
| architecture | 89 | 0 | 89 |
| class-diagrams | 145 | 0 | 145 |
| foundation | 55 | 0 | 55 |
| providers | 28 | 0 | 28 |
| sequence | 5 | 0 | 5 |
| state-machines | 5 | 0 | 5 |
| `_template.mmd` | 1 | 0 | 0 |
| views | 0 | 165 | 165 |
| **итого** | **328** | **165** | **492** |

`git ls-files` видит `_template.mmd`. PNG под `diagrams/` в индексе: 0. Пропусков sibling SVG у источников: 0. PlantUML/Graphviz/drawio под `docs/` не найдены. Встроенные fences ` ```mermaid ` вне дерева diagrams: 53 файла, 82 блока (синтаксис fences отдельно не гонялся). Секретов по шаблону key/password/token в `.mmd`/`.mermaid` нет.

Типы по `%% @type`: flowchart 144, classDiagram 162, sequenceDiagram 25, stateDiagram 14, плюс короткие `sequence`/`state` у sequence/state-machines.

## Команды

| Команда | Результат |
| --- | --- |
| `lint_diagrams.py docs/02-architecture/diagrams` с `PYTHONPATH` | exit 0; 492 файла; 0 errors; 174 warnings (SIZE-002 99, STALE-002 24, LINK-001 22, LABEL-001 20, GRAPH-001 4, SIZE-003 3, CLASS-003 2) |
| тот же lint без пакета `scripts` на path | exit 0; GRAPH-001 отсутствует (DIAG-005) |
| `lint-budget --lint-report` (max errors 0) | exit 0, `lint.errors=0` |
| `check-artifacts` | exit 0, 6 SVG |
| `generate_package_family_class_diagrams.py --check` | exit 1, changed 26, stale 1 (DIAG-001) |
| `python -m scripts.diagrams.render.generate_pipeline_dataflows --check --pipeline chembl_activity` | exit 0, artifacts current |
| `prune_orphan_nodes.py --check --json` | exit 1, total_orphans 6 (DIAG-003, DIAG-004) |
| `apply-elk --dry-run` | exit 0, Modified 17, already ELK 0 (DIAG-002) |

Предупреждения SIZE-002 / STALE-002 (90–136 дней, порог ERROR 150) / LINK-001 / LABEL-001 укладываются в бюджет warnings (`max-lint-warnings` по умолчанию выключен). Отдельными дефектами не открыты.

## Канонический источник

SSOT: `docs/02-architecture/diagrams/**/*.mmd` и `views/**/*.mermaid` (ADR-040 D2, DOC-GOV-02). Рендер: `.github/actions/setup-mermaid` pin `@mermaid-js/mermaid-cli` 10.6.1, `scripts/diagrams/mmdc_wrapper.sh` требует ту же версию. `npx -y` в scripts/diagrams и diagram workflows не найден. PNG не в git.

## Пропуски

Полный рендер SVG/PNG не запускался. Embedded-fence pytest и `check-quality-gates` не запускались. Dataflow `--check` выполнен только для `chembl_activity`.

## Findings

1. **DIAG-001 P2.** `90-pkg-*` расходится с генератором; nightly `--check` выключен.
2. **DIAG-002 P2.** Детектор ELK однострочный: lint не видит multiline init, dry-run хочет переписать 17 файлов.
3. **DIAG-003 P2.** `-. label .->` не считается ребром; EXEC/MAINT ложные orphan.
4. **DIAG-004 P3.** Участники `Profiles` и `PR` без сообщений.
5. **DIAG-005 P3.** `ImportError` в lint гасит GRAPH-001.
6. **DIAG-006 P3.** У local-deployment Silver/Quarantine стоят чужие hex из палитры ADR-040.
