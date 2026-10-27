import re

with open("scripts/engineering/ci/check_mypy_diagnostic_ratchet.py", "r") as f:
    content = f.read()

# Refactor _parse_mypy_output to lower cognitive complexity
new_parse_func = """def _parse_line(line: str) -> tuple[str, str, str] | None:
    if ": error:" not in line:
        return None
    parts = line.split(":", 3)
    if len(parts) < 4:
        return None
    file_path = parts[0].strip()
    msg_and_code = parts[3].strip()
    code_start = msg_and_code.rfind("[")
    code_end = msg_and_code.rfind("]")
    if code_start != -1 and code_end != -1 and code_end > code_start:
        code = msg_and_code[code_start + 1 : code_end]
        msg = msg_and_code[:code_start].strip()
    else:
        code = "unknown"
        msg = msg_and_code
    return file_path, msg, code

def _parse_mypy_output(log_path: Path) -> dict[str, dict[str, dict[str, int]]]:
    \"\"\"Parse mypy log output into a dict of module -> message -> code -> count.\"\"\"
    diagnostics: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    if not log_path.exists():
        raise FileNotFoundError(
            f"mypy log file not found at {log_path}. Ensure mypy runs before this script."
        )

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            parsed = _parse_line(line)
            if parsed:
                file_path, msg, code = parsed
                diagnostics[file_path][msg][code] += 1

    return diagnostics"""

content = re.sub(r'def _parse_mypy_output.*?return diagnostics', new_parse_func, content, flags=re.DOTALL)

with open("scripts/engineering/ci/check_mypy_diagnostic_ratchet.py", "w") as f:
    f.write(content)
