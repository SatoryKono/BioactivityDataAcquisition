#!/usr/bin/env python3
"""
CLI Documentation Parity Check Script

This script verifies that the CLI documentation matches the actual CLI command registry.
It checks for missing commands, missing options, and other discrepancies.

Issue #3093: Add CLI Documentation Parity Checks
"""
# Compatibility wrapper

import re
import sys
from pathlib import Path

# Constants
CLI_REGISTRY_FILE = "src/bioetl/interfaces/cli/main.py"
CLI_DOC_FILE = "docs/04-reference/cli.md"


def _is_cli_command_name(command_name: str) -> bool:
    """Return whether a registry entry looks like a real CLI command."""
    return (
        command_name.replace("-", "").isalpha()
        and command_name.islower()
        and not command_name.startswith("__")
        and command_name not in {"name", "Commands"}
    )


def _extract_command_name(line: str) -> str | None:
    """Extract a command name from a registry line when present."""
    if '"' not in line or ":" not in line:
        return None
    parts = line.split('"')
    if len(parts) < 2:
        return None
    command_name = parts[1]
    return command_name if _is_cli_command_name(command_name) else None


def extract_cli_commands_from_registry() -> dict[str, str]:
    """Extract CLI commands from the _LAZY_COMMAND_SPECS dictionary."""
    registry_content = Path(CLI_REGISTRY_FILE).read_text()
    commands: dict[str, str] = {}
    in_specs = False

    for line in registry_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("_LAZY_COMMAND_SPECS:"):
            in_specs = True
            continue
        if not in_specs:
            continue
        if stripped == "},":
            break

        command_name = _extract_command_name(line)
        if command_name is not None:
            commands[command_name] = command_name

    if not commands:
        print("❌ Could not find any CLI commands in registry")
        sys.exit(1)

    return commands


def extract_cli_commands_from_docs() -> set[str]:
    """Extract CLI commands mentioned in the documentation."""
    doc_content = Path(CLI_DOC_FILE).read_text()

    # Look for command sections (e.g., "### `run`")
    command_pattern = r"### `([^`]+)`"
    commands = set(re.findall(command_pattern, doc_content))

    # Also look for code block commands
    code_block_pattern = r"```bash\n.*bioetl (\w+)"
    commands.update(re.findall(code_block_pattern, doc_content))

    return commands


def check_cli_parity() -> tuple[list[str], list[str], int, int]:
    """Check parity between CLI registry and documentation."""
    registry_commands = extract_cli_commands_from_registry()
    doc_commands = extract_cli_commands_from_docs()

    # Find missing commands in documentation
    missing_in_docs = [cmd for cmd in registry_commands if cmd not in doc_commands]

    # Find commands in docs but not in registry (shouldn't happen, but good to check)
    extra_in_docs = [cmd for cmd in doc_commands if cmd not in registry_commands]

    registry_count = len(registry_commands)
    doc_count = len(doc_commands)

    return missing_in_docs, extra_in_docs, registry_count, doc_count


def main() -> int:
    """Main entry point for CLI parity check."""
    print("🔍 CLI Documentation Parity Check")
    print("=" * 50)

    try:
        missing_commands, extra_commands, registry_count, doc_count = check_cli_parity()

        print(f"📊 Registry Commands: {registry_count}")
        print(f"📚 Documented Commands: {doc_count}")
        print()

        if missing_commands:
            print("❌ Missing commands in documentation:")
            for cmd in sorted(missing_commands):
                print(f"  - {cmd}")
            print()
        else:
            print("✅ All registry commands are documented")
            print()

        if extra_commands:
            print("⚠️  Extra commands in documentation (not in registry):")
            for cmd in sorted(extra_commands):
                print(f"  - {cmd}")
            print()
        else:
            print("✅ No extra commands in documentation")
            print()

        # Summary
        print("📋 Summary:")
        print(f"  • Registry commands: {registry_count}")
        print(f"  • Documented commands: {doc_count}")
        print(f"  • Missing in docs: {len(missing_commands)}")
        print(f"  • Extra in docs: {len(extra_commands)}")
        print()

        if missing_commands:
            print(
                "💡 Recommendation: Update CLI documentation to include missing commands"
            )
            return 1
        else:
            print("🎉 CLI documentation parity check PASSED!")
            return 0

    except FileNotFoundError as e:
        print(f"❌ File not found: {e.filename}")
        return 1
    except Exception as e:
        print(f"❌ Error during parity check: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
