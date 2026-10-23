import ast
import re
import sys
from pathlib import Path

def check_domain_types():
    domain_path = Path("src/bioetl/domain")
    if not domain_path.exists():
        print("Domain layer not found")
        return 1

    issues = []

    for py_file in domain_path.rglob("*.py"):
        with open(py_file) as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                continue

        # Check for Protocol imports in ports.py
        if py_file.name == "ports.py":
            has_protocol = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module == "typing" and any(
                        alias.name == "Protocol" for alias in node.names
                    ):
                        has_protocol = True
                        break
            if not has_protocol:
                issues.append(f"{py_file}: ports.py should use typing.Protocol")

        # Check for NewType usage in types.py
        if py_file.name == "types.py":
            has_newtype = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module == "typing" and any(
                        alias.name == "NewType" for alias in node.names
                    ):
                        has_newtype = True
                        break
            if not has_newtype:
                print(f"ℹ️  {py_file}: Consider using NewType for domain-specific types")

    if issues:
        print("❌ Type definition issues found:")
        for issue in issues:
            print(f"  {issue}")
        return 1
    else:
        print("✅ Domain layer type definitions look good")
        return 0

def check_any_usage():
    any_patterns = [
        r'\bAny\b',
        r':\s*Any\b',
        r'->\s*Any\b',
    ]

    warnings = []
    for layer in ["domain", "application"]:
        layer_path = Path(f"src/bioetl/{layer}")
        if not layer_path.exists():
            continue

        for py_file in layer_path.rglob("*.py"):
            with open(py_file) as f:
                content = f.read()

            for i, line in enumerate(content.split('\n'), 1):
                if 'TYPE_CHECKING' in line or line.strip().startswith('#'):
                    continue
                for pattern in any_patterns:
                    if re.search(pattern, line):
                        warnings.append(f"{py_file}:{i}: {line.strip()}")

    if warnings:
        print(f"⚠️  Found {len(warnings)} potential Any type usage(s):")
        for w in warnings[:10]:
            print(f"  {w}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more")
        print("\nConsider using more specific types where possible.")
    else:
        print("✅ No problematic Any type usage found")
    return 0

def main():
    exit_code = 0
    if check_domain_types() != 0:
        exit_code = 1
    if check_any_usage() != 0:
        pass # Warning only
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
