# tests-system

- prompt: `prompt.audit.tests-system`
- surface_score: **2**
- proven: 5; P0/P1: 0
- run_id: `20260924T183653Z-9d9d303fa3f6-e28b4aa3`

Стек подтверждён: Python >=3.12 (3.12/3.13), pytest в pyproject.toml, pytest.ini нет. Merge wall — pr-gate-complete; гейт tests (always_required) гоняет tests.yml: unit 3.12/3.13, integration, security, offline contract-confidence, coverage-verify --fail-under=85 и branch min 85 (порог из репозитория). Архитектура блокируется lint-arch. xfail в продуктовых тестах нет; curated flaky пуст. e2e-smoke и полный e2e вне каталога required checks; live-контракты — monthly schedule. Оценка 2: основные слои CI блокирует, сигнал e2e_smoke и flaky-наблюдаемость неполные.

## Findings

- **TST-001** P2 PROVEN `pyproject.toml:236` — Маркер e2e_smoke описан как PR-blocking, тогда как каталог required checks и политика не включают e2e-matrix-health в pr-gate-complete.
- **TST-002** P2 PROVEN `.github/workflows/e2e-matrix-health.yml:221` — Полный offline e2e replay не исполняется на pull_request: job e2e-nightly-full-replay ограничен schedule и workflow_dispatch.
- **TST-003** P2 PROVEN `tests/architecture/test_fix_mermaid_operators.py:161` — Два вызова mounted_worktree_skip_reason не входят в architecture_platform_skips, а guard сравнивает инвентарь только с жёстким набором из четырёх путей.
- **TST-004** P2 PROVEN `.github/workflows/tests.yml:321` — Блокирующий flaky-telemetry повторяет только два модуля на трёх seed и не даёт repeat-count по остальному suite.
- **TST-005** P3 PROVEN `docs/00-project/governance/05-github-policy.md:364` — Политика и комментарий tests.yml называют job test-matrix path-scoped и not always-on, хотя гейт tests в каталоге always_required и на каждом PR вызывает весь tests.yml.

## Remediations

- Выровнять маркер e2e_smoke с политикой: это PR-спутник, не merge wall, пока e2e-matrix-health нет в github_required_checks.yaml.
- Для полного e2e явно пометить nightly-only в матрице слоёв либо ввести узкий блокирующий replay в гейт tests.
- Дописать два Windows/WSL skip в architecture_platform_skips и проверять все вызовы mounted_worktree_skip_reason.
- Не трактовать flaky-telemetry из двух модулей и пустой curated inventory как доказательство стабильности всего suite.
- Исправить формулировку path-scoped/not always-on для test-matrix: на PR job входит в always_required гейт tests.
