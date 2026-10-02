# Локальная проверка остатков аудита #11856–#11859

Дата: 2026-10-02. Ветка: `fix/audit-p2-closeout-20261002`.
База: `0e2114a121d8f4707b6dfd57953d2056b92297a2`.
Scope: актуальные строки четырёх issues аудита 2026-09-30; без новых
архитектурных программ, запуска monitoring и повышения бюджетов долга.

Большинство исходных исправлений уже находится в базе. Эта ветка завершает
их проверку, исправляет обнаруженные пробелы и связывает generated artifacts
с текущими входами. Это локальные доказательства, не заявление о merge или
закрытии GitHub issues. `proof_or_stop_policy.yaml` ограничивает
`local_single_host` результатом `DEGRADED`; для lifecycle closeout нужен `ADMIT`.

## Карта покрытия

| Issue / ID | Текущее решение и источник доказательства |
| --- | --- |
| #11856 AUD-005 | `DEVIN-RUNTIME.md` явно разрешает `swe-1.6` только write-профилям; pin py-config-bot соответствует этому исключению. Read-only профили наследуют parent. |
| #11856 AUD-009 | `.junie/guidelines.md` содержит OpenCode-секцию, disabled installer/write-path ограничения и ссылку на AGENTS.md. |
| #11856 AUD-008 | Deprecated orchestration alias вычищен до pointer; исторические имена упомянуты лишь в пояснении удаления. |
| #11857 DIAG-01-PORTS-OVERCLAIM | `01-domain-ports.mmd`: scoped header, ссылки на 01a/90-pkg, `@nodes 23`. |
| #11857 DIAG-01-HEX-ORPHANS | CFG/OBSERVER/PROVIDERS/SCHEMAS/VALIDATION связаны; TYPES/EXCEPTIONS оставлены как явно документированный ambient vocabulary. Orphan-check теперь анализирует многострочный Mermaid init, а не молча пропускает файл. |
| #11857 DIAG-CI-NIGHTLY-DISABLED | Ограничение full-corpus/nightly перенесено в canonical `governance/policy.md`; disabled jobs не объявляются успешными gates. |
| #11857 DIAG-PNG-POLICY-DRIFT | Compliance map и canonical policy различают tracked SVG и untracked PNG; routing согласован с render-retention. |
| #11857 DIAG-90PKG-NO-DRIFT-GATE | Canonical policy фиксирует supplemental/non-CI scope 90-pkg и ручную регенерацию; обязательные source/SVG drift gates сохранены. |
| #11857 DIAG-README-PNG-INDEX | `README.md` больше не публикует gitignored png/INDEX.md как supplementary index. |
| #11857 DIAG-UQ-NAMING | Узел в `13-port-protocol-contracts.mmd` называется UnifiedQuarantineAdapter. |
| #11857 DIAG-013-REF-SLICES | `@reference` содержит 13a–13i. |
| #11857 DIAG-LINT-DOC-STALE-PATH | Usage linter указывает на canonical architecture/01-high-level-hexagonal.mmd. |
| #11857 DIAG-DUP-FIX-OPERATORS | Корневого дубля нет; CLI маршрутизирует в fix/fix_mermaid_operators.py. |
| #11857 DIAG-12-EMOJI-NODES | Local deployment source не содержит emoji labels. |
| #11857 DIAG-DOCKER-TAG-NO-DIGEST | Wrapper содержит tag 10.6.1 и 64-символьный SHA-256 digest; regression guard требует оба. |
| #11858 DOCS-PIPE-001 residual | Verify явно документирует исключение providers/glossary; --ai-surfaces включён. |
| #11858 DOCS-PIPE-002 | Panel inventory --check включён в verify/docs.yml; два устаревших shipped-panel блока обновлены генератором. Missing approved output root исправлен в generated_artifact_routing.yaml. |
| #11858 DOCS-PIPE-003 | KPI workflow объявлен optional-but-scheduled; stale KEEP-DISABLED утверждение снято. |
| #11858 DOCS-PIPE-004 | Неиспользуемые mkdocs-mermaid2-plugin/mkdocstrings extras удалены из pyproject.toml. |
| #11858 DOCS-PIPE-005 | Parity guide документирует фактический scripts.data_quality check-entity-config-parity. |
| #11858 DOCS-PIPE-006 | REQ-DOC-001 в crosswalk требует полный check-links. |
| #11858 DOCS-PIPE-007 | GEMINI.md удалён из docs workflow path contract. |
| #11858 DOCS-PIPE-008 | Неиспользуемая ROLE_PROFILE_MEMO_DOC_BY_RUNTIME удалена; комментарий поясняет причину. |
| #11858 DOCS-PIPE-009 | После отдельного полного check-links workflow вызывает verify --skip-links. |
| #11858 DOCS-PIPE-010 | Legacy scripts помечены non-CI в коде/гайде и теперь имеют соответствующие lifecycle decisions compatibility_wrapper / legacy_manual_utility. Active scripts: 338, cap: 338. |
| #11859 ARCH-005 | Scanner census исправлен: live composition 282; snapshot coverage 2521 rows против live 2541 файлов не выдаётся за полное измерение. |
| #11859 ARCH-007 | CLI catalog содержит archive/cleanup/report/vacuum/workflow, описание selected-run ADR-061; слой перепроверен 2026-10-02. |
| #11859 ARCH-008 | В базе фабрика уже собирает shared RunReportStorePort однократно, query callers передают ссылку через store=. Повторные обращения не создают новый адаптер; 3 singleton tests и 76 CLI/HTTP report tests прошли. Сохранён текущий sanctioned composition API. |
| #11859 ARCH-009 | Overview имеет Last verified 2026-10-01 и актуальное описание слоёв; повторная сверка проведена в этой работе. |
| #11859 ARCH-010 | Opening infrastructure описывает local filesystem/provider HTTP/Delta/optional Prometheus, brokers/remote DB — historical context. |
| #11859 ARCH-011 | Composition live count 282, scorecard 282, budget-comment 282/295; max_modules=295 неизменен. |

