import re

with open("scripts/engineering/ci/check_mypy_diagnostic_ratchet.py", "r") as f:
    content = f.read()

new_main = """def _compare_diagnostics(current_diagnostics: dict[str, dict[str, dict[str, int]]], baseline: dict[str, Any]) -> list[str]:
    errors = []
    for file_path, messages in current_diagnostics.items():
        for msg, codes in messages.items():
            for code, count in codes.items():
                baseline_count = baseline.get(file_path, {}).get(msg, {}).get(code, 0)
                if count > baseline_count:
                    errors.append(
                        f"{file_path}: count for '{msg}' [{code}] increased from {baseline_count} to {count}"
                    )
    return errors

def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    log_path = repo_root / "reports" / "mypy_strict.log"
    baseline_path = repo_root / "configs" / "quality" / "mypy_diagnostic_baseline.json"

    current_diagnostics = _parse_mypy_output(log_path)

    if baseline_path.exists():
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                baseline = json.load(f)
        except json.JSONDecodeError:
            print("::error::Invalid JSON in mypy_diagnostic_baseline.json")
            return 1
    else:
        baseline = {}

    errors = _compare_diagnostics(current_diagnostics, baseline)

    if errors:
        print("::error::Mypy diagnostic ratchet failed. New type errors introduced:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("::notice::Mypy diagnostic ratchet passed.")
    return 0"""

content = re.sub(r'def main\(\) -> int:.*return 0', new_main, content, flags=re.DOTALL)

with open("scripts/engineering/ci/check_mypy_diagnostic_ratchet.py", "w") as f:
    f.write(content)
