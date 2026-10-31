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
"""Architecture tests for the non-skippable import-linter CI gate.REQ-GOV-008: Import Linter is a change-set gate."""

from __future__ import annotations

from pathlib import Path
import json
import shlex
import subprocess

import pytest
import yaml


pytestmark = pytest.mark.architecture


def test_import_linter_workflow_is_reusable_without_push() -> None:
    """Import-linter stays callable and no longer starts on push."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert "workflow_call:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "workflow_dispatch:" in workflow
    assert "paths-ignore:" not in workflow


def test_import_linter_workflow_keeps_checks_complete_as_blocking_gate() -> None:
    """The aggregate gate must remain blocking across lint and architecture jobs."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert "checks-complete:" in workflow
    assert "needs:" in workflow
    assert "- lint" in workflow
    assert "- c901-governance" in workflow
    assert "- arch-tests" in workflow
    assert "if: ${{ always() }}" in workflow


def test_import_linter_workflow_requires_capabilities_for_sharded_arch_tests() -> None:
    """Required CI must fail fast on capability drift during architecture tests."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert "arch-tests:" in workflow
    assert 'BIOETL_REQUIRE_TEST_CAPABILITIES: "1"' in workflow
    assert "scripts/engineering/dev/run_pytest_sharded.sh" in workflow
    assert "strategy:" in workflow
    assert "matrix:" in workflow
    assert "bash scripts/engineering/dev/run_pytest_sharded.sh" in workflow
    assert '--shard "${{ matrix.shard }}"' in workflow
    assert "--skip-preflight" in workflow
    assert '-m "not slow and not benchmark and not memory"' in workflow


def test_import_linter_changed_file_gate_stays_below_arg_max() -> None:
    """Large changed-file sets must stay on disk and be processed in batches."""
    workflow = Path(".github/workflows/import-linter.yml").read_text(encoding="utf-8")

    assert 'list_file="${RUNNER_TEMP}/ruff-changed-python.txt"' in workflow
    assert 'echo "list_file=${list_file}" >> "$GITHUB_OUTPUT"' in workflow
    assert 'echo "file_count=${file_count}" >> "$GITHUB_OUTPUT"' in workflow
    assert 'if [[ "$file_count" -gt 400 ]]' in workflow
    assert "xargs -a \"$list_file\" -d '\\n' -n 100" in workflow
    assert 'echo "files=' not in workflow


@pytest.mark.parametrize("job_name", ["arch-tests", "arch-tests-slow"])
def test_architecture_prepares_archived_source_objects_after_squash(
    tmp_path: Path, job_name: str
) -> None:
    """Execute the real checkout preparation after deleting the source branch."""
    workflow = yaml.safe_load(Path(".github/workflows/import-linter.yml").read_text())
    step = next(
        step
        for step in workflow["jobs"][job_name]["steps"]
        if step.get("name") == "Unshallow current-ref history for ancestor gates"
    )
    fetches = [
        shlex.split(line.strip())
        for line in step["run"].splitlines()
        if line.strip().startswith("git fetch ")
    ]
    assert len(fetches) == 2
    assert not any(
        "--force" in command or any(arg.startswith("+") for arg in command)
        for command in fetches
    )

    def git(*args: str, cwd: Path, check: bool = True, data: str | None = None):
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            input=data,
            capture_output=True,
            text=True,
            check=check,
            timeout=30,
        )

    producer, remote, receiver = (
        tmp_path / name for name in ("producer", "remote.git", "receiver")
    )
    git("init", "--initial-branch=main", str(producer), cwd=tmp_path)
    git("init", "--bare", "--initial-branch=main", str(remote), cwd=tmp_path)
    git("config", "user.name", "Synthetic evidence fixture", cwd=producer)
    git("config", "user.email", "fixture@example.invalid", cwd=producer)
    git("config", "commit.gpgsign", "false", cwd=producer)
    git("commit", "--allow-empty", "-m", "fixture base", cwd=producer)
    base = git("rev-parse", "HEAD", cwd=producer).stdout.strip()
    git("checkout", "-b", "source-branch", cwd=producer)
    source_path = "src/bioetl/example.py"
    source_bytes = b"def value():\n    return 17\n"
    (producer / source_path).parent.mkdir(parents=True)
    (producer / source_path).write_bytes(source_bytes)
    git("add", source_path, cwd=producer)
    git("commit", "-m", "fixture source", cwd=producer)
    source = git("rev-parse", "HEAD", cwd=producer).stdout.strip()
    source_tree = git("rev-parse", "HEAD^{tree}", cwd=producer).stdout.strip()
    catalog_path = "configs/quality/external_resource_inventory.json"
    (producer / catalog_path).parent.mkdir(parents=True)
    catalog = {"source_commit": source, "source_tree": source_tree}
    (producer / catalog_path).write_text(json.dumps(catalog))
    git("add", catalog_path, cwd=producer)
    git("commit", "-m", "fixture catalog", cwd=producer)
    published = git("rev-parse", "HEAD", cwd=producer).stdout.strip()
    tree = git("rev-parse", "HEAD^{tree}", cwd=producer).stdout.strip()
    squash = git(
        "commit-tree", tree, "-p", base, cwd=producer, data="fixture squash\n"
    ).stdout.strip()
    git("update-ref", "refs/heads/main", squash, cwd=producer)
    tag = f"evidence/issue-12474-fixture-{published}"
    git("tag", tag, published, cwd=producer)
    git("remote", "add", "origin", str(remote), cwd=producer)
    git("push", "origin", "main", "source-branch", f"refs/tags/{tag}", cwd=producer)
    git("push", "origin", "--delete", "source-branch", cwd=producer)
    assert not git(
        "ls-remote", "origin", "refs/heads/source-branch", cwd=producer
    ).stdout.strip()
    git(
        "clone",
        "--depth=1",
        "--single-branch",
        "--branch=main",
        "--no-tags",
        remote.as_uri(),
        str(receiver),
        cwd=tmp_path,
    )
    assert not (receiver / ".git/objects/info/alternates").exists()
    assert (
        source
        not in git(
            "cat-file",
            "--batch-all-objects",
            "--batch-check=%(objectname)",
            cwd=receiver,
        ).stdout.splitlines()
    )
    git(*fetches[0][1:], cwd=receiver)
    assert (
        source
        not in git(
            "cat-file",
            "--batch-all-objects",
            "--batch-check=%(objectname)",
            cwd=receiver,
        ).stdout.splitlines()
    )
    git(*fetches[1][1:], cwd=receiver)
    assert (
        source
        in git(
            "cat-file",
            "--batch-all-objects",
            "--batch-check=%(objectname)",
            cwd=receiver,
        ).stdout.splitlines()
    )
    assert (
        git("rev-parse", f"refs/tags/{tag}", cwd=receiver).stdout.strip() == published
    )
    assert (
        json.loads(git("show", f"{published}:{catalog_path}", cwd=receiver).stdout)
        == catalog
    )
    assert (
        git("rev-parse", f"{source}^{{tree}}", cwd=receiver).stdout.strip()
        == source_tree
    )
    assert (
        git("show", f"{source}:{source_path}", cwd=receiver).stdout.encode()
        == source_bytes
    )
    git("merge-base", "--is-ancestor", source, published, cwd=receiver)
    assert (
        git(
            "merge-base", "--is-ancestor", source, "HEAD", cwd=receiver, check=False
        ).returncode
        == 1
    )
    assert git("rev-parse", "HEAD^{tree}", cwd=receiver).stdout.strip() == tree
    # A changed archival ref must not replace the previously pinned object.
    git("--git-dir", str(remote), "update-ref", f"refs/tags/{tag}", base, cwd=tmp_path)
    assert git(*fetches[1][1:], cwd=receiver, check=False).returncode != 0
    assert (
        git("rev-parse", f"refs/tags/{tag}", cwd=receiver).stdout.strip() == published
    )
