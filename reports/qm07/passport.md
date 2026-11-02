# Паспорт закрытия issue #12388

**Цель:** Доказать cold imports, корректность root и изоляцию установленного runtime (Quality Move QM-07).

**Результаты:**
1. Разделены три окружения (Source CANDIDATE, sdist, установленный runtime wheel). Wheel установлен в изолированный `wheel_venv` (вне `system-site-packages`).
2. Проведены **Source-проверки**:
   - Все 30 новых модулей и facade из `scripts.engineering.quality` импортированы отдельно из временного `cwd`. Проверено отсутствие shadowing и ошибок eager `__init__`.
   - Проверены root/path seams (`architecture_debt_reduction` и др.) и корректный fallback на repository root из внешнего cwd.
   - Проверен `debt_governance_gate_evaluators` (отсутствие None bindings при импорте).
3. Проведен **Runtime wheel smoke**:
   - Wheel установлен из `dist/` в `wheel_venv`.
   - Проведен smoke-тест без путей checkout и `PYTHONPATH`.
   - Установлен import hook, запрещающий любые импорты из `scripts.*`. Сам `bioetl` (например, `bioetl.application.core.runner.PipelineRunner`) загружается успешно.

Тесты написаны в `tests/architecture/test_qm07_cold_imports.py` и успешно проходят mypy и ruff, а также `uv run pytest`.
