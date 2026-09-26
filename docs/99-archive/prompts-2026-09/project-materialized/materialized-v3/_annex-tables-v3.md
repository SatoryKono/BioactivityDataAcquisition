# Annex — Tables from DOCX

## Table 0

Параметр | Значение
Дата генерации | 28.08.2026
ID документа | BIOETL-PROMPT-ARCH-KERNEL-V3-003
Repository baseline | main @ 3aba8559a58038cd9ff9a90621f19ea39b930a2f
Source portfolio | 10+ 14 canonical cycle cards 
Execution profile | MODE=full;  / ALLOW_ISSUE_WRITE/PUSH/MERGE/CLOSE=true

## Table 1

№ | Объект | Prompt ID | Source path* | 
01 | Документация | prompt.audit.cycle.docs | cycle/docs.md | 8.87
02 | Диаграммы | prompt.audit.cycle.diagrams | cycle/diagrams.md | 8.77
03 | Агенты и память | prompt.audit.cycle.agents-memory | cycle/agents-memory.md | 8.81
04 | Конфигурация | prompt.audit.cycle.configs | cycle/configs.md | 8.73
05 | Тестовая система | prompt.audit.cycle.tests | cycle/tests.md | 8.79
06 | Технический долг | prompt.audit.cycle.tech-debt | cycle/tech-debt.md | 8.76
07 | Архитектура | prompt.audit.cycle.architecture | cycle/architecture.md | 9.12
08 | Телеметрия | prompt.audit.cycle.telemetry | cycle/telemetry.md | 8.84
09 | Дашборды | prompt.audit.cycle.dashboards | cycle/dashboards.md | 8.98
10 | Полный проект + CodeRabbit | prompt.audit.cycle.coderabbit | cycle/coderabbit.md | 9.23
11 | Medallion / write-path | prompt.audit.project.new2.medallion | project/new2/01-medallion.md | 8.68
12 | DQ / Pandera / Gold-контракты | prompt.audit.project.new2.dq-contracts | project/new2/02-dq-contracts.md | 8.64
13 | Control plane / replay / resume | prompt.audit.project.new2.control-plane | project/new2/03-control-plane.md | 8.68
14 | Провайдеры и каталог сущностей | prompt.audit.project.new2.providers | project/new2/04-providers.md | 8.45
15 | HTTP-клиенты и адаптеры | prompt.audit.project.new2.http-clients | project/new2/05-http-clients.md | 8.60
16 | Нормализация и идентификаторы | prompt.audit.project.new2.normalization | project/new2/06-normalization.md | 8.46
17 | CLI / HTTP public compatibility | prompt.audit.project.new2.cli-compat | project/new2/07-cli-compat.md | 8.41
18 | Безопасность и секреты | prompt.audit.project.new2.security-secrets | project/new2/08-security-secrets.md | 8.63
19 | VCR / HTTP fixtures | prompt.audit.project.new2.vcr-http | project/new2/09-vcr-http.md | 8.60
20 | QA gates и scorecard freshness | prompt.audit.project.new2.qa-gates | project/new2/10-qa-gates.md | 8.66
21 | GitHub Actions | prompt.audit.project.new2.github-actions | project/new2/11-github-actions.md | 8.57
22 | REQ-* traceability | prompt.audit.project.new2.requirements-trace | project/new2/12-requirements-trace.md | 8.60
23 | Operations / runbooks | prompt.audit.project.new2.ops-runbooks | project/new2/13-ops-runbooks.md | 8.45
24 | Scripts inventory / lifecycle | prompt.audit.project.new2.scripts-inventory | project/new2/14-scripts-inventory.md | 8.59

## Table 2

