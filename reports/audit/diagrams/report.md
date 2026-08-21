<<<<<<< HEAD
# Diagrams audit — 20260821T112959Z-audit-seq-27105f85
||||||| b48ac65c98
# Циклический аудит диаграмм и `scripts/diagrams`
=======
# Audit: diagrams
>>>>>>> master20260821-3

<<<<<<< HEAD
surface_score: **2** (acceptable). Lint is green after #9326. 258 warnings remain (STALE-002/SIZE/LABEL/LINK), within warning class.
||||||| b48ac65c98
Run ID: `20260818T141321Z-diagrams-cycle-3809e140`
=======
- **domain_id:** `diagrams`
- **prompt_id:** `prompt.audit.diagrams`
- **mode:** `audit` / `AUDIT_MODE=full`
- **language:** `ru`
- **base:** `main`
- **repo:** `SatoryKono/BioactivityDataAcquisition`
- **date:** 2026-08-21
- **surface_score:** `2` (acceptable — text-as-code + pinned render + CI; local model/drift gaps remain)
- **blocked:** `false`
>>>>>>> master20260821-3

<<<<<<< HEAD
Issue #9326 closed. PR #9328 (ALLOW_MERGE=false).
||||||| b48ac65c98
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
=======
## Executive summary

Канонические диаграммы BioETL живут как text-as-code (Mermaid `.mmd` / `.mermaid`) под `docs/02-architecture/diagrams/`, рендерятся pinned `@mermaid-js/mermaid-cli@10.6.1` (lockfile в `.github/actions/setup-mermaid`, Docker fallback `minlag/mermaid-cli:10.6.1`), и закрываются CI (`docs.yml`: syntax/lint/render/drift; `diagram-nightly.yml`: smoke/budget/canary). PNG не трекается (DOC-GOV-02). PlantUML / Graphviz / drawio как источники не найдены.

Контроль зрелый, но не score 3: (1) runtime-диаграмма observability всё ещё ведёт logs/traces в Grafana после вывода Loki/Tempo; (2) security-диаграмма рендерит безымянные узлы `BW`/`SW`/`HASHED`; (3) skill `technical-designer-mermaid` указывает на несуществующий `mmd-diagrams/`; (4) secondary families (`providers/`, `sequence/`, `state-machines/`) не входят в PR drift-gate и pre-commit globs; (5) generated `90-pkg-*` class slices не имеют CI `--check`.

P0 нет. P1: 1. Proven findings: 8.

## Surface score legend

| Score | Meaning (this domain) |
| ---: | --- |
| 3 | Text source in VCS; deterministic render; CI validation; model matches system |
| 2 | Diagrams current; some regeneration/review still manual |
| 1 | Binary-only, unclear source, or regular drift |
| 0 | Key diagram wrong enough to cause a bad security/deploy decision |

**Mapping used:** domain card `prompt.audit.diagrams` surface score (0–3), not 0–5 dimension average.

## Inventory (SCOPE)

| Family | Format | Count (sources) | Sibling SVG | Classification |
| --- | --- | ---: | --- | --- |
| `architecture/` | `.mmd` | 89 | 89 | context/container/component/data/runtime |
| `class-diagrams/` | `.mmd` | 94 | 94 | class (19 curated + sandbox + 74 `90-pkg-*`) |
| `foundation/` | `.mmd` | 55 | 55 | historical/system reference |
| `_template.mmd` | `.mmd` | 1 | n/a | scaffolding (lint-excluded) |
| `views/` | `.mermaid` | 165 | 165 | decomposed review views |
| `sequence/` | `.mmd` | 5 | 5 | sequence/runtime |
| `state-machines/` | `.mmd` | 5 | 5 | state |
| `providers/{7}/` | `.mmd` | 28 | 28 | provider data flows |
| **Total sources** | | **442** | **441 SVG** | PNG gitignored |

ADR-040 / `diagrams-index.md` baseline (guarded by `tests/architecture/test_diagram_corpus_regression_guards.py`): 89+94+55+1 = **239** `.mmd` + **165** `.mermaid`. Secondary families (+38 `.mmd`) есть в дереве и в README, но не в ADR-040 inventory counts.

Other formats:

- PlantUML / `.puml` / drawio / Graphviz source diagrams: **не найдены** (кроме CLI `--format dot` для lineage, не architecture SSOT).
- Embedded Mermaid in active `docs/02-architecture/**/*.md`: C4/context pages (`current-state-diagrams.md`, `system-context.md`, `observability-layers.md`, …). CI `validate-mermaid` uses `--include-embedded`.
- Renderer pin: `10.6.1` in `setup-mermaid/package.json` + `mmdc_wrapper.sh`. **No `npx -y` in `.github/workflows`.**

