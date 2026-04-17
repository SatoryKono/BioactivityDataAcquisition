______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-01'

______________________________________________________________________

# D-01: Governance & Style Guide документации BioETL

## Executive Summary

D-01 задаёт единые правила управления и стиля для документации BioETL.
Нормативные страницы MUST быть проверяемыми: команды воспроизводимы, ссылки
разрешаются, cross-links синхронизированы с кодом, а источник истины указан
явно.

Актуализация `2026-03-31` закрепляет control-plane publication delta: проект
публикует не только data contracts Gold слоя, но и control-plane / inspection
contracts. Для таких surfaces действует правило traceability documentation
pack: `ADR + contract + CLI + runbook`.

## Область действия

Этот документ определяет:

- канонический путь, статус и навигационную публикацию D-01;
- допустимые классы документации и source-of-truth discipline;
- обязательные шаблоны для published docs;
- требования к связности ADR ↔ contract ↔ CLI ↔ runbook;
- обязательные секции для control-plane contracts;
- минимальные quality gates для documentation governance.

Этот документ не заменяет:

- [Documentation Publication Policy](06-doc-publication-policy.md);
- [Documentation Navigation Policy](07-doc-nav-policy.md);
- [ADR-043: Documentation Knowledge Management](../../02-architecture/decisions/ADR-043-documentation-knowledge-management.md);
- `RULES.md` и active ADR как источники runtime и architectural truth.

## Каноническое размещение

- Канонический путь для D-01 MUST быть
  `docs/00-project/governance/01-documentation-governance-style-guide.md`.
- Любые draft, export или historical copies D-01 вне
  `docs/00-project/governance/` MUST NOT считаться нормативным источником истины.
- Нормативной считается Markdown-версия, опубликованная через `mkdocs.yml`.

## Нормативная иерархия

1. `RULES.md`, active ADR, published contract docs и published runbooks задают
   проектные и runtime-правила.
1. D-01 задаёт metapolicy: как документировать эти правила и как связывать
   документационные surfaces.
1. Publication policy и nav policy определяют class/discoverability, но не
   подменяют содержательные требования D-01.

## Документационные классы и Source of Truth

- Классы страниц MUST соответствовать
  [Documentation Publication Policy](06-doc-publication-policy.md).
- Published документы в `docs/00-05/**` MUST описывать текущее, а не
  историческое поведение.
- Archive материалы MAY использоваться как traceability context, но MUST NOT
  переопределять active published guidance.
- Internal и repo-only материалы MAY использоваться как supporting evidence, но
  MUST NOT заменять published ADR, contract, CLI или runbook.

### Граница для `reports/**`

- Семейство `reports/**` MUST рассматриваться как repo-only supporting surface,
  а не как published guidance.
- Допустимая taxonomy для `reports/**`: working output, shared artefact, plan
  bundle, trash/deletion candidate и legacy snapshot.
- Published страницы MAY ссылаться на `reports/**` только как на
  repository-path evidence reference.
- Если `reports/**` содержит вывод, который должен стать обязательным для
  operator или contributor workflow, этот вывод MUST быть перенесён в
  `docs/00-05/**` до того, как на него начнут опираться как на guidance.

## Обязательные шаблоны

Published doc families MUST опираться на живые шаблоны из
[Template Index](../../04-reference/templates/index.md).

| Template type                 | Canonical file                                                        | Назначение                                                  |
| ----------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------- |
| `adr`                         | `docs/04-reference/templates/adr-template.md`                         | Архитектурное решение                                       |
| `runbook`                     | `docs/04-reference/templates/runbook-template.md`                     | Операционная процедура                                      |
| `provider-spec`               | `docs/04-reference/templates/provider-spec-template.md`               | Спецификация внешнего провайдера                            |
| `pipeline-spec`               | `docs/04-reference/templates/pipeline-spec-template.md`               | Спецификация пайплайна                                      |
| `data-contract-spec`          | `docs/04-reference/templates/data-contract-spec-template.md`          | Контракт данных / published schema contract                 |
| `control-plane-contract-spec` | `docs/04-reference/templates/control-plane-contract-spec-template.md` | Контракт feature-flagged control-plane / inspection surface |

