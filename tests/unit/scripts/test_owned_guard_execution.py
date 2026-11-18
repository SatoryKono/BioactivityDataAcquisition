"""Guard code reuse retains CLI checks inside the owned Linux watchdog."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.repo import hook_runtime as runtime


def _command(phase):
    name = {"tree": "check_no_partial_tree", "budgets": "budget_guard"}[phase]
    path = Path(runtime.__file__).with_name(name + ".py")
    return [runtime.sys.executable, "-I", "-B", str(path), "--base", "origin/main"]


@pytest.fixture
def owned_linux(monkeypatch):
    monkeypatch.setattr(runtime.sys, "platform", "linux")
    token = runtime._OWNED_GUARD_CONTEXT.set(True)
    yield
    runtime._OWNED_GUARD_CONTEXT.reset(token)


@pytest.mark.parametrize("phase", ["tree", "budgets"])
@pytest.mark.parametrize("code", [0, 1, 2])
def test_exact_guard_cli_arguments_and_status(owned_linux, monkeypatch, phase, code):
    command = _command(phase)
    calls = []
    module = SimpleNamespace(
        __file__=command[3],
        main=lambda args: calls.append(args) or code,
    )
    monkeypatch.setattr(runtime.importlib, "import_module", lambda name: module)
    expected = 0 if code == 0 else runtime.PHASE_CODES[phase] if code == 1 else 22
    assert runtime._try_builtin_guard(phase, command) == expected
    assert calls == [command[4:]]


@pytest.mark.parametrize("case", ["non-owned", "windows", "phase", "argv", "module"])
def test_unqualified_call_retains_subprocess_path(owned_linux, monkeypatch, case):
    phase, command = "tree", _command("tree")
    module = SimpleNamespace(
        __file__=command[3], main=lambda args: pytest.fail("executed")
    )
    if case == "non-owned":
        runtime._OWNED_GUARD_CONTEXT.set(False)
    elif case == "windows":
        monkeypatch.setattr(runtime.sys, "platform", "win32")
    elif case == "phase":
        phase = "foreign"
    elif case == "argv":
        command[2] = "-b"
    else:
        module.__file__ = str(Path(command[3]).with_name("foreign_guard.py"))
    monkeypatch.setattr(runtime.importlib, "import_module", lambda name: module)
    assert runtime._try_builtin_guard(phase, command) is None


@pytest.mark.parametrize("result", [None, True, "0", 3, -1])
def test_unknown_return_value_is_error(owned_linux, monkeypatch, result):
    command = _command("tree")
    module = SimpleNamespace(__file__=command[3], main=lambda args: result)
    monkeypatch.setattr(runtime.importlib, "import_module", lambda name: module)
    assert runtime._try_builtin_guard("tree", command) == 20


@pytest.mark.parametrize("error", [RuntimeError("guard"), SystemExit(0), SystemExit(2)])
def test_guard_exception_is_error_without_raw_output(
    owned_linux, monkeypatch, capsys, error
):
    command = _command("budgets")

    def main(args):
        print("private stdout")
        print("private stderr", file=runtime.sys.stderr)
        raise error

    module = SimpleNamespace(__file__=command[3], main=main)
    monkeypatch.setattr(runtime.importlib, "import_module", lambda name: module)
    assert runtime._try_builtin_guard("budgets", command) == 20
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def test_import_failure_is_error(owned_linux, monkeypatch):
    def unavailable(name):
        raise ImportError("unavailable")

    monkeypatch.setattr(runtime.importlib, "import_module", unavailable)
    assert runtime._try_builtin_guard("tree", _command("tree")) == 20


@pytest.mark.parametrize("failure", [False, True])
def test_owned_entry_scopes_and_resets_context(monkeypatch, tmp_path, failure):
    assert not runtime._OWNED_GUARD_CONTEXT.get()
    monkeypatch.setattr(
        runtime.sys,
        "argv",
        ["hook_runtime", "--owned-child", "pre-commit", str(tmp_path)],
    )

    def run(*args):
        assert runtime._OWNED_GUARD_CONTEXT.get()
        if failure:
            raise RuntimeError("worker failed")
        return 0

    monkeypatch.setattr(runtime, "run", run)
    if failure:
        with pytest.raises(RuntimeError, match="worker failed"):
            runtime.main()
    else:
        assert runtime.main() == 0
    assert not runtime._OWNED_GUARD_CONTEXT.get()
