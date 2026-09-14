# Аудит документации (docs-content)

- **Дата:** 2026-09-14T06:13:32Z
- **Prompt:** `prompt.docs.audit` (RHAI stale id `prompt.audit.docs-content`)
- **SCOPE:** `README.md docs/` (high-traffic only; не полный обход markdown)
- **MODE:** audit / AUDIT_MODE=full / LANGUAGE=ru
- **surface_score:** **1**

## Легенда surface_score (0–3, выше = лучше)

| Score | Значение |
| --- | --- |
| 3 | Критические сценарии описаны; команды проверены; ссылки/сборка закрыты автоматикой |
| 2 | Основной путь верен; есть устаревшие или неполные секции |
| 1 | Существенный drift docs↔код/CI или в основном ручные проверки |
| 0 | Критические инструкции отсутствуют, невоспроизводимы или опасно неверны |

## Executive summary

Основной onboarding-путь в `README.md`, `docs/03-guides/quick-start.md` и `docs/03-guides/getting-started.md` согласован с `Makefile`/`pyproject.toml` (Python 3.12+, uv-first extras, `python -m scripts.ops setup-plugins`, `degraded_observable`, 22 entity YAML).
Существенный drift сосредоточен в contributor/governance поверхностях: `.github/CONTRIBUTING.md` всё ещё утверждает, что прямые merge в `main` разрешены, хотя `05-github-policy.md` и `.github/workflows/pr-required.yml` фиксируют ruleset с required context `pr-gate-complete`.
Опубликованный cheatsheet `docs/03-guides/cheatsheets/cli-commands.md` содержит несуществующие `python -m scripts.*` команды (подтверждено exit 2) и wrapper-пути в корне репозитория.
Выборка markdown-ссылок: 555 локальных ссылок в 25 high-traffic файлах, битых `[](path)` нет (см. `broken-links.json`). Path-цитаты в backticks (архивный `05-engineering` plan) сканер ссылок не видит.

**Итог:** 11 PROVEN findings, из них 4 уровня P0/P1. P0 (утечки секретов / destructive prod) не найдены.

## Метод

1. Инвентарь high-traffic: README, CONTRIBUTING, CHANGELOG, 00-map, NORMATIVE_SOURCES, RULES, TOOLS, getting-started, quick-start, guides index, docs-verification, GitHub guides, runbooks index + vacuum/data-recovery, CLI, pipeline-catalog.
2. Сверка команд с `Makefile`, `pyproject.toml`, `scripts/*/__main__.py`, CLI (`quarantine`, `maintenance vacuum`, `config list-pipelines`).
3. Сверка required checks с `docs/00-project/governance/05-github-policy.md` и `pr-required.yml`.
4. Резолв относительных markdown-ссылок (выборка, не весь `docs/`).
5. Игнорирован unrelated WIP (grafana/http/tests), кроме случаев прямого противоречия с docs.
6. Генераторы/MkDocs/publish не аудировались (disjoint: docs-pipeline).

## Evidence highlights

- README Option A extras `dev,tests,tracing` совпадают с TOOLS.md; `make install` = `dev,tests,tests_full,export` — README это явно оговаривает.
- Entity count 22 + 5 composite + 7 providers совпадает с `configs/` и `pipeline-catalog.md`.
- Rate limits README ↔ `configs/providers/*.yaml` (ChEMBL 0.1/burst 1, PubChem 5, UniProt 10, PubMed 3, OpenAlex 10, S2 0.1) — без drift.
- `bioetl config list-pipelines`, `quarantine purge/inspect`, `maintenance vacuum` существуют.
- Выборка ссылок: 0 broken `[](path)` / 555 checked.

## Findings (по приоритету)

### DOCS-001 — P1 High (PROVEN)

- **path:** `.github/CONTRIBUTING.md:120-126`
- **requirement_id:** `GAP`
- **observation:** Contributor GitHub docs contradict the live main ruleset: they claim direct merges to main are allowed and treat checks-complete as the merge wall, while governance and CI require pr-gate-complete and block direct pushes.
- **remediation:** Rewrite CONTRIBUTING Branch Protection, github-quick-reference CI/Release, and github-local-workflow Required PR checks to match 05-github-policy.md: ruleset 13643213 active, required context pr-gate-complete, no git push origin main. Point release flow to a PR then tag after merge.
- **fingerprint:** `7eb84df593675019e6210a04c0a5087601c2e8d7688b4798ef558e5b50566e63`