## Checks run / skipped

| Check | Result |
| --- | --- |
| File inventory (`docs/02-architecture/diagrams/**`, `scripts/diagrams/**`) | done |
| Format search (PlantUML/drawio/dot/mermaid/npx) | done |
| ADR-040, POL-LLM-DIAGRAMS-001, render-retention, README | done |
| CI: `docs.yml`, `diagram-nightly.yml`, `setup-mermaid` | done |
| Pre-commit diagram hooks | done |
| Architecture tests for corpus/drift | done |
| Observability/security model vs ADR-010 / current-state | done |
| Secrets/internal endpoints in `.mmd`/`.mermaid` | no secret values; `api_key` is field name only |
| `python -m scripts.diagrams lint` | **skipped** (no shell in this agent) |
| `validate_mermaid_syntax.sh` / `render.sh` | **skipped** (no shell) |
| Memory `pre-task`/`post-task` | **skipped** (no shell) |

## Findings

| ID | Pri | Status | Path | Observation |
| --- | --- | --- | --- | --- |
| DIAG-001 | P1 | PROVEN | `architecture/22-data-operations-observability.mmd:67-69` | Logs and traces sink into Grafana after Loki/Tempo retirement |
| DIAG-002 | P2 | PROVEN | `architecture/17-security-pii-audit.mmd:39,71` | Unlabeled `HASHED`/`BW`/`SW` nodes in source and tracked SVG |
| DIAG-003 | P2 | PROVEN | `.codex`/`.junie` `technical-designer-mermaid/SKILL.md:72` | Skill still targets `mmd-diagrams/` (removed canonical root) |
| DIAG-004 | P2 | PROVEN | `docs.yml` drift globs + pre-commit `files:` | `providers/`/`sequence/`/`state-machines/` outside PR SVG-drift gate |
| DIAG-005 | P2 | PROVEN | `generate_package_family_class_diagrams.py` + `90-pkg-*` | Generator `--check` not in CLI/CI; `@date 2026-03-27` |
| DIAG-006 | P3 | PROVEN | `diagrams/README.md:101-107` | Links to gitignored `**/png/INDEX.md` |
| DIAG-007 | P3 | PROVEN | `ADR-040` inventory | Secondary families omitted from measured baseline counts |
| DIAG-008 | P3 | PROVEN | `09-observability-stack.mmd:72` / `09b` | Grafana shown as required external, not optional (ADR-010) |

## What is healthy

- Canonical source is Mermaid text, not PNG-first (anti-pattern avoided).
- Renderer version pinned; CI install is lockfile-backed (`npm ci`), not bare `npx -y`.
- SVG tracked; PNG gitignored; PR `check-diagram-drift` for primary families.
- Lint policy (SIZE/META/COLOUR/GRAPH/NBSP/STALE) + quality budget + nightly canary.
- Hexagonal overview does not show `domain -> infrastructure` (implements-ports only).
- No Redis/Loki/Tempo/Quarantine Explorer nodes in `.mmd` corpus (grep).
- `90-pkg-*` slices stay ≤30 nodes (`MAX_SLICE_NODES`) — not a full-monorepo class dump.

## Top remediations (MODE=full; not applied)

1. Rewrite `22-data-operations-observability.mmd`: metrics → optional Prometheus/Grafana; logs → files/CLI; traces → OTLP/console. Re-render SVG.
2. Define labeled nodes `HASHED`, `BronzeWriter`, `SilverWriter` in `17-security-pii-audit.mmd`; re-render SVG.
3. Replace `mmd-diagrams/` with `diagrams/` in `.codex` and `.junie` `technical-designer-mermaid` skills (then docs mirrors).
4. Extend `check-diagram-drift` and pre-commit `files:` to `providers/**`, `sequence/`, `state-machines/`.
5. Add `python -m scripts.diagrams` command + CI `--check` for `generate_package_family_class_diagrams.py`.
6. Drop dead `png/INDEX.md` links from `diagrams/README.md` (or point to render-retention policy).
7. Add sequence/providers/state-machines counts to ADR-040 / `diagrams-index.md` (keep architecture test in sync).
8. Label Grafana as optional in `09` / `09b`.

## Kit extras

- `diagram-inventory.csv`
- `render-failures.txt`
- `diagram-code-drift.csv`
- `canonical-source-map.md`

## Debt outcome

`unchanged` (audit-only; no code edits; no debt budget changes).
>>>>>>> master20260821-3