ID | Категория | Вес | Что проверяется
C1 | Предметная полнота | 10% | Полнота объекта, подповерхностей, рисков и исключений.
C2 | Привязка к SSOT и архитектуре BioETL | 10% | Связь с RULES, REQUIREMENTS, ADR, контрактами и владельцами слоёв.
C3 | Доказательность и фактчек | 10% | PROVEN/NOT_PROVEN, path/symbol/command evidence, запрет догадок.
C4 | Полнота цикла | 10% | Baseline, audit, normalize, plan, issues, fix, validate, close, post-audit.
C5 | Жизненный цикл GitHub Issues | 10% | Dedupe, create/reuse/defer/block, acceptance и закрытие на target branch.
C6 | Безопасность мутаций | 10% | Fail-closed permissions, worktree, secrets, budgets, branch и CI guards.
C7 | Верификация и защита от регрессий | 10% | Same-scope recheck, domain gates, required CI, delta и regression scan.
C8 | Детерминизм, идемпотентность и resume | 10% | Stable fingerprint, append-only ledger, resume cursor, повторный запуск.
C9 | Исполнимость и ограниченность затрат | 10% | Конкретные команды, caps, bounded scope, platform notes и stop conditions.
C10 | Контракт выходов и трассируемость | 10% | Структурированные outputs, schemas, requirement_id и audit trail.

## Table 3

Диапазон | Уровень | Интерпретация
0,0–2,9 | Критический | Метод отсутствует или создаёт прямой риск.
3,0–4,9 | Слабый | Есть намерение, но нет воспроизводимого процесса.
5,0–6,9 | Частичный | Основной поток описан, существенные gaps не закрыты.
7,0–8,4 | Хороший | Исполнимый prompt с отдельными process/guard gaps.
8,5–9,4 | Сильный | Evidence-first, ограниченный и трассируемый prompt.
9,5–10,0 | Целевой | Machine-verifiable composition с устойчивым lifecycle и resume.

## Table 4

ID | Долг | Следствие
D1 | Дублирование controller logic | Audit/Issues/Fix/Validate/Early-stop повторяются в десятках cards; drift неизбежен.
D2 | Конфликт defaults | Domain cards часто materialize ALLOW_*=true, тогда как общий orchestrator задуман fail-closed.
D3 | Неполный Issue state machine | Не везде формализованы reuse/defer/blocked, target-branch close и residual disposition.
D4 | Нет stable finding fingerprint | Перефразированный root cause может породить duplicate finding и Issue.
D5 | Слабый resume contract | run_id есть, но append-only ledger, cursor и side-effect replay описаны непоследовательно.
D6 | Разные output schemas | Папка reports задана, однако stage artifacts и JSON contracts не унифицированы.
D7 | Overlay как проза | Нет JSON Schema, которая запрещает overlay ослаблять kernel или пропускать обязательные поля.
D8 | Нет compiler/golden tests | Не проверяются rendered prompts, parameter precedence, duplicate stages и guard weakening.
D9 | Смешение method и execution profile | Предметный метод хранит permissions и GitHub behavior, хотя это ответственность orchestration layer.
D10 | Сложная миграция | IDs используются операторами; без wrappers/deprecation policy улучшение ломает bookmarks и automation.

## Table 5

