# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guards for canonical composite naming surfaces."""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace

import pytest

from bioetl.application import composite as composite_package
from bioetl.application.composite import checkpoint as checkpoint_package
from bioetl.application.composite import preflight_validator as preflight_module
from bioetl.application.composite import runner_pkg, runtime_wiring_api
from bioetl.application.composite.runner_pkg import runner as runner_module

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
TEST_ROOT = ROOT / "tests"
DOC_ROOTS = (
    ROOT / "docs" / "02-architecture" / "diagrams",
    ROOT / "docs" / "reports" / "knowledge-graphs",
)
DEPRECATED_COMPOSITE_SYMBOLS = (
    "CompositeCheckpointManager",
    "CompositePipelineRunnerService",
    "CompositePreflightValidator",
)
_DEPRECATED_COMPOSITE_SYMBOL_BYTES = tuple(
    symbol.encode("utf-8") for symbol in DEPRECATED_COMPOSITE_SYMBOLS
)
_SCAN_CHUNK_SIZE = 64 * 1024
_SCAN_OVERLAP = max(len(symbol) for symbol in _DEPRECATED_COMPOSITE_SYMBOL_BYTES) - 1
_SYMBOL_SCAN_TIMEOUT_SECONDS = 20.0


_TEXT_SUFFIXES = frozenset({".py", ".mmd", ".mermaid", ".md", ".json", ".svg"})


@cache
def _python_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        for filename in filenames:
            if filename.endswith(".py"):
                files.append(base / filename)
    return tuple(sorted(files))


@cache
def _text_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        for filename in filenames:
            if Path(filename).suffix in _TEXT_SUFFIXES:
                files.append(base / filename)
    return tuple(sorted(files))


def _file_contains_symbol(path: Path, symbol: bytes) -> bool:
    with path.open("rb") as stream:
        tail = b""
        while chunk := stream.read(_SCAN_CHUNK_SIZE):
            haystack = tail + chunk
            if symbol in haystack:
                return True
            tail = haystack[-_SCAN_OVERLAP:] if _SCAN_OVERLAP > 0 else b""
    return False


def _symbol_hits(root: Path, allowlist: frozenset[Path]) -> list[str]:
    hits: list[str] = []
    for py_file in _python_files(root):
        if py_file in allowlist:
            continue
        for symbol, symbol_bytes in zip(
            DEPRECATED_COMPOSITE_SYMBOLS,
            _DEPRECATED_COMPOSITE_SYMBOL_BYTES,
            strict=True,
        ):
            if _file_contains_symbol(py_file, symbol_bytes):
                hits.append(f"{py_file.relative_to(ROOT)} -> {symbol}")
    return hits


@cache
def _doc_symbol_hits() -> list[str]:
    scanners = {
        "git": _repo_symbol_hits_with_git_grep,
        "rg": _repo_symbol_hits_with_ripgrep,
    }
    for scanner_name in _doc_symbol_scan_order():
        hits = scanners[scanner_name](DOC_ROOTS, skip_legacy=True)
        if hits is not None:
            return hits

    if os.name == "nt":
        pytest.skip(
            "Active composite doc symbol scan requires git grep or ripgrep on Windows; "
            "filesystem fallback is intentionally disabled to avoid PyCharm timeout hangs."
        )

    hits: list[str] = []
    for root in DOC_ROOTS:
        for doc_file in _text_files(root):
            if "legacy" in doc_file.parts:
                continue
            for symbol, symbol_bytes in zip(
                DEPRECATED_COMPOSITE_SYMBOLS,
                _DEPRECATED_COMPOSITE_SYMBOL_BYTES,
                strict=True,
            ):
                if _file_contains_symbol(doc_file, symbol_bytes):
                    hits.append(f"{doc_file.relative_to(ROOT)} -> {symbol}")
    return hits


def _doc_symbol_scan_order(*, os_name: str = os.name) -> tuple[str, str]:
    """Return bounded scanner preference for the current filesystem platform."""
    if os_name == "nt":
        return ("rg", "git")
    return ("git", "rg")


