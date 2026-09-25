# Аудит тестовой системы

Прогон: локальная сверка конфигурации и деревьев, без полного pytest tests/.
Балл поверхности: **2**.

## Что реально блокирует merge

Единственный required context — pr-gate-complete. Гейт 	ests в configs/quality/github_required_checks.yaml имеет decision: always_required и владельца .github/workflows/tests.yml (smoke-check, governance-preflight, test-fast, test-matrix, coverage-verify). Допустимый результат только success.

Порог покрытия задан проектом и не выдуман здесь: 85% строк (coverage report --fail-under=85) и 85% веток (check-branch-coverage --min-percent 85). В pyproject.toml ail_under намеренно не задан, чтобы частичные шарды не падали.

Локальный pytest серийный: ddopts без xdist, benchmark выключен. Таймаут 60 с. --strict-markers включён. pytest.mark.only в 	ests/ не найден.

## Уровни

Файлы 	est_*.py: unit 2057, architecture 530, integration 226, contract 44, e2e 28, security 13, prompts 8, smoke 7, benchmarks 5, performance 4. Отдельных 	ests/migration и 	ests/api нет. Контракты API живут в 	ests/contract и в фасадных architecture-тестах.

2e_smoke по маркеру и 	est_matrix.yaml не является required-контекстом GitHub. Полный e2e replay — nightly. Это зафиксированная политика, не новая находка.

## Пропуски и flaky

configs/quality/test_skip_inventory.yaml: 37 записей, все permanent_policy, владелец есть. Временного долга в этом инвентаре нет. Юнит-пропуски инвентарь явно не покрывает.

Повторных прогонов подозрительных тестов не было (N=0). Ничего не помечено flaky.

Hotspot performance-бюджет в 	ests.yml падает, если нет observations или degradation JSON. Это уже в дереве, патч не предлагается повторно.

## Находка

TESTS-UNIT-SKIP-001 (P2, PROVEN, уверенность medium). В 	ests/unit 120 упоминаний pytest.mark.skip или pytest.skip(, 0 xfail. Инвентарь их не ведёт. Не доказано, что это безусловные skip.

Предлагаемый патч, не применён: расширить 	ests/architecture/test_test_skip_inventory.py, чтобы безусловный skip в 	ests/unit попадал в инвентарь, а skipif оставался допустимым.

## Команды сверки

- Подсчёт 	est_*.py по верхним каталогам 	ests/.
- Разбор 	est_skip_inventory.yaml.
- Поиск pytest.mark.only — пусто.
- Чтение pyproject.toml, github_required_checks.yaml, 	ests.yml, pr-required.yml.
