# Паспорт QM-07 / issue #12388

**Цель:** Доказать cold imports, корректность root seams и изоляцию установленного runtime wheel.

**Статус:** source cold imports, root seams и installed-wheel smoke закрыты harness'ом `tests/architecture/test_qm07_cold_imports.py`.

**Harness:** `uv run --frozen --no-build pytest -m architecture tests/architecture/test_qm07_cold_imports.py`  
Ожидаемый итог: exit code `0`, все сценарии ниже зелёные.

## 1. Source CANDIDATE

**Команда (эквивалент теста):** дочерний процесс  
`python -I -c '<prelude sys.path=[src, repo_root]; importlib.import_module(M); print(json.dumps(module.__file__))'`  
с `cwd=<tmp_path>` (не checkout).

| Сценарий | Ожидаемый exit | Проверка |
| --- | --- | --- |
| Cold import каждого из 30 модулей + facade `scripts.engineering.quality` | `0` | `Path(module.__file__).resolve()` == checkout `scripts/engineering/quality/<name>.py` (или `__init__.py` для facade) |
| Root seams из внешнего cwd (`_project_root` / `PROJECT_ROOT` / `project_root`) | `0` | все roots == checkout `REPO_ROOT`; есть `pyproject.toml` + `scripts/` |
| Path/error: `build_module_path_key("/tmp/not-in-repo.py")` | `0` (AssertionError внутри → fail теста) | ожидаемый `ValueError` с `"module_path must resolve"` |
| Evaluator bindings `debt_governance_gate_evaluators` | `0` | три имени не `None` и `callable` |
| `load_debt_scorecard` + `evaluate_debt_scorecard` | `0` | scorecard — непустой `dict`; violations — `list` |
| `build_architecture_quality_scorecard()` (без `main()`) | `0` | payload содержит schema/metrics; tracked reports не пишутся |

## 2. Installed runtime wheel

**Fixture `wheel_venv_python` (session):** child env без `UV_NO_BUILD`/`UV_NO_SYNC`, timeout 600s на шаг:

1. `uv build --wheel -o <tmp>/dist` → exit `0`, ровно один `bioetl-*.whl`
2. `uv venv <tmp>/wheel_venv --python <sys.executable>` → exit `0`
3. `uv pip install --python <venv>/bin/python <wheel>` → exit `0`

**Smoke (cwd=tmp, без `PYTHONPATH`, interpreter = venv python `-I`):**

| Сценарий | Ожидаемый exit | Проверка |
| --- | --- | --- |
| `import bioetl` + `PipelineRunner` при meta_path blocker на `scripts.*` | `0` | `bioetl.__file__` под `site-packages` |
| `import scripts.engineering` при том же blocker | ≠ `0` | stderr содержит `Attempted to import scripts` |

Известные source blockers quality→scripts по-прежнему в `tests/architecture/qm_07/test_qm07_cold_imports.py` (отдельный inventory; не отменяет wheel smoke для runtime package).
