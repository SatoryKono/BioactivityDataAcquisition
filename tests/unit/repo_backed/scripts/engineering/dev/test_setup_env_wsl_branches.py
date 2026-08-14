"""Execute WSL installer branches with stubbed uv/pip (issue #8766)."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("pyproject.toml not found")


ROOT = _repo_root()
SCRIPT = ROOT / "scripts/engineering/dev/setup_env_wsl.sh"


def _write_exec(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _run_installer(
    tmp_path: Path,
    *,
    agent_tools: str,
    with_uv: bool,
    fail_extra: str | None = None,
) -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    capture = tmp_path / "commands.log"
    venv_dir = tmp_path / "venv"
    capture.write_text("", encoding="utf-8")

    _write_exec(
        fake_bin / "true",
        "#!/bin/sh\nexit 0\n",
    )
    python_stub = r"""#!/bin/sh
echo "python3 $*" >> "$BIOETL_TEST_CAPTURE"
if echo "$*" | grep -q -- '-m venv'; then
  target=""
  for arg in "$@"; do
    target=$arg
  done
  mkdir -p "$target/bin"
  cat > "$target/bin/python" <<'INNER'
#!/bin/sh
echo "venv_python $*" >> "$BIOETL_TEST_CAPTURE"
exit 0
INNER
  chmod +x "$target/bin/python"
fi
exit 0
"""
    _write_exec(fake_bin / "python3", python_stub)
    _write_exec(fake_bin / "python", python_stub)

    if with_uv:
        fail_check = ""
        if fail_extra:
            fail_check = f"""
if echo "$*" | grep -q -- '--extra {fail_extra}'; then
  echo "uv $*" >> "$BIOETL_TEST_CAPTURE"
  exit 1
fi
"""
        _write_exec(
            fake_bin / "uv",
            f"""#!/bin/sh
{fail_check}
echo "uv $*" >> "$BIOETL_TEST_CAPTURE"
if [ "$1" = "venv" ]; then
  mkdir -p "$2/bin"
  cat > "$2/bin/python" <<'INNER'
#!/bin/sh
echo "venv_python $*" >> "$BIOETL_TEST_CAPTURE"
exit 0
INNER
  chmod +x "$2/bin/python"
fi
exit 0
""",
        )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}/usr/bin{os.pathsep}/bin"
    env["BIOETL_TEST_CAPTURE"] = str(capture)
    env["BIOETL_WSL_VENV_DIR"] = str(venv_dir)
    env["HOME"] = str(tmp_path / "home")
    (tmp_path / "home").mkdir()
    return subprocess.run(
        ["bash", str(SCRIPT), "--agent-tools", agent_tools],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def _logged_commands(tmp_path: Path) -> list[str]:
    log = (tmp_path / "commands.log").read_text(encoding="utf-8")
    return [line for line in log.splitlines() if line.strip()]


def test_setup_env_wsl_syntax() -> None:
    completed = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_uv_nominal_sync_keeps_tests_extra(tmp_path: Path) -> None:
    completed = _run_installer(tmp_path, agent_tools="none", with_uv=True)
    assert completed.returncode == 0, completed.stderr
    commands = _logged_commands(tmp_path)
    syncs = [line for line in commands if line.startswith("uv sync")]
    assert len(syncs) == 1
    assert "--frozen" in syncs[0]
    assert "--no-build" in syncs[0]
    assert "--extra tests" in syncs[0]
    assert "--extra dev" in syncs[0]
    assert "--extra tracing" in syncs[0]


def test_uv_agent_tools_all_keeps_tests_and_isolates_failure(tmp_path: Path) -> None:
    completed = _run_installer(
        tmp_path, agent_tools="all", with_uv=True, fail_extra="agentdebugx"
    )
    assert completed.returncode == 1, completed.stdout + completed.stderr
    commands = _logged_commands(tmp_path)
    syncs = [line for line in commands if line.startswith("uv sync")]
    assert len(syncs) == 3
    assert all("--extra tests" in line for line in syncs)
    assert any("--extra agentdebugx" in line for line in syncs)
    assert any("--extra proofagent" in line for line in syncs)
    assert "without blocking the remaining tools: agentdebugx" in completed.stderr


def test_pip_nominal_install_keeps_tests_extra(tmp_path: Path) -> None:
    completed = _run_installer(tmp_path, agent_tools="none", with_uv=False)
    assert completed.returncode == 0, completed.stderr
    commands = _logged_commands(tmp_path)
    installs = [line for line in commands if " -m pip install " in line]
    project = [line for line in installs if ".[dev,tests,tracing]" in line]
    assert project, commands
    assert all("--only-binary=:all:" in line for line in project)


def test_pip_agent_tools_all_retains_tests_extra(tmp_path: Path) -> None:
    completed = _run_installer(tmp_path, agent_tools="all", with_uv=False)
    assert completed.returncode == 0, completed.stderr
    commands = _logged_commands(tmp_path)
    extra_installs = [
        line
        for line in commands
        if " -m pip install " in line
        and ("agentdebugx" in line or "proofagent" in line)
    ]
    assert len(extra_installs) == 2, commands
    assert all("dev,tests,tracing" in line for line in extra_installs)
