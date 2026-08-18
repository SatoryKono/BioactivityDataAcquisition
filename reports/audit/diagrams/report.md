# Циклический аудит диаграмм и `scripts/diagrams`

Run ID: `20260818T141321Z-diagrams-cycle-3809e140`

Base: `main@3809e140aa`

Scope: `docs/02-architecture/diagrams`, `scripts/diagrams`

Режим: `full`, 10 итераций, read-only mutation fallback

Итоговый `surface_score`: **1 / 3 (weak)**

## Итог

Корпус имеет сильную базовую механику — 441 активный text-as-code источник, 441 соответствующий SVG, pinned Mermaid CLI `10.6.1`, нулевой hard lint budget и проходящие curated artifact/smoke gates. Однако опубликованные provider-specific диаграммы содержат системные противоречия живым конфигам и нормативному storage contract, а официальный Docker render fallback и два публичных fixer-а дают ложные либо неработающие результаты. Поэтому поверхность нельзя оценить выше `1` до устранения P1 и восстановления воспроизводимого полного render gate.

Найдено **7 PROVEN** gaps: `P1=1`, `P2=5`, `P3=1`, `P0=0`. Секретов и непубликуемых внутренних endpoint-ов в источниках не обнаружено. Бюджеты качества не повышались. PNG не создавались и не коммитились.

## Главные gaps

| ID | Priority | Кратко | Статус |
| --- | --- | --- | --- |
| `DIAG-AUD-001` | P1 | ChEMBL и ещё четыре provider API diagrams противоречат auth/pagination/storage config/SSOT | PROVEN, unchanged |
| `DIAG-AUD-002` | P2 | 9 SVG без fallback text; 23 без canonical CSS; broad gate видит лишь часть | PROVEN, unchanged |
| `DIAG-AUD-003` | P2 | Official Docker fallback ломает Chromium discovery args-only Puppeteer config | PROVEN, unchanged |
| `DIAG-AUD-004` | P2 | `apply-elk` предлагает менять 17 уже ELK-enabled multiline sources | PROVEN, unchanged |
| `DIAG-AUD-005` | P2 | `differentiate-linkstyle` молча сканирует удалённый каталог и 0 файлов | PROVEN, unchanged |
| `DIAG-AUD-006` | P2 | `generate-dataflows --check` создаёт date-only drift для 14 artifacts | PROVEN, unchanged |
| `DIAG-AUD-007` | P3 | Published view inventory: 162 вместо фактических 165 | PROVEN, unchanged |

Полные поля доказательств и remediation находятся в `findings.json`.

## Инвентаризация

- 442 text source candidates: 277 `.mmd` (включая `_template.mmd`) и 165 `.mermaid`.
- 441 активная диаграмма и 441 tracked SVG sibling; lone PNG и tracked PNG не найдены.
- 6 embedded Mermaid fences в 4 Markdown-файлах; config-only fence без diagram declaration корректно исключается validator-ом.
- Классификация активного корпуса: component 300, data 70, sequence 25, state 14, context 14, container 12, deployment 6, CI flow 1.
- Renderer: `@mermaid-js/mermaid-cli 10.6.1`, зафиксирован в action package/lock и Docker image reference. Bare `npx -y` в production CI/render scripts не найден.
- C4 zoom используется как context/container/component; признаков подмены container на Docker или whole-repo code-level dump нет.
- Полная строковая карта находится в `diagram-inventory.csv`.

## Gate evidence

