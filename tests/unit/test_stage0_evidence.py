import pytest
from scripts.engineering.ci.collect_stage0_evidence import sha256
from scripts.engineering.ci.evaluate_mypy import normalize_diagnostics

def test_sha256_dict():
    # Positive test
    data1 = {"a": 1, "b": 2}
    data2 = {"b": 2, "a": 1}
    assert sha256(data1) == sha256(data2)

def test_sha256_string():
    # Positive test
    assert sha256("test") == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

def test_normalize_diagnostics_removes_lines():
    # Positive test
    output = "src/file.py:10: error: Something went wrong\nsrc/file.py:15:20: note: See here\nSuccess: no issues found in 2607 source files"
    normalized = normalize_diagnostics(output)
    assert normalized == ["src/file.py: error: Something went wrong", "src/file.py: note: See here"]

def test_normalize_diagnostics_ignores_success_messages():
    # Negative test (ensure it strips out success/found msgs which vary)
    output = "Found 12 errors in 3 files"
    normalized = normalize_diagnostics(output)
    assert normalized == []
