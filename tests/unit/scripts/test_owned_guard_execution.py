"""Guard code reuse retains CLI checks inside the owned Linux watchdog."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.repo import hook_runtime as runtime


pytestmark = pytest.mark.unit


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


@pytest.mark.parametrize("parallel", [False, True])
def test_user_interrupt_propagates_from_owned_guard(owned_linux, monkeypatch, parallel):
    commands = [(phase, _command(phase)) for phase in ("tree", "budgets")]
    finished = []

    def interrupt(args):
        raise KeyboardInterrupt

    def budgets(args):
        finished.append("budgets")
        return 0

    modules = {
        "check_no_partial_tree": SimpleNamespace(
            __file__=commands[0][1][3], main=interrupt
        ),
        "budget_guard": SimpleNamespace(__file__=commands[1][1][3], main=budgets),
    }
    monkeypatch.setattr(
        runtime.importlib, "import_module", lambda name: modules[name.rsplit(".", 1)[1]]
    )
    with pytest.raises(KeyboardInterrupt):
        if parallel:
            runtime._try_parallel_guards(commands)
        else:
            runtime._try_builtin_guard(*commands[0])
    assert finished == (["budgets"] if parallel else [])


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


@pytest.mark.parametrize(
    "tree_code,budget_code,expected",
    [(0, 0, 0), (1, 2, 11), (0, 1, 12), (0, 2, 22), (True, 0, 20)],
)
def test_parallel_guard_group_awaits_both_and_preserves_order(
    owned_linux, monkeypatch, capsys, tree_code, budget_code, expected
):
    from threading import Barrier

    barrier = Barrier(2)
    finished = []
    modules = {}
    commands = [(phase, _command(phase)) for phase in ("tree", "budgets")]
    for (phase, command), code in zip(commands, (tree_code, budget_code), strict=True):

        def main(args, phase=phase, code=code, command=command):
            assert args == command[4:]
            barrier.wait(timeout=5)
            print("private guard output")
            finished.append(phase)
            return code

        modules[Path(command[3]).stem] = SimpleNamespace(__file__=command[3], main=main)
    monkeypatch.setattr(
        runtime.importlib, "import_module", lambda name: modules[name.rsplit(".", 1)[1]]
    )
    assert runtime._try_parallel_guards(commands) == expected
    assert set(finished) == {"tree", "budgets"}
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def test_parallel_group_rejects_unknown_partner_without_executing(
    owned_linux, monkeypatch
):
    commands = [(phase, _command(phase)) for phase in ("tree", "budgets")]
    commands[1][1][2] = "-b"
    module = SimpleNamespace(
        __file__=commands[0][1][3], main=lambda args: pytest.fail("executed")
    )
    monkeypatch.setattr(runtime.importlib, "import_module", lambda name: module)
    assert runtime._try_parallel_guards(commands) is None


def test_parallel_group_exception_still_awaits_other_check(owned_linux, monkeypatch):
    from threading import Barrier

    barrier = Barrier(2)
    finished = []
    commands = [(phase, _command(phase)) for phase in ("tree", "budgets")]

    def tree(args):
        barrier.wait(timeout=5)
        raise SystemExit(0)

    def budgets(args):
        barrier.wait(timeout=5)
        finished.append("budgets")
        return 0

    modules = {
        "check_no_partial_tree": SimpleNamespace(__file__=commands[0][1][3], main=tree),
        "budget_guard": SimpleNamespace(__file__=commands[1][1][3], main=budgets),
    }
    monkeypatch.setattr(
        runtime.importlib, "import_module", lambda name: modules[name.rsplit(".", 1)[1]]
    )
    assert runtime._try_parallel_guards(commands) == 20
    assert finished == ["budgets"]


@pytest.mark.parametrize(
    "failed_phase,tree_code,expected",
    [("budgets", 1, 11), ("budgets", 0, 20), ("tree", 0, 20)],
)
def test_parallel_import_error_preserves_phase_order_and_runs_partner(
    owned_linux, monkeypatch, failed_phase, tree_code, expected
):
    commands = [(phase, _command(phase)) for phase in ("tree", "budgets")]
    finished = []
    modules = {}
    for phase, command in commands:

        def main(args, phase=phase):
            finished.append(phase)
            return tree_code if phase == "tree" else 0

        modules[Path(command[3]).stem] = SimpleNamespace(__file__=command[3], main=main)

    failed_name = Path(_command(failed_phase)[3]).stem

    def load(name):
        if name.rsplit(".", 1)[1] == failed_name:
            raise ImportError("private loader diagnostics")
        return modules[name.rsplit(".", 1)[1]]

    monkeypatch.setattr(runtime.importlib, "import_module", load)
    assert runtime._try_parallel_guards(commands) == expected
    assert finished == (["tree"] if failed_phase == "budgets" else ["budgets"])