№ | Объект | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 | Итог | Δ
01 | Документация | 9.20 | 9.40 | 9.20 | 9.82 | 9.85 | 9.45 | 9.41 | 9.12 | 8.90 | 9.95 | 9.43 | +0.56
02 | Диаграммы | 9.00 | 9.28 | 9.58 | 9.72 | 9.45 | 9.55 | 9.68 | 9.02 | 9.00 | 9.72 | 9.40 | +0.63
03 | Агенты и память | 9.48 | 9.52 | 9.58 | 9.72 | 9.55 | 9.87 | 9.48 | 9.42 | 8.76 | 9.72 | 9.51 | +0.70
04 | Конфигурация | 9.38 | 9.62 | 9.48 | 9.62 | 9.77 | 9.95 | 9.28 | 9.22 | 8.86 | 9.62 | 9.48 | +0.75
05 | Тестовая система | 9.38 | 9.22 | 9.48 | 9.72 | 9.87 | 9.95 | 9.68 | 9.32 | 8.96 | 9.72 | 9.53 | +0.74
06 | Технический долг | 9.18 | 9.32 | 9.48 | 9.72 | 9.57 | 9.95 | 9.48 | 9.52 | 8.76 | 9.72 | 9.47 | +0.71
07 | Архитектура | 9.50 | 9.70 | 9.40 | 9.95 | 9.85 | 9.45 | 9.78 | 9.82 | 8.90 | 9.95 | 9.63 | +0.51
08 | Телеметрия | 9.48 | 9.42 | 9.78 | 9.72 | 9.35 | 9.77 | 9.68 | 9.32 | 8.86 | 9.82 | 9.52 | +0.68
09 | Дашборды | 9.68 | 9.72 | 9.78 | 9.82 | 9.95 | 9.95 | 9.78 | 9.74 | 9.06 | 9.92 | 9.74 | +0.76
10 | Полный проект + CodeRabbit | 9.48 | 9.62 | 9.95 | 9.95 | 9.95 | 9.95 | 9.88 | 9.77 | 8.50 | 9.95 | 9.70 | +0.47
11 | Medallion / write-path | 9.58 | 9.62 | 9.68 | 9.95 | 9.95 | 9.95 | 9.38 | 9.95 | 8.76 | 9.78 | 9.66 | +0.98
12 | DQ / Pandera / Gold-контракты | 9.48 | 9.62 | 9.58 | 9.95 | 9.95 | 9.95 | 9.38 | 9.95 | 8.66 | 9.88 | 9.64 | +1.00
13 | Control plane / replay / resume | 9.48 | 9.72 | 9.71 | 9.95 | 9.95 | 9.95 | 9.38 | 9.95 | 8.66 | 9.95 | 9.67 | +0.99
14 | Провайдеры и каталог сущностей | 9.08 | 9.22 | 9.38 | 9.95 | 9.95 | 9.95 | 9.08 | 9.95 | 8.76 | 9.88 | 9.52 | +1.07
15 | HTTP-клиенты и адаптеры | 9.38 | 9.52 | 9.58 | 9.95 | 9.95 | 9.95 | 9.38 | 9.95 | 8.76 | 9.58 | 9.60 | +1.00
16 | Нормализация и идентификаторы | 8.98 | 9.32 | 9.41 | 9.95 | 9.95 | 9.95 | 9.18 | 9.95 | 8.66 | 9.95 | 9.53 | +1.07
17 | CLI / HTTP public compatibility | 8.88 | 9.22 | 9.41 | 9.95 | 9.95 | 9.95 | 9.08 | 9.95 | 8.66 | 9.95 | 9.50 | +1.09
18 | Безопасность и секреты | 9.08 | 9.32 | 9.95 | 9.95 | 9.95 | 9.95 | 9.84 | 9.95 | 8.56 | 9.95 | 9.65 | +1.02
19 | VCR / HTTP fixtures | 8.98 | 9.22 | 9.91 | 9.95 | 9.95 | 9.95 | 9.38 | 9.95 | 8.66 | 9.95 | 9.59 | +0.99
20 | QA gates и scorecard freshness | 9.28 | 9.42 | 9.58 | 9.95 | 9.95 | 9.95 | 9.48 | 9.95 | 8.76 | 9.88 | 9.62 | +0.96
21 | GitHub Actions | 9.18 | 9.42 | 9.58 | 9.95 | 9.95 | 9.95 | 9.28 | 9.95 | 8.76 | 9.78 | 9.58 | +1.01
22 | REQ-* traceability | 9.08 | 9.62 | 9.91 | 9.95 | 9.95 | 9.95 | 9.18 | 9.95 | 8.56 | 9.95 | 9.61 | +1.01
23 | Operations / runbooks | 8.88 | 9.32 | 9.41 | 9.95 | 9.95 | 9.95 | 9.08 | 9.95 | 8.66 | 9.95 | 9.51 | +1.06
24 | Scripts inventory / lifecycle | 9.08 | 9.42 | 9.48 | 9.95 | 9.95 | 9.95 | 9.28 | 9.95 | 8.76 | 9.88 | 9.57 | +0.98

## Table 6