## Дополнительные исправления для валидации

- Mermaid orphan detector пропускал continuation lines в многострочном init
  только частично и определял type=unknown. Исправлено; 4 regression cases
  включают реальный high-level source и graph/flowchart/sequence declarations.
- В inherited тестах исправлены отсутствующие unit/integration markers и
  два duplicate names в quarterly-targets tests. Поведение тестов не изменено.
- Lifecycle/integration-VCR inventories и CI drift families обновлены
  каноническими генераторами; бюджетные cap/threshold значения не повышены.

## Доказательства и ограничения

- 123 связанных architecture/unit/integration tests: PASS.
- 76 CLI/HTTP report tests: PASS.
- 25 generated-routing/catalog tests: PASS; 2 Windows full-walk tests SKIP.
  Эквивалентный catalog CLI проверяется напрямую pretest-guardrails.
- `ruff check` для изменённых Python-файлов: PASS.
- `scripts.docs verify`, включая полный check-links, drift, panel inventory,
  docstrings, cleanup inventory, normalization matrix и strict MkDocs: PASS.
- Codex–Junie mirror parity: PASS; runtime sources в этой ветке не менялись.
- Targeted diagram lint: 4/4 PASS, 0 errors, 5 существующих warnings о размере,
  длинном label и method signature. Orphan-check: 1 файл, 0 orphan nodes.
- Debt gates: 46 PASS / 0 FAIL / 0 WARN после canonical refresh.
- Source-bound execution receipts и итог verifier сохраняются в
  `reports/quality/proof-or-stop/audit-p2-11856-11859-20261002/`.

Полный pytest/17-shard coverage не запускался: product Python-код не изменён;
coverage completion относится к отдельной программе. Coverage snapshot/live
gap зафиксирован честно, без подстановки процентов или повышения лимитов.
Полный diagram render/nightly не запускался: Mermaid sources не менялись,
accepted CI residuals сохранены. Preflight cache cleanup отключён, memory
pre-task выполнен read-only отдельно; post-task также использует read-only.

Требуемое продолжение для GitHub lifecycle closure: publish/review этой ветки,
source-bound проверка на том же коммите в разрешённом trust tier, ADMIT,
затем merge и закрытие issues. Локальная ветка не публикуется автоматически.
