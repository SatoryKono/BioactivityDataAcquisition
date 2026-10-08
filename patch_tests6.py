import os

test_file = "tests/unit/repo_backed/scripts/engineering/ci/test_pr_lane_results.py"
with open(test_file, 'r') as f:
    content = f.read()

if "pytestmark = pytest.mark.repo_backed" not in content:
    content = content.replace("import pytest", "import pytest\n\npytestmark = pytest.mark.repo_backed")
    with open(test_file, 'w') as f:
        f.write(content)

test_file_2 = "tests/unit/interfaces/cli/commands/test_run_manifest_commands.py"
with open(test_file_2, 'r') as f:
    content = f.read()

if "pytestmark = pytest.mark.cli_unit" not in content:
    content = content.replace("import pytest", "import pytest\n\npytestmark = pytest.mark.cli_unit")
    with open(test_file_2, 'w') as f:
        f.write(content)
