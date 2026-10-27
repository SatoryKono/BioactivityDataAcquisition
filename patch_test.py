import re

with open("tests/unit/scripts/engineering/ci/test_mypy_diagnostic_ratchet.py", "r") as f:
    content = f.read()

content = content.replace(
    "def test_parse_mypy_output(tmp_path: Path) -> None:",
    "def test_parse_mypy_output(tmp_path: Path) -> None:\n    log = tmp_path / 'mypy.log'\n    log.touch()\n    # Test fail closed\n    with pytest.raises(FileNotFoundError):\n        _parse_mypy_output(tmp_path / 'nonexistent.log')\n\ndef test_parse_mypy_output_valid(tmp_path: Path) -> None:"
)

with open("tests/unit/scripts/engineering/ci/test_mypy_diagnostic_ratchet.py", "w") as f:
    f.write(content)
