# TOP-25 Implementation Report (Mermaid → PNG)

*Версия: 1.0 | Дата: 2026-02-17*

Отчёт обеспечивает трассировку для первых 25 реализуемых диаграмм: исходник Mermaid, ожидаемый PNG-путь, параметры рендера и статус читаемости.

## Параметры рендера (базовый профиль)

```bash
mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2
```

|   # | Diagram ID | Исходник Mermaid                                | PNG-путь                                        | Параметры рендера                                         | Статус читаемости | Примечание                                 |
| --: | ---------- | ----------------------------------------------- | ----------------------------------------------- | --------------------------------------------------------- | ----------------- | ------------------------------------------ |
|   1 | T01        | `01-full-system-component.mermaid`              | `png/01-full-system-component.png`              | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|   2 | T02        | `01-high-level.mermaid`                         | `png/01-high-level.png`                         | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|   3 | T03        | `02-full-medallion-data-flow.mermaid`           | `png/02-full-medallion-data-flow.png`           | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|   4 | T04        | `02-medallion.mermaid`                          | `png/02-medallion.png`                          | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|   5 | T05        | `03-pipeline-execution-happy-path.mermaid`      | `png/03-pipeline-execution-happy-path.png`      | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|   6 | T06        | `03-pipeline-sequence.mermaid`                  | `png/03-pipeline-sequence.png`                  | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|   7 | T07        | `04-domain-layer-class-diagram.mermaid`         | `png/04-domain-layer-class-diagram.png`         | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|   8 | T08        | `04-error-flow.mermaid`                         | `png/04-error-flow.png`                         | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|   9 | T09        | `05-layers-interaction.mermaid`                 | `png/05-layers-interaction.png`                 | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  10 | T10        | `05-locking.mermaid`                            | `png/05-locking.png`                            | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  11 | T11        | `05-pipeline-lifecycle-states.mermaid`          | `png/05-pipeline-lifecycle-states.png`          | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  12 | T12        | `06-application-layer-class-diagram.mermaid`    | `png/06-application-layer-class-diagram.png`    | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  13 | T13        | `06-pipeline-execution.mermaid`                 | `png/06-pipeline-execution.png`                 | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  14 | T14        | `07-circuit-breaker-states.mermaid`             | `png/07-circuit-breaker-states.png`             | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  15 | T15        | `07-medallion-flow.mermaid`                     | `png/07-medallion-flow.png`                     | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  16 | T16        | `08-complete-etl-workflow.mermaid`              | `png/08-complete-etl-workflow.png`              | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  17 | T17        | `08-domain-ddd.mermaid`                         | `png/08-domain-ddd.png`                         | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  18 | T18        | `09-full-er-diagram.mermaid`                    | `png/09-full-er-diagram.png`                    | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  19 | T19        | `10-infrastructure-layer-class-diagram.mermaid` | `png/10-infrastructure-layer-class-diagram.png` | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Needs Review**  | Требуется ручная проверка масштаба шрифтов |
|  20 | T20        | `11-lock-acquisition-sequence.mermaid`          | `png/11-lock-acquisition-sequence.png`          | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Needs Review**  | Требуется ручная проверка масштаба шрифтов |
|  21 | T21        | `13-domain-models-relationship.mermaid`         | `png/13-domain-models-relationship.png`         | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Needs Review**  | Требуется ручная проверка масштаба шрифтов |
|  22 | T22        | `14-provider-health-states.mermaid`             | `png/14-provider-health-states.png`             | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Needs Review**  | Требуется ручная проверка масштаба шрифтов |
|  23 | T23        | `15-dq-check-workflow.mermaid`                  | `png/15-dq-check-workflow.png`                  | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Needs Review**  | Требуется ручная проверка масштаба шрифтов |
|  24 | T24        | `16-memory-lock-class.mermaid`                  | `png/16-memory-lock-class.png`                  | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |
|  25 | T25        | `17-pipeline-hierarchy.mermaid`                 | `png/17-pipeline-hierarchy.png`                 | `mmdc -w 1600 -H 900 -t neutral -b transparent --scale 2` | **Pass**          | Шрифт/контраст OK                          |

## Критерии читаемости

- Минимальный размер основного текста после рендера: 14px.
- Контраст текста к фону: не ниже WCAG AA для статичных схем.
- На схеме не более 20 пересечений линий без явных маркеров направлений.