def _repo_symbol_hits_with_git_grep(
    roots: tuple[Path, ...],
    *,
    skip_legacy: bool,
) -> list[str] | None:
    git_executable = _git_executable()
    if git_executable is None:
        return None

    pathspecs: list[str] = []
    for root in roots:
        pathspec = _repo_relative_pathspec(root)
        if pathspec is None:
            return None
        pathspecs.append(pathspec)

    command = [
        git_executable,
        "-C",
        ROOT.as_posix(),
        "grep",
        "-I",
        "-n",
        "-F",
        "--no-color",
        *(
            option
            for symbol in DEPRECATED_COMPOSITE_SYMBOLS
            for option in ("-e", symbol)
        ),
        "--",
        *pathspecs,
    ]
    try:
        completed, stdout = _run_symbol_scan_command(command)
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode == 1:
        return []
    if completed.returncode != 0:
        return None

    hits: set[str] = set()
    for line in stdout.splitlines():
        path_text, separator, remainder = line.partition(":")
        if not separator:
            continue
        _line_number, separator, text = remainder.partition(":")
        if not separator:
            continue
        path = Path(path_text.replace("\\", "/"))
        if skip_legacy and "legacy" in path.parts:
            continue
        if path.suffix not in {".py", ".mmd", ".mermaid", ".md", ".json", ".svg"}:
            continue
        for symbol in DEPRECATED_COMPOSITE_SYMBOLS:
            if symbol in text:
                hits.add(f"{path.as_posix()} -> {symbol}")
    return sorted(hits)


def _repo_symbol_hits_with_ripgrep(
    roots: tuple[Path, ...],
    *,
    skip_legacy: bool,
) -> list[str] | None:
    rg_executable = _rg_executable()
    if rg_executable is None:
        return None

    pathspecs: list[str] = []
    for root in roots:
        pathspec = _repo_relative_pathspec(root)
        if pathspec is None:
            return None
        pathspecs.append(pathspec)

    command = [
        rg_executable,
        "-n",
        "-F",
        "--no-heading",
        *(
            option
            for symbol in DEPRECATED_COMPOSITE_SYMBOLS
            for option in ("-e", symbol)
        ),
        *pathspecs,
    ]
    try:
        completed, stdout = _run_symbol_scan_command(command)
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode == 1:
        return []
    if completed.returncode != 0:
        return None

    hits: set[str] = set()
    for line in stdout.splitlines():
        path_text, separator, remainder = line.partition(":")
        if not separator:
            continue
        _line_number, separator, text = remainder.partition(":")
        if not separator:
            continue
        path = Path(path_text.replace("\\", "/"))
        if skip_legacy and "legacy" in path.parts:
            continue
        if path.suffix not in _TEXT_SUFFIXES:
            continue
        for symbol in DEPRECATED_COMPOSITE_SYMBOLS:
            if symbol in text:
                hits.add(f"{path.as_posix()} -> {symbol}")
    return sorted(hits)


@cache
def _git_executable() -> str | None:
    return shutil.which("git")


@cache
def _rg_executable() -> str | None:
    return shutil.which("rg")


def _run_symbol_scan_command(
    command: list[str],
) -> tuple[subprocess.CompletedProcess[str], str]:
    output_path = _temporary_symbol_scan_output_path()
    try:
        with output_path.open("w", encoding="utf-8", errors="replace") as stdout_file:
            completed = subprocess.run(
                command,
                stdout=stdout_file,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                cwd=ROOT,
                timeout=_SYMBOL_SCAN_TIMEOUT_SECONDS,
                **_hidden_windows_subprocess_kwargs(),
            )
        stdout = output_path.read_text(encoding="utf-8", errors="replace")
    finally:
        output_path.unlink(missing_ok=True)
    return completed, stdout


def _temporary_symbol_scan_output_path() -> Path:
    handle = tempfile.NamedTemporaryFile(
        prefix="composite_canonical_surface_scan_",
        suffix=".txt",
        delete=False,
    )
    handle.close()
    return Path(handle.name)


def _hidden_windows_subprocess_kwargs(
    *,
    os_name: str = os.name,
    subprocess_module: object = subprocess,
) -> dict[str, object]:
    if os_name != "nt":
        return {}

    kwargs: dict[str, object] = {}
    create_no_window = int(getattr(subprocess_module, "CREATE_NO_WINDOW", 0))
    if create_no_window:
        kwargs["creationflags"] = create_no_window

    startupinfo_factory = getattr(subprocess_module, "STARTUPINFO", None)
    if callable(startupinfo_factory):
        startupinfo = startupinfo_factory()
        startf_use_show_window = int(
            getattr(subprocess_module, "STARTF_USESHOWWINDOW", 0)
        )
        if startf_use_show_window:
            startupinfo.dwFlags = (
                int(getattr(startupinfo, "dwFlags", 0)) | startf_use_show_window
            )
        if hasattr(subprocess_module, "SW_HIDE"):
            startupinfo.wShowWindow = int(getattr(subprocess_module, "SW_HIDE", 0))
        kwargs["startupinfo"] = startupinfo
    return kwargs


def _repo_relative_pathspec(path: Path) -> str | None:
    try:
        common_path = os.path.commonpath(
            [
                os.path.abspath(os.fspath(ROOT)),
                os.path.abspath(os.fspath(path)),
            ]
        )
    except ValueError:
        return None
    repo_root = os.path.abspath(os.fspath(ROOT))
    if os.path.normcase(common_path) != os.path.normcase(repo_root):
        return None
    relative = os.path.relpath(os.path.abspath(os.fspath(path)), repo_root)
    return "." if relative == "." else relative.replace(os.sep, "/")