| Проверка | Результат |
| --- | --- |
| `python -m scripts.diagrams lint docs/02-architecture/diagrams` | PASS: 441 checked, 0 failed, 0 errors, 279 warnings |
| `lint-budget --mode pr ...` | PASS: hard=0, DIAG-T022=0, DIAG-T023=0, lint errors=0 |
| `check-quality-gates` | PASS: 5 files, 0 hard/warning failures |
| default/extended/broad `check-artifacts` | PASS: 6 / 26 / 56 |
| default/extended/broad `check-visual-smoke` | PASS: 6 / 26 / 56 |
| default/extended `check-svg-text` | PASS: 6 / 26 |
| broad `check-svg-text` | FAIL: architecture SVG 24 lacks readable fallback text |
| full `fix-svg-text --check` | FAIL: 9 SVG need fallback text |
| `fix-svg-styles --check` | FAIL: 23 SVG need injection |
| `fix-orphans --check` | PASS: 0 orphan artifacts |
| `fix-operators --check` | PASS: 442 scanned, no issues |
| pinned direct Docker sample renders | PASS: flowchart, sequence, state, class |
| official pinned Docker `checks --profile quick` | FAIL: Puppeteer/Chromium discovery blocker |
| `generate-dataflows --check` | FAIL: 14 date-only stale artifacts; 0 normalized semantic mismatches |
| focused diagram test groups | PASS: 49 + 53 + 53 tests |
| additional composite/config/debt groups | PASS: 8 + 25 + 5 tests |
| docs link/spec/config checks | PASS |
| docs runtime-mirror/freshness drift check | PASS |
| Codex-Junie mirror parity | PASS |

Полный `checks --profile pr --enforce-budget` не завершён: системный `mmdc 11.12.0` правильно отклонён pin guard-ом, а pinned Docker fallback доказанно ломается в official wrapper. После `DIAG-AUD-003` точная повторная команда: `MMDC_FORCE_DOCKER=1 python -m scripts.diagrams checks --profile pr --enforce-budget`.

## Accuracy и security

Core architecture, composite и config-topology guard suites проходят. Generated ChEMBL dataflow preview после исключения display-only date полностью совпадает с tracked content, поэтому semantic drift там не заявлен. При ручной проверке provider-specific claim mapping подтверждён один системный P1: неверные auth/pagination/storage claims перечислены в `DIAG-AUD-001`.

Поиск URL/IP/localhost/token/secret patterns не выявил опубликованных secret values или внутренних endpoint-ов. Термины `token`/`secret` встречаются только как архитектурные понятия и security filtering labels.

## Mutation blocker

Исходный checkout содержал крупный чужой dirty work, поэтому аудит выполнялся в отдельном worktree `/tmp/bioetl-diagrams-cycle-3809e140`. Все три разрешённые `.env` GitHub credential variables и default `gh` credential были проверены read-only запросом и не прошли authentication. Значения секретов не печатались.

Согласно `orchestrator-guards.md`, missing permissions требуют остановить mutation и вернуть read-only + blocker report. Поэтому:

- source/SVG fixes не применялись;
- GitHub issues не создавались, но payloads сохранены в `issues.jsonl` и по итерациям;
- commit/push/merge/close не выполнялись;
- финальный delta всех семи findings: `unchanged`; regressions/new-after-fix отсутствуют.

Proof-or-Stop для claim `reviewed` сформировал bundle и вернул ожидаемый `STOP`: независимый evaluator receipt недоступен в single-agent запуске. Поэтому отчёт не заявляет `independently reviewed` или `ready_to_merge`. Обязательный memory post-task затем прошёл успешно (`ok=true`, `degraded=false`) и записал локальную episodic summary; это единственный untracked файл вне ignored report tree, созданный обязательным memory workflow.

## Рекомендуемый порядок устранения

1. Исправить `DIAG-AUD-001` и добавить provider config contract test.
2. Исправить Docker branch `DIAG-AUD-003`, затем прогнать полный pinned render.
3. Нормализовать только перечисленные SVG и расширить required coverage (`DIAG-AUD-002`).
4. Починить idempotence/path fixers (`DIAG-AUD-004`, `DIAG-AUD-005`).
5. Устранить date-only generated drift и обновить view inventory (`DIAG-AUD-006`, `DIAG-AUD-007`).

Не следует повышать lint/debt budgets или коммитить PNG/bulk binary render dumps для прохождения этих проверок.
