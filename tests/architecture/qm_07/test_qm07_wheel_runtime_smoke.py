import subprocess
import sys
from pathlib import Path
import pytest


@pytest.mark.architecture
def test_wheel_runtime_smoke(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]

    # We assume wheel was already built in dist, but if not build it
    wheel_files = list((repo_root / "dist").glob("*.whl"))
    if not wheel_files:
        subprocess.run(
            [sys.executable, "-m", "build", "--sdist", "--wheel"],
            cwd=repo_root,
            check=True,
        )
        wheel_files = list((repo_root / "dist").glob("*.whl"))

    wheel = wheel_files[0]

    # 2. Install to venv
    venv_dir = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

    venv_python = venv_dir / "bin" / "python3"
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", str(wheel)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"install failed: {result.stderr}"

    # 3. Import hook blocking `scripts`
    hook_code = """
import sys
class BlockScriptsHook:
    def find_spec(self, fullname, path, target=None):
        if fullname == "scripts" or fullname.startswith("scripts."):
            raise ImportError(f"Blocked import of {fullname}")
        return None

sys.meta_path.insert(0, BlockScriptsHook())
"""

    # 4. Smoke scenarios
    scenarios = [
        "import bioetl",
        "from bioetl.interfaces.cli.commands.domains.diagnostics.contract_checks import run_observability_contract_checks",
        "from bioetl.composition.observability_runtime import check_metric_inventory",
    ]
    for scenario in scenarios:
        code = hook_code + "\n" + scenario
        result = subprocess.run(
            [str(venv_python), "-I", "-c", code],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Scenario failed: {scenario}\n{result.stderr}\n{result.stdout}"
        )
