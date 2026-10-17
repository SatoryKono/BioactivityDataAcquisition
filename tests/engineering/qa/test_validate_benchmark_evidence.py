import pytest
from scripts.engineering.qa.validate_benchmark_evidence import validate_evidence

pytestmark = pytest.mark.unit


def test_missing_observations(tmp_path):
    with pytest.raises(ValueError, match="Missing observations"):
        validate_evidence(tmp_path / "missing.json", "abc")


def test_empty_json(tmp_path):
    f = tmp_path / "empty.json"
    f.write_text("")
    with pytest.raises(ValueError, match="Empty JSON"):
        validate_evidence(f, "abc")


def test_malformed_json(tmp_path):
    f = tmp_path / "malformed.json"
    f.write_text("{")
    with pytest.raises(ValueError, match="Malformed JSON"):
        validate_evidence(f, "abc")


def test_zero_execution(tmp_path):
    f = tmp_path / "zero.json"
    f.write_text('{"benchmarks": []}')
    with pytest.raises(ValueError, match="Zero execution or all-skipped"):
        validate_evidence(f, "abc")


def test_failed_benchmark(tmp_path):
    f = tmp_path / "failed.json"
    f.write_text('{"benchmarks": [{"name": "test", "has_error": true}]}')
    with pytest.raises(ValueError, match="Failed benchmark detected: test"):
        validate_evidence(f, "abc")


def test_wrong_sha(tmp_path):
    f = tmp_path / "wrong.json"
    f.write_text('{"benchmarks": [{"name": "test"}], "commit_info": {"id": "123"}}')
    with pytest.raises(ValueError, match=r"Wrong SHA\. Expected 456, got 123"):
        validate_evidence(f, "456")


def test_missing_sha(tmp_path):
    f = tmp_path / "missing_sha.json"
    f.write_text('{"benchmarks": [{"name": "test"}]}')
    with pytest.raises(ValueError, match="No commit SHA found"):
        validate_evidence(f, "456")


def test_successful_validation(tmp_path):
    f = tmp_path / "success.json"
    payload = (
        '{"benchmarks": [{"name": "test"}], '
        '"commit_info": {"id": "123"}, '
        '"machine_info": {"system": "Linux"}}'
    )
    f.write_text(payload)
    manifest = validate_evidence(f, "123")
    assert manifest["revision"] == "123"
    assert manifest["environment_identity"]["system"] == "Linux"
    assert manifest["benchmarks_count"] == 1
