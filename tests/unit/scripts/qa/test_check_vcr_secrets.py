"""CF-007 regressions for tracked VCR HTTP metadata."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.engineering.qa.vcr import check_vcr_secrets as checker
from tests.helpers.isolated_git import isolated_git_env, run_isolated_git

pytestmark = pytest.mark.unit


def _cassette(
    *,
    request_headers: str = "{}",
    response_headers: str = "{}",
    uri: str = "https://example.test/items?term=protein",
) -> str:
    return (
        "interactions:\n"
        "- request:\n"
        "    method: GET\n"
        f"    uri: {uri}\n"
        f"    headers: {request_headers}\n"
        "  response:\n"
        "    status: {code: 200}\n"
        f"    headers: {response_headers}\n"
        '    body: {string: "{\\"organism\\": \\"human\\"}"}\n'
        "version: 1\n"
    )


@pytest.mark.parametrize(
    ("request_headers", "response_headers", "field"),
    [
        ("{CoOkIe: synthetic-session}", "{}", "cookie"),
        ("{cookie: [REDACTED, synthetic-session]}", "{}", "cookie"),
        ("{}", "{SET-COOKIE: [REDACTED, synthetic-session]}", "set-cookie"),
        ("{}", "{set-cookie2: [synthetic-session]}", "set-cookie2"),
        ("{NCBI-SID: [synthetic-session]}", "{}", "ncbi-sid"),
        ("{}", "{NcBi-PhId: [synthetic-session]}", "ncbi-phid"),
        ("{Authorization: [REDACTED, synthetic-session]}", "{}", "authorization"),
        ("{X-API-Key: [synthetic-session]}", "{}", "x-api-key"),
        ("{cookie: [my-test-token]}", "{}", "cookie"),
        ("{cookie: [unredacted_secret]}", "{}", "cookie"),
    ],
)
def test_each_sensitive_header_value_is_checked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request_headers: str,
    response_headers: str,
    field: str,
) -> None:
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    path = tmp_path / "cassette.yaml"
    path.write_text(
        _cassette(request_headers=request_headers, response_headers=response_headers),
        encoding="utf-8",
    )

    findings = checker._scan_file(path)

    assert any(
        field in finding.casefold() and "interaction 1" in finding
        for finding in findings
    )
    assert all("synthetic-session" not in finding for finding in findings)


def test_query_credentials_are_checked_individually_in_flow_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    path = tmp_path / "cassette.yaml"
    path.write_text(
        _cassette(
            request_headers="{cookie: [REDACTED]}",
            uri="https://example.test/items?API_KEY=REDACTED&ncbi_sid=synthetic-session&term=protein",
        ),
        encoding="utf-8",
    )

    findings = checker._scan_file(path)

    assert any(
        "ncbi_sid" in finding and "interaction 1" in finding for finding in findings
    )
    assert all("synthetic-session" not in finding for finding in findings)


@pytest.mark.parametrize(
    "content",
    [
        "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123\n",
        "interactions: [\n",
        "interactions: []\n",
        "interactions: &loop [*loop]\n",
        _cassette() + "interactions: []\n",
        "interactions:\n- request: {headers: {cookie: [REDACTED]}}\n  response: {headers: {}}\n",
    ],
)
def test_invalid_or_ambiguous_cassette_cannot_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content: str,
) -> None:
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    path = tmp_path / "cassette.yaml"
    path.write_text(content, encoding="utf-8")

    assert checker._scan_file(path)


@pytest.mark.parametrize("create_root", [False, True])
def test_missing_or_empty_root_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    create_root: bool,
) -> None:
    vcr_root = tmp_path / "tests/fixtures/vcr"
    if create_root:
        vcr_root.mkdir(parents=True)
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "VCR_ROOT", vcr_root)

    assert checker.main() != 0


@pytest.mark.parametrize(
    "style", ["block", "quoted", "flow", "merge", "upper_extension"]
)
def test_tracked_cassette_outside_canonical_directory_is_scanned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    style: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    vcr_root = tmp_path / "tests/fixtures/vcr"
    vcr_root.mkdir(parents=True)
    (vcr_root / "clean.yaml").write_text(_cassette(), encoding="utf-8")
    outside = tmp_path / "tests/fixtures/http/captured.yaml"
    if style == "upper_extension":
        outside = outside.with_suffix(".YaMl")
    outside.parent.mkdir(parents=True)
    content = _cassette(response_headers="{set-cookie: [synthetic-session]}")
    if style == "quoted":
        content = content.replace("interactions:", '"interactions":', 1)
    elif style == "flow":
        content = yaml.safe_dump(yaml.safe_load(content), default_flow_style=True)
    elif style == "merge":
        content = (
            "defaults: &cassette\n"
            + "".join("  " + line + "\n" for line in content.splitlines())
            + "<<: *cassette\n"
        )
    outside.write_text(content, encoding="utf-8")
    subprocess.run(
        ["git", "init", "-q"],
        cwd=tmp_path,
        env=isolated_git_env(),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "add",
            "tests/fixtures/vcr/clean.yaml",
            outside.relative_to(tmp_path).as_posix(),
        ],
        cwd=tmp_path,
        env=isolated_git_env(),
        check=True,
        capture_output=True,
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "VCR_ROOT", vcr_root)

    assert checker.main() != 0
    assert "response.headers.set-cookie" in capsys.readouterr().err


def test_missing_tracked_cassette_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vcr_root = tmp_path / "tests/fixtures/vcr"
    vcr_root.mkdir(parents=True)
    path = vcr_root / "missing.yaml"
    path.write_text(_cassette(), encoding="utf-8")
    subprocess.run(
        ["git", "init", "-q"],
        cwd=tmp_path,
        env=isolated_git_env(),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "tests/fixtures/vcr/missing.yaml"],
        cwd=tmp_path,
        env=isolated_git_env(),
        check=True,
        capture_output=True,
    )
    path.unlink()
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "VCR_ROOT", vcr_root)

    assert checker.main() != 0


def test_safe_aliases_remain_supported_and_each_expanded_value_is_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    path = tmp_path / "cassette.yaml"
    path.write_text(
        _cassette(
            response_headers="{Set-Cookie: &session [REDACTED, synthetic-session], Cookie: *session}"
        ),
        encoding="utf-8",
    )

    findings = checker._scan_file(path)

    assert len(findings) == 2
    assert any("response.headers.set-cookie" in finding for finding in findings)
    assert any("response.headers.cookie" in finding for finding in findings)


def test_empty_canonical_root_fails_with_other_tracked_yaml_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    vcr_root = tmp_path / "tests/fixtures/vcr"
    vcr_root.mkdir(parents=True)
    other = tmp_path / "config.yaml"
    other.write_text("name: unrelated\n", encoding="utf-8")
    subprocess.run(
        ["git", "init", "-q"],
        cwd=tmp_path,
        env=isolated_git_env(),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "config.yaml"],
        cwd=tmp_path,
        env=isolated_git_env(),
        check=True,
        capture_output=True,
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "VCR_ROOT", vcr_root)

    assert checker.main() == 1
    assert "empty cassette traversal" in capsys.readouterr().err


@pytest.mark.parametrize("content", ["[unterminated", "invalid: \xff"])
def test_malformed_off_catalog_yaml_is_not_silently_excluded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    content: str,
) -> None:
    vcr_root = tmp_path / "tests/fixtures/vcr"
    vcr_root.mkdir(parents=True)
    clean = vcr_root / "clean.yaml"
    clean.write_text(_cassette(), encoding="utf-8")
    ambiguous = tmp_path / "unknown.yaml"
    ambiguous.write_bytes(content.encode("latin-1"))
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "VCR_ROOT", vcr_root)
    monkeypatch.setattr(checker, "_tracked_yaml_paths", lambda: [clean, ambiguous])

    assert checker.main() == 1
    diagnostic = capsys.readouterr().err
    assert "unknown.yaml" in diagnostic
    assert "unavailable=1" in diagnostic


def test_inventory_cannot_be_redirected_to_another_git_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    foreign = tmp_path / "foreign"
    for root, name in ((target, "target.yaml"), (foreign, "foreign.yaml")):
        root.mkdir()
        (root / name).write_text("name: safe\n", encoding="utf-8")
        run_isolated_git(root, "init", "-q")
        run_isolated_git(root, "add", name)
    monkeypatch.setattr(checker, "ROOT", target)
    monkeypatch.setenv("GIT_DIR", str(foreign / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(foreign))
    monkeypatch.setenv("GIT_INDEX_FILE", str(foreign / ".git/index"))

    assert checker._tracked_yaml_paths() == [target / "target.yaml"]