Rank | Composition | Weighted score
1 | Дашборды | 9.74
2 | Полный проект + CodeRabbit | 9.70
3 | Control plane / replay / resume | 9.67
4 | Medallion / write-path | 9.66
5 | Безопасность и секреты | 9.65
6 | DQ / Pandera / Gold-контракты | 9.64
7 | Архитектура | 9.63
8 | QA gates и scorecard freshness | 9.62
9 | REQ-* traceability | 9.61
10 | HTTP-клиенты и адаптеры | 9.60
11 | VCR / HTTP fixtures | 9.59
12 | GitHub Actions | 9.58
13 | Scripts inventory / lifecycle | 9.57
14 | Тестовая система | 9.53
15 | Нормализация и идентификаторы | 9.53
16 | Телеметрия | 9.52
17 | Провайдеры и каталог сущностей | 9.52
18 | Агенты и память | 9.51
19 | Operations / runbooks | 9.51
20 | CLI / HTTP public compatibility | 9.50
21 | Конфигурация | 9.48
22 | Технический долг | 9.47
23 | Документация | 9.43
24 | Диаграммы | 9.40

## Table 7

Priority | Workstream | Действия | Acceptance
P0 | Нормативное решение | Принять ADR «Prompt Kernel and Overlay Architecture»; определить owners, precedence, versioning и migration window. | ADR принят; owner и compatibility policy назначены.
P0 | Kernel extraction | Вынести controller, evidence, Issue FSM, outputs, stop/resume в cyclic-kernel-v3.md. | No duplicated controller stages in overlays.
P0 | Schemas | Создать schemas kernel/overlay/profile/finding/ledger; запретить unknown guard overrides. | All 24 overlays validate; negative weakening cases fail.
P1 | Compiler | Materialize kernel+overlay+profile; resolve params; compute prompt_sha8; emit provenance header. | Deterministic byte-identical render for same inputs.
P1 | Ledger/resume | Append-only ledger events, stable fingerprints, cursor, side-effect idempotency. | Interrupted pilot resumes without duplicate Issue/PR.
P1 | Migrate 24 domains | Перенести предметные sections в overlays; оставить legacy IDs как wrappers. | Rendered parity accepted for all 24 IDs.
P1 | Prompt tests | Golden render, schema, guard non-weakening, profile precedence, Issue FSM, resume tests. | CI blocks regressions and unsafe defaults.
P2 | Pilot | Read-only + full-run pilots на 5 macro-groups; собрать duration/noise/duplicate metrics. | No P0 method break; measured operating envelope.
P2 | Deprecation | Mark megacards deprecated after parity and pilot; publish migration guide. | No broken operator bookmark; warnings precede removal.
P3 | Expansion | Добавить новые overlays по evidence-backed gaps; не копировать kernel. | New domain requires only schema-valid overlay and tests.

## Table 8

Candidate overlay | Scope
Composite pipeline semantics | Seed/dependencies/enrichers/merge/cross-validation, MANY_TO_ONE aggregation, EXPLICIT_RULES priorities.
Quarantine lifecycle | Payload immutability, deterministic hash, status machine, replay and filtered reads.
Schema evolution/migrations | Contract registry, compatibility levels, migration guides, generated artifacts.
Lineage/provenance | Artifact closure, input snapshot identity, cross-store reconciliation.
Locking/concurrency/shutdown | Fencing, lock ownership, graceful shutdown, interrupted writes.
Storage lifecycle | Vacuum, archive, retention-sensitive cleanup, restore evidence.
Performance/cost | Hotspots, I/O amplification, API quota cost, bounded benchmarks.
Release/versioning | SemVer, changelog, compatibility windows, release evidence.
Licensing/data provenance | Provider terms, attribution, dataset redistribution constraints.
Prompt-system self-audit | Registry freshness, orphan IDs, duplicate overlays, compiler drift, deprecation debt.

## Table 9

