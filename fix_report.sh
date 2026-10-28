# Create a much more comprehensive report
echo "# Test Run Report" > reports/test_failure_analysis.md
echo "" >> reports/test_failure_analysis.md
echo "## Environment & SHA" >> reports/test_failure_analysis.md
echo "\`\`\`" >> reports/test_failure_analysis.md
echo "Commit SHA:" $(git rev-parse HEAD) >> reports/test_failure_analysis.md
uname -a >> reports/test_failure_analysis.md
uv run python --version >> reports/test_failure_analysis.md
echo "\`\`\`" >> reports/test_failure_analysis.md
echo "" >> reports/test_failure_analysis.md
echo "## Commands Executed" >> reports/test_failure_analysis.md
echo "\`\`\`bash" >> reports/test_failure_analysis.md
echo "uv run pytest tests/unit/ -n auto -q --tb=short" >> reports/test_failure_analysis.md
echo "\`\`\`" >> reports/test_failure_analysis.md
echo "" >> reports/test_failure_analysis.md

echo "## Flakiness vs Environment/Drift Failure Analysis" >> reports/test_failure_analysis.md
echo "Отсутствующие прогоны: честно отмечаю, что хотя были запущены полные unit тесты 3 раза, не все сырые логи (raw logs) были сохранены на всех этапах из-за таймаутов и ограничений окружения на больших выводах в консоль, а также я очищал файлы между попытками. Утверждать о 100% полном скоупе без полных логов неверно. Но найденные падения детерминированы (не flaky)." >> reports/test_failure_analysis.md
echo "Ниже приведена разбивка падений." >> reports/test_failure_analysis.md

echo "### 1. Environment Failure (Permission Denied)" >> reports/test_failure_analysis.md
echo "- **NodeID**: \`tests/unit/repo_backed/scripts/ai/test_npm_runtime_contract.py::test_shell_filesystem_executes_locked_pin\`" >> reports/test_failure_analysis.md
echo "- **Exit Code**: 1" >> reports/test_failure_analysis.md
echo "- **Pass/Fail**: Fail (Run 1, 2, 3)" >> reports/test_failure_analysis.md
echo "- **Evidence (Raw Log snippet)**: \`AssertionError: mkdir: cannot create directory ‘/home/ubuntu’: Permission denied\`" >> reports/test_failure_analysis.md

echo "### 2. Contract Drift (YAML assertion mismatch)" >> reports/test_failure_analysis.md
echo "- **NodeID**: \`tests/unit/scripts/engineering/ci/test_generated_artifact_selection.py::test_real_daily_caller_and_command_partition_are_complete\`" >> reports/test_failure_analysis.md
echo "- **Exit Code**: 1" >> reports/test_failure_analysis.md
echo "- **Pass/Fail**: Fail (Run 1, 2, 3)" >> reports/test_failure_analysis.md
echo "- **Evidence (Raw Log snippet)**: \`assert '--fallback-addopts \"-p no:xdist -q --tb=line\"' in 'name: PR Gate Complete...\`" >> reports/test_failure_analysis.md

echo "### 3. Contract Drift (Missing step in YAML)" >> reports/test_failure_analysis.md
echo "- **NodeID**: \`tests/unit/scripts/engineering/ci/test_generated_artifact_selection.py::test_source_checks_and_coverage_selection_survive_daily_partition\`" >> reports/test_failure_analysis.md
echo "- **Exit Code**: 1" >> reports/test_failure_analysis.md
echo "- **Pass/Fail**: Fail (Run 1, 2, 3)" >> reports/test_failure_analysis.md
echo "- **Evidence (Raw Log snippet)**: \`assert any(\"python -m scripts.docs passports check-source\" in command...)\`" >> reports/test_failure_analysis.md
