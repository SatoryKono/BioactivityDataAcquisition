import json
import os
import subprocess

import pytest


@pytest.mark.unit
def test_receipt_plugin_positive(tmp_path):
    receipt_dir = tmp_path / "receipts"
    run_id = "run123"
    attempt = "1"

    # Create a dummy test file
    test_file = tmp_path / "test_dummy.py"
    test_file.write_text("def test_pass(): pass\ndef test_fail(): assert False\n")

    # Run pytest with the plugin
    env = os.environ.copy()
    env["CI"] = "true"
    env["PYTEST_XDIST_WORKER"] = "gw0"

    cmd = [
        "python",
        "-m",
        "pytest",
        str(test_file),
        "-p",
        "scripts.engineering.ci.pytest_receipts",
        f"--receipt-dir={receipt_dir}",
        f"--receipt-run-id={run_id}",
        f"--receipt-attempt={attempt}",
    ]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    assert result.returncode == 1  # test_fail fails

    # Check receipt file
    target_dir = receipt_dir / run_id / attempt / "gw0"
    receipt_files = list(target_dir.glob("receipt_*.json"))
    assert len(receipt_files) == 1

    with receipt_files[0].open() as f:
        data = json.load(f)

    assert data["run_id"] == run_id
    assert data["attempt"] == attempt
    assert data["worker"] == "gw0"
    assert data["exit_code"] == 1
    assert data["collection"]["selected"] == 2
    assert "CI" in data["environment"]

    # Check node outcomes (using the relative path from where pytest ran is tricky, so just check keys)
    # The node ids will start with the file path.
    results = data["results"]
    assert any("test_pass" in k and v == ["passed"] for k, v in results.items())
    assert any("test_fail" in k and v == ["failed"] for k, v in results.items())


@pytest.mark.unit
def test_receipt_plugin_sha_mismatch(tmp_path):
    test_file = tmp_path / "test_dummy.py"
    test_file.write_text("def test_pass(): pass\n")

    cmd = [
        "python",
        "-m",
        "pytest",
        str(test_file),
        "-p",
        "scripts.engineering.ci.pytest_receipts",
        f"--receipt-dir={tmp_path}",
        "--receipt-expected-sha=fake_sha123",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    assert result.returncode != 0
    assert "Checkout SHA mismatch! Expected fake_sha123" in result.stderr


@pytest.mark.unit
def test_receipt_plugin_no_secrets_leak(tmp_path):
    test_file = tmp_path / "test_dummy.py"
    test_file.write_text("def test_pass(): pass\n")

    env = os.environ.copy()
    env["SECRET_TOKEN"] = "leaked!"
    env["GITHUB_RUN_ID"] = "456"

    cmd = [
        "python",
        "-m",
        "pytest",
        str(test_file),
        "-p",
        "scripts.engineering.ci.pytest_receipts",
        f"--receipt-dir={tmp_path}",
    ]
    subprocess.run(cmd, env=env, capture_output=True, text=True)

    receipt_files = list(tmp_path.glob("local/1/master/receipt_*.json"))
    assert len(receipt_files) == 1

    with receipt_files[0].open() as f:
        data = json.load(f)

    assert "SECRET_TOKEN" not in data["environment"]
    assert data["environment"].get("GITHUB_RUN_ID") == "456"