Metric | Current | Target | Evidence
Controller duplication | 24 copies | 1 kernel | Static lint
Unsafe library defaults | Multiple ALLOW_*=true | 0 | Schema/profile check
Schema-valid overlays | 0/24 | 24/24 | CI contract test
Stable finding fingerprints | Не гарантированы | 100% findings | Ledger validation
Resume duplicate side effects | Не измеряется | 0 in pilots | Integration test
Legacy ID breakage | Риск | 0 | Compatibility golden
Budget raises from prompts | Policy only | 0 accepted | Plan/payload lint
Target-branch premature close | Possible | 0 | Issue FSM test
Rendered prompt determinism | Не проверяется | Byte-identical | Compiler golden
Domain expansion cost | Copy megacard | One overlay + tests | Lead-time metric

## Table 10

Risk | Mitigation
Kernel becomes a new monolith | Versioned fragments, small schemas, strict ownership and compatibility tests.
Overlay loses domain nuance | Mandatory MANDATORY_EVIDENCE/VALIDATION fields plus domain golden examples.
Full profile used casually | Library default remains read-only; full-write profile requires explicit name and provenance.
Compiler hides rendered behavior | Commit generated catalog/diff, expose prompt_sha8 and render command.
Migration breaks operators | Legacy wrappers, deprecation window, parity reports and redirect catalog.
Score optimism | Pilot benchmark: precision of findings, duplicate rate, cycle completion, regression rate and duration.

## Table 11

№ | Объект | Source prompt | Target overlay | Target score
01 | Документация | prompt.audit.cycle.docs | overlay:docs | 9.43
02 | Диаграммы | prompt.audit.cycle.diagrams | overlay:diagrams | 9.40
03 | Агенты и память | prompt.audit.cycle.agents-memory | overlay:agents-memory | 9.51
04 | Конфигурация | prompt.audit.cycle.configs | overlay:configs | 9.48
05 | Тестовая система | prompt.audit.cycle.tests | overlay:tests | 9.53
06 | Технический долг | prompt.audit.cycle.tech-debt | overlay:tech-debt | 9.47
07 | Архитектура | prompt.audit.cycle.architecture | overlay:architecture | 9.63
08 | Телеметрия | prompt.audit.cycle.telemetry | overlay:telemetry | 9.52
09 | Дашборды | prompt.audit.cycle.dashboards | overlay:dashboards | 9.74
10 | Полный проект + CodeRabbit | prompt.audit.cycle.coderabbit | overlay:coderabbit | 9.70
11 | Medallion / write-path | prompt.audit.project.new2.medallion | overlay:medallion | 9.66
12 | DQ / Pandera / Gold-контракты | prompt.audit.project.new2.dq-contracts | overlay:dq-contracts | 9.64
13 | Control plane / replay / resume | prompt.audit.project.new2.control-plane | overlay:control-plane | 9.67
14 | Провайдеры и каталог сущностей | prompt.audit.project.new2.providers | overlay:providers | 9.52
15 | HTTP-клиенты и адаптеры | prompt.audit.project.new2.http-clients | overlay:http-clients | 9.60
16 | Нормализация и идентификаторы | prompt.audit.project.new2.normalization | overlay:normalization | 9.53
17 | CLI / HTTP public compatibility | prompt.audit.project.new2.cli-compat | overlay:cli-compat | 9.50
18 | Безопасность и секреты | prompt.audit.project.new2.security-secrets | overlay:security-secrets | 9.65
19 | VCR / HTTP fixtures | prompt.audit.project.new2.vcr-http | overlay:vcr-http | 9.59
20 | QA gates и scorecard freshness | prompt.audit.project.new2.qa-gates | overlay:qa-gates | 9.62
21 | GitHub Actions | prompt.audit.project.new2.github-actions | overlay:github-actions | 9.58
22 | REQ-* traceability | prompt.audit.project.new2.requirements-trace | overlay:requirements-trace | 9.61
23 | Operations / runbooks | prompt.audit.project.new2.ops-runbooks | overlay:ops-runbooks | 9.51
24 | Scripts inventory / lifecycle | prompt.audit.project.new2.scripts-inventory | overlay:scripts-inventory | 9.57
