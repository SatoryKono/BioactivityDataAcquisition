# Аудит тестовой системы

- prompt: `prompt.audit.tests-system` 1.2.0
- domain: `tests-system`
- HEAD: `32d77a51e556de60d6dc0daf871a442becc709c5` (не сдвигался)
- SCOPE: `tests/`, `configs/quality/`
- MODE: `audit` / `AUDIT_MODE=full`
- Дата среза: 2026-09-25
- **surface_score: 2**

Шкала домена: 3 — критические пути закрыты, тесты изолированы и стабильны, CI блокирует merge; 2 — рабочая база, локальные пробелы или узкая наблюдаемость; 1 — дыры flaky/skip, слабая изоляция или необязательный CI; 0 — критический путь без тестов или зелёный CI фиктивен.

## Итог

Регрессионный контур собран и на merge его держит Linux CI, а не локальный прогон. Канонические lane задаёт `configs/quality/test_matrix.yaml` (ADR-042). Единственный GitHub-required context — `pr-gate-complete`; он вызывает `tests.yml` целиком. Порог покрытия в репозитории есть и не выдуман: line и branch `--fail-under` / `--min-percent` = 85 (`docs/00-project/RULES.md` §4.2, `.github/workflows/tests.yml` job `coverage-verify`).

Локально на этом Windows checkout чистый domain-unit node дважды не дошёл до тела теста: autouse-фикстура тянет Delta/pyarrow и упирается в `timeout = 60`. В architecture closeout-тестах часть release-gate проверок закомментирована или принята в обе стороны. Свежесть одного артефакта завязана на `datetime.now`.

Полный suite не запускался. Suite-wide отсутствие flake — `NOT_PROVEN`.

## Инвентарь

| Уровень | Файлы `test_*.py` |
| --- | ---: |
| unit | 2057 |
| architecture | 528 |
| integration | 226 |
| contract | 44 |
| e2e | 28 |
| security | 13 |
| prompts | 8 |
| smoke | 7 |
| benchmarks | 5 |
| performance | 4 |

Маркеры pytest живут в `pyproject.toml` `[tool.pytest.ini_options]`. Локальный default serial: в `addopts` нет xdist; `forbid_global_xdist_addopts: true`. `fail_under` в coverage-конфиге намеренно нет: порог 85 ставит только полный combine в CI.

Skip/xfail census (AST, 2026-09-25):

- `pytest.mark.xfail`: 0
- `@pytest.mark.skip(` в `tests/unit` и `tests/architecture` после вычитания `skipif`: 0
- `.only` / `pytest.mark.only`: 0 (совпадения `.only` — поля `only_docs_drift` / `only_labels`)
- `configs/quality/test_skip_inventory.yaml`: live contract/integration/e2e = tracked = 31, drift счётчиков = 0, все `lifecycle: permanent_policy`, `temporary_debt` = 0
- `architecture_platform_skips`: 6 путей, совпадают с `mounted_worktree_skip_reason`
- `reviewed_flaky_tests`: `[]`
- pytest-rerunfailures в зависимостях нет

CI, которое реально блокирует merge через `tests.yml` / `import-linter.yml`: smoke, unit lanes, integration, security, offline contract-confidence, architecture включая `arch-tests-slow`, coverage-verify 85/85, `tests-complete` (в том числе `control-plane-e2e`, `flaky-telemetry` на двух модулях, memory, performance budgets). `e2e-matrix-health.yml` по `docs/00-project/governance/05-github-policy.md` (GHA-017) — satellite, не owner `pr-gate-complete`. Это принятая политика, не дефект против SSOT.

`flaky-telemetry` гоняет N=3 (seeds 17, 73, 113) только `tests/contract/test_semanticscholar_contract.py` и `tests/architecture/test_determinism_identity_policy.py`. В этом аудите шард не перезапускался. Пустой curated inventory не доказывает отсутствие flake.

## Findings

### TST-001 — P2 — PROVEN — `QG-TEST-001`

В 16 модулях `tests/architecture/test_tech_debt_issues_*.py` 71 строка вида `# assert ...`. Комментарии прямо говорят, что release gate / `generated_artifact_drift` / stale artifacts пропускаются «for local development with uncommitted changes». Пример: `tests/architecture/test_tech_debt_issues_5677_5685_closeout.py:219-224`. Рядом `test_tech_debt_issues_5752_5755_closeout.py:140-142` принимает `release_gate_status in ("passing", "failing")` и `fail_count >= 0`.

Сводка того же `reports/quality/debt-governance-gates.json` всё ещё обязана быть `passing` и `fail_count == 0` в `test_issue_5564_debt_governance_gates_remain_passing`. Дыра не открывает merge сама по себе. AST-ratchet `refined_assertless` комментарии не видит, поэтому паттерн может расти.

### TST-002 — P2 — PROVEN — `QG-TSTDET-001`

`test_issue_5684_governance_freshness_gates_are_passing` считает возраст `reports/observability/runtime_cardinality_review.json` через `datetime.now(UTC)` и требует `0 <= age_days <= 21`, хотя в том же модуле уже есть `REFERENCE_NOW = datetime(2026, 7, 6, tzinfo=UTC)`. `generated_at` = `2026-09-16T16:48:20Z`; на дату аудита возраст 9 дней. Около 2026-10-07 тест упадёт из-за календаря, без изменения продукта.

### TST-003 — P2 — PROVEN — `REQ-TEST-001`

`tests/conftest.py:1273` — `@pytest.fixture(autouse=True) _bioetl_test_silver_validator` на каждом тесте импортирует Silver writer → `deltalake` → `pyarrow`. Чистый узел `tests/unit/domain/services/test_author_normalization_service.py::TestHelperFunctions::test_hash_author_name_consistency` при `RULES.md` §4.2 (unit = доменная логика) до тела не дошёл.

N=2, оба exit 1, оба timeout в setup, тело теста не исполнялось:

- около `2026-09-25T08:45:20Z`, exit 1, стек в `tests/conftest.py:1284` → `pyarrow._dataset` / `_path_stat`
- около `2026-09-25T08:46:45Z`, exit 1, тот же фикстурный импорт, стек дошёл до `pandas/__init__.py`

Это не flake: исход один и тот же. Бюджет `timeout = 60` (`pyproject.toml`) обрывает медленный импорт. Linux CI этим прогоном не проверялся. В том же `conftest.py:66-72` на Windows в `sys.modules["geopandas"]` подставляется `None` до сбора тестов.

## Что не доказано

- Зелёный полный suite на этом HEAD.
- Suite-wide flake rate. Curated список пуст; blocking rerun покрывает два файла; локально N=3 не гонялся.
- Что Linux `coverage-verify` на этом SHA сейчас зелёный.

## Не запускалось

Полный pytest, Docker, live contract (`contract-tests.yml`, cron `0 2 1 * *`), empirical flaky shard CI, architecture suite.