@pytest.mark.architecture
def test_deprecated_composite_symbols_are_confined_to_owner_modules() -> None:
    hits = _symbol_hits(SRC_ROOT / "bioetl" / "application" / "composite", frozenset())
    assert hits == [], (
        "Deprecated composite symbols must stay removed from application "
        "composite source:\n" + "\n".join(f"  - {hit}" for hit in hits)
    )


@pytest.mark.architecture
def test_first_party_composite_tests_use_canonical_names_by_default() -> None:
    roots = (
        TEST_ROOT / "unit" / "application" / "composite",
        TEST_ROOT / "unit" / "composition" / "bootstrap" / "runtime",
        TEST_ROOT / "integration" / "composite",
    )
    hits: list[str] = []
    for root in roots:
        hits.extend(_symbol_hits(root, frozenset()))
    assert hits == [], (
        "First-party composite tests must use canonical composite names by "
        "default:\n" + "\n".join(f"  - {hit}" for hit in hits)
    )


@pytest.mark.architecture
def test_active_composite_docs_and_generated_graphs_use_canonical_names() -> None:
    hits = _doc_symbol_hits()
    assert hits == [], (
        "Active composite docs and generated knowledge graphs must use canonical "
        "composite names:\n" + "\n".join(f"  - {hit}" for hit in hits)
    )


@pytest.mark.architecture
def test_symbol_scan_subprocess_kwargs_hide_windows_console() -> None:
    startupinfo = SimpleNamespace(dwFlags=0, wShowWindow=5)
    fake_subprocess = SimpleNamespace(
        CREATE_NO_WINDOW=0x08000000,
        STARTF_USESHOWWINDOW=0x00000001,
        SW_HIDE=0,
        STARTUPINFO=lambda: startupinfo,
    )

    kwargs = _hidden_windows_subprocess_kwargs(
        os_name="nt",
        subprocess_module=fake_subprocess,
    )

    assert kwargs["creationflags"] == 0x08000000
    assert kwargs["startupinfo"] is startupinfo
    assert startupinfo.dwFlags == 0x00000001
    assert startupinfo.wShowWindow == 0


@pytest.mark.architecture
def test_doc_symbol_scan_prefers_ripgrep_on_windows() -> None:
    assert _doc_symbol_scan_order(os_name="nt") == ("rg", "git")
    assert _doc_symbol_scan_order(os_name="posix") == ("git", "rg")


@pytest.mark.architecture
def test_symbol_scan_timeout_fits_inside_default_pytest_budget() -> None:
    assert 0 < _SYMBOL_SCAN_TIMEOUT_SECONDS < 60


@pytest.mark.architecture
def test_composite_facades_export_only_canonical_composite_symbols() -> None:
    composite_exports = set(composite_package.__all__)
    runtime_exports = set(runtime_wiring_api.__all__)
    checkpoint_exports = set(checkpoint_package.__all__)
    runner_exports = set(runner_pkg.__all__)
    owner_runner_exports = set(runner_module.__all__)
    owner_preflight_exports = set(preflight_module.__all__)

    assert "CompositeCheckpointService" in composite_exports
    assert "CompositePipelineRunner" in composite_exports
    assert "CompositePreflightValidationService" in composite_exports

    assert "CompositePipelineRunner" in runtime_exports
    assert "CompositePreflightValidationService" in runtime_exports
    assert "CompositeCheckpointService" in checkpoint_exports
    assert "CompositePipelineRunner" in runner_exports
    assert "CompositePipelineRunner" in owner_runner_exports
    assert "CompositePreflightValidationService" in owner_preflight_exports

    for deprecated_name in DEPRECATED_COMPOSITE_SYMBOLS:
        assert deprecated_name not in composite_exports
        assert deprecated_name not in runtime_exports
        assert deprecated_name not in checkpoint_exports
        assert deprecated_name not in runner_exports
        assert deprecated_name not in owner_runner_exports
        assert deprecated_name not in owner_preflight_exports


@pytest.mark.architecture
def test_application_composite_does_not_keep_port_types_shadow_seam() -> None:
    seam_path = SRC_ROOT / "bioetl" / "application" / "composite" / "port_types.py"
    assert not seam_path.exists(), (
        "application composite must not keep a local *Port alias seam; import "
        "domain ports directly instead."
    )

    hits = [
        str(path.relative_to(ROOT))
        for path in _python_files(SRC_ROOT / "bioetl" / "application" / "composite")
        if "from bioetl.application.composite.port_types import"
        in path.read_text(encoding="utf-8")
    ]
    assert hits == [], (
        "application composite code must not import a local port_types seam:\n"
        + "\n".join(f"  - {hit}" for hit in hits)
    )