### DOCS-002 — P1 High (PROVEN)

- **path:** `docs/03-guides/cheatsheets/cli-commands.md:563-595`
- **requirement_id:** `GAP`
- **observation:** Published CLI cheatsheet documents retired underscore script entrypoints that the current python -m scripts.* routers reject.
- **remediation:** Replace the Unified Script Entry Points block with current router names from scripts/*/__main__.py (check-naming, check-terminology, check-c901, check-links, check-drift, check-docstrings, validate-configs, lint, check-inventory). Change make clean-local-artifacts --apply to make clean-local-artifacts (Makefile already passes --apply unless DRY_RUN).
- **fingerprint:** `3a4128ad4d5cb5ec82a1cfabd5ed1bad9e0d6198e76dd454f7517fe7eeef66d5`

### DOCS-003 — P1 High (PROVEN)

- **path:** `docs/03-guides/cheatsheets/cli-commands.md:600-617`
- **requirement_id:** `GAP`
- **observation:** Cheatsheet OS wrappers are invoked from repository root (./setup_env_windows.ps1, ./setup_env_wsl.sh) but the real helpers live under scripts/engineering/dev/.
- **remediation:** Replace wrapper snippets with the canonical paths from README mixed-checkout section.
- **fingerprint:** `0a7c8f187350d45cc06117988444722315d38b818558d6bcea4978dd77ddeb3e`

### DOCS-004 — P1 High (PROVEN)

- **path:** `.github/CONTRIBUTING.md:11-16`
- **requirement_id:** `GAP`
- **observation:** CONTRIBUTING Quick Start and RULES §4.2.1 tell contributors to uv sync without tests_full then run make test / architecture-capable suites that require import-linter (tests_full extra).
- **remediation:** Change CONTRIBUTING Quick Start and RULES §4.2.1 recommended install to include --extra tests_full before make test / make lint architecture-adjacent flows. github-quick-reference.md:35 (make lint && make test) should point at make install extras or README's tests_full note.
- **fingerprint:** `7138f8301d83b91c6da8b59ff878cfbafa2405e981ee2b9383f1b4fb11929610`

### DOCS-005 — P2 Medium (PROVEN)

- **path:** `docs/00-project/RULES.md:1474`
- **requirement_id:** `GAP`
- **observation:** RULES.md and two published policy/reference pages cite docs/05-engineering/normalization_plan_P0_P6.md, which is not on that path; the file lives only in docs/99-archive/engineering/.
- **remediation:** Replace live citations with docs/99-archive/engineering/normalization_plan_P0_P6.md and label historical, matching docs/04-reference/normalization/*.
- **fingerprint:** `344020bccb36a400c8a95a1e0f35ff20333c9a0cce4c1b1c62036f96a038aaa3`

### DOCS-006 — P2 Medium (PROVEN)

- **path:** `docs/00-project/RULES.md:1474`
- **requirement_id:** `GAP`
- **observation:** RULES.md points identity hashing to domain/transformations.py:_should_include_field() and RetryConfig.calculate-delay(); the implementation is hashing.py and calculate_delay.
- **remediation:** Update RULES §6.1 Content Hash and Retry Jitter pointers to hashing.py and calculate_delay; keep policy file as SSOT for field lists.
- **fingerprint:** `c4166e5a210bba369cb4ebea82b3a8c9421b981bb71d684b058b93c94a89f1e5`

### DOCS-007 — P2 Medium (PROVEN)

- **path:** `CHANGELOG.md:8`
- **requirement_id:** `REQ-GOV-006`
- **observation:** Keep a Changelog surface is inconsistent: pyproject and README still advertise 6.1.0 (unreleased) while CHANGELOG also has a dated ## [6.1.0] - 2026-03-11 plus a large Unreleased section.
- **remediation:** Decide whether 6.1.0 already shipped. If yes, bump pyproject for current Unreleased (e.g. 6.2.0) and stop labeling README 6.1.0 unreleased. If 6.1.0 never shipped, fold or relabel the dated [6.1.0] section so it does not look released.
- **fingerprint:** `6e40af6b231486ce944c11721813268afb7101f6171e5a75da589278a4b163a3`

### DOCS-008 — P2 Medium (PROVEN)

- **path:** `docs/03-guides/index.md:33`
- **requirement_id:** `GAP`
- **observation:** Guides index still presents github-setup-plan.md as a comprehensive GitHub setup guide, but that file is an archived-pointer (Status: archived-pointer, Class: repo-only).
- **remediation:** Retarget the Common Entry Points row and Role Boundaries paragraph to github-local-workflow.md; mention the pointer only as archive.
- **fingerprint:** `227fdaa3c710af364efddf6b676a669257aca543565c8a375a6361bddbc06fe5`

### DOCS-009 — P2 Medium (PROVEN)

- **path:** `docs/03-guides/file-path-audit-report.md:1-18`
- **requirement_id:** `GAP`
- **observation:** A January 2026 file-path audit report is published as Class: published / Status: active in docs/03-guides/, next to live how-to guides.
- **remediation:** Move to docs/99-archive/ or reports/docs-evidence/, add archive banner, or change Status/Class to archived and stop treating it as a guide.
- **fingerprint:** `33b519c79f64a8382aeb3c0aab102da6ec890afc7b05a0c42daaddb4126ef283`

### DOCS-010 — P3 Low (PROVEN)

- **path:** `.github/CONTRIBUTING.md:26-34`
- **requirement_id:** `GAP`
- **observation:** CONTRIBUTING markdown tables use a leading extra pipe (||) so Essential Reading, layer-dependency, and testing tables do not render as tables.
- **remediation:** Remove the extra leading | on those three tables.
- **fingerprint:** `366906c0910294ba6a24fb8a5b71755a8e99e41694464491147839c63dea5fbf`

### DOCS-011 — P3 Low (PROVEN)

- **path:** `docs/00-project/RULES.md:1146`
- **requirement_id:** `GAP`
- **observation:** RULES §4.2.1 still lists pytest>=8.0 / pytest-asyncio>=0.23 / vcrpy>=6.0 while pyproject.toml pins pytest>=9.0.3, pytest-asyncio>=1.4, vcrpy>=8.2.1.
- **remediation:** Replace version floors in RULES §4.2.1 with a pointer to pyproject.toml extras, or copy current bounds.
- **fingerprint:** `877810b9e522a9b591eb2ba6af9284b87e8abcfb015f5d2609b5900a637c6d92`

## Top remediations

1. Синхронизировать `.github/CONTRIBUTING.md`, `github-quick-reference.md`, `github-local-workflow.md` с `05-github-policy.md`: `pr-gate-complete`, запрет `git push origin main`.
2. Переписать блок Unified Script Entry Points и OS wrappers в `docs/03-guides/cheatsheets/cli-commands.md` под актуальные kebab-case routers и `scripts/engineering/dev/`.
3. Добавить `--extra tests_full` в CONTRIBUTING Quick Start и RULES §4.2.1 перед `make test`.
4. Заменить живые цитаты `docs/05-engineering/normalization_plan_P0_P6.md` на `docs/99-archive/engineering/normalization_plan_P0_P6.md`.
5. Закрыть Keep-a-Changelog рассинхрон `[Unreleased]` vs датированный `[6.1.0]` vs `pyproject.toml` 6.1.0.

## Skipped / out of scope

- Полный обход всех markdown в `docs/` (запрещено карточкой; focus high-traffic).
- MkDocs build, generators, publish pipeline (`prompt.audit.docs-pipeline`).
- Grafana/HTTP/tests WIP на working tree, если не противоречит docs.
- Внешние URL (GitHub badges, keepachangelog.com) — не резолвились по сети.
- `REQUIRE_GH_TRACKING=false` — GitHub Issues не создавались.

## Checks run

- `python -m scripts.engineering.qa naming_check` @ 2026-09-14T06:13:32Z exit 2 (Unknown command).
- `python -m scripts.docs link_check` @ 2026-09-14T06:13:32Z exit 2 (Unknown command).
- Sampled markdown link resolver: 555 local links, 0 broken (25 files).
- Path existence: entity YAML 22, providers 7, composites 5, vacuum CLI, docker-compose.monitoring.yml (Loki/Tempo removed — README claim holds).

Временный `_scan_links.py` / `_write_artifacts.py` не являются deliverable; оставлять только `report.md`, `findings.json`, `broken-links.json`.