`data-contract-spec` является нормативным именем семейства для published data
contracts; legacy label `contract-spec` MAY использоваться как краткий alias,
если он не вносит двусмысленность.

## Общий контракт published страницы

Каждая published governance/reference page SHOULD содержать или явно
подразумевать:

- заголовок и идентичность документа;
- `Version`, `Status`, `Class`, `Owner`, `Reviewers`, `Last verified`;
- область применимости;
- воспроизводимые команды и ожидаемые результаты, если документ описывает
  runtime behavior;
- compatibility/compliance notes, если документ описывает provider/API/contract
  surface;
- cross-links на связанные ADR, contracts, CLI surfaces и runbooks.

Для high-signal control-plane / traceability pages SHOULD использоваться один и
тот же metadata envelope (`Version`, `Status`, `Class`, `Owner`, `Reviewers`,
`Last verified`) и относительные ссылки на смежные элементы pack, чтобы manual
audit и docs automation давали одинаковый результат.

Если published или `internal-published` страница ссылается на `repo-only`
surface, такая ссылка MUST оформляться как repository-path reference, а не как
обычная built-site markdown navigation link.

## Traceability Documentation Pack

Для любого feature-flagged control-plane surface или inspection surface MUST
поставляться complete traceability documentation pack.

Под такими surfaces понимаются, например:

- immutable manifest / append-only ledger surfaces;
- inspection CLI для manifest, ledger, lineage или effective-config artifacts;
- file-backed control-plane stores и связанные operator-facing contracts;
- rollout-controlled traceability features, влияющие на воспроизводимость
  запуска и инспекцию исполнения.

Traceability documentation pack MUST включать:

1. active ADR с решением, rollout boundary и rationale;
1. published contract doc или `control-plane-contract-spec`;
1. published CLI reference либо нормативную CLI-секцию;
1. published runbook для операторской диагностики и эскалации;
1. двусторонние cross-links между ADR, contract, CLI и runbook;
1. воспроизводимые команды и storage paths, совпадающие с реальным runtime.

Если surface feature-flagged, документация MUST явно фиксировать:

- rollout flags и default values;
- disabled semantics и partial rollout behavior;
- storage layout;
- invariants;
- inspection CLI;
- verification path;
- incident/escalation anchors, если surface operator-facing.

## Правило согласованности ADR ↔ contract ↔ CLI ↔ runbook

Для published contract-bearing surfaces MUST соблюдаться явная согласованность:

- ADR MUST ссылаться на published contract doc и operator guidance;
- contract doc MUST ссылаться на ADR, CLI reference/inspection commands и
  runbook;
- CLI reference и runbook MUST ссылаться на тот же contract doc и тот же ADR;
- runbook MUST использовать те же terms, flag names, storage paths, invariants
  и inspection commands, что и contract doc и CLI.

Если одна из четырёх surfaces расходится по терминологии, флагам, путям или
инвариантам, change set считается incomplete.

## Обязательные секции для control-plane contracts

Каждый published control-plane contract MUST явно фиксировать:

1. `Rollout Flags`
   - точные config keys;
   - default values;
   - enabled/disabled semantics;
   - partial rollout behavior;
   - compatibility constraints между flag-ами.
1. `Storage Layout`
   - канонические файловые или табличные пути;
   - sidecar, index и lookup anchors;
   - ownership и resolution semantics.
1. `Invariants`
   - immutable / append-only guarantees;
   - identity lookup guarantees;
   - correlation guarantees между artifacts.
1. `Inspection CLI`
   - canonical commands;
   - supported identifiers;
   - expected output modes для human/machine inspection.
1. `References`
   - active ADR;
   - CLI reference;
   - runbook;
   - related guide или operator-facing reference при необходимости.

## RunManifest / RunLedger как нормативный пример

В текущем published documentation pack canonical control-plane surface уже
представлен published документами:

- [ADR-044: Run Manifest and Run Ledger Control Plane](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md);
- [Run Manifest and Run Ledger Contract](../../04-reference/contracts/run-manifest-ledger.md);
- [CLI Reference](../../04-reference/cli.md);
- [Run Manifest Inspection](../../05-operations/runbooks/run-manifest-inspection.md).

Этот published pack считается reference example для
`control-plane-contract-spec`, потому что он уже фиксирует:

- `run_manifest_enabled`;
- `run_ledger_enabled`;
- `checkpoint_compatibility_policy`;
- file-backed storage layout under `data/output/control/...`;
- invariants `immutable manifest`, `append-only ledger`,
  `run_id -> manifest_id`;
- inspection CLI `bioetl run-manifest show` и `bioetl run-manifest diff`.

## Требования к control-plane и inspection changesets

Если change set затрагивает control-plane, inspection или traceability surface,
он MUST:

- сначала сверяться с существующими code seams и published docs;
- не вводить новый runtime surface только ради документации;
- актуализировать docs и CI только после сверки с текущими ports, services, CLI
  и runbooks;
- сохранять детерминированность, идемпотентность и совместимость с текущими
  DQ/strict-validation правилами.

Для control-plane changesets SHOULD выполняться совместное review по
Architecture + Ops, если меняются invariants, rollout flags или inspection
workflow.

## Style Guide

- Нормативные требования SHOULD формулироваться через `MUST`, `SHOULD`, `MAY`.
- Формулировки MUST быть однозначными, проверяемыми и привязанными к
  репозиторным источникам истины.
- Команды SHOULD указывать ожидаемый runtime profile или контекст, если без
  него поведение неоднозначно.
- Примеры MUST отражать текущий CLI и текущую config topology, а не legacy
  команды или старые пути.

## Quality Gates

Перед merge change set, затрагивающего documentation governance, templates или
control-plane contract docs, MUST быть выполнено:

```bash
python scripts/docs/check_doc_links.py
python -m scripts.docs build-site --strict
```

Для drift-sensitive documentation surfaces SHOULD дополнительно выполняться:

```bash
python scripts/docs/check_doc_drift.py
```

Если меняются template entrypoints или governance cross-links, SHOULD
дополнительно проверяться связность:

- `mkdocs.yml`;
- `docs/00-project/00-map.md`;
- [Documentation Publication Policy](06-doc-publication-policy.md);
- [Template Index](../../04-reference/templates/index.md).

## Merge Checklist

- Canonical Markdown version D-01 находится в governance path и опубликована в nav.
- Related links разрешаются и не ведут на historical copy как source of truth.
- `data-contract-spec` и `control-plane-contract-spec` отражены в template index.
- Для control-plane surface согласованы ADR ↔ contract ↔ CLI ↔ runbook.
- Для feature-flagged surface явно перечислены rollout flags, storage layout,
  invariants и inspection CLI.

## Связанные документы

- [Project Map](../00-map.md)
- [Documentation Publication Policy](06-doc-publication-policy.md)
- [Documentation Navigation Policy](07-doc-nav-policy.md)
- [Template Index](../../04-reference/templates/index.md)
- [ADR-043: Documentation Knowledge Management](../../02-architecture/decisions/ADR-043-documentation-knowledge-management.md)
- [ADR-044: Run Manifest and Run Ledger Control Plane](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [ADR-045: Data Quality Contract System](../../02-architecture/decisions/ADR-045-dq-contract-system.md)
- [Run Manifest and Run Ledger Contract](../../04-reference/contracts/run-manifest-ledger.md)
- [CLI Reference](../../04-reference/cli.md)
- [Run Manifest Inspection](../../05-operations/runbooks/run-manifest-inspection.md)
