#!/usr/bin/env python3
"""
Script to generate a single text file containing the codebase context for LLMs.
It concatenates all relevant files, using 'git ls-files' to respect .gitignore.
"""

import os
import subprocess
import sys
import argparse

def get_git_files():
    """Returns a list of files tracked by git."""
    try:
        # Get list of files tracked by git
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=True
        )
        files = result.stdout.splitlines()
        return files
    except subprocess.CalledProcessError:
        print("Error: Not a git repository or git not found.", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'git' command not found.", file=sys.stderr)
        sys.exit(1)

def is_text_file(filepath):
    """Checks if a file is text-based and likely useful for LLM context."""
    # Exclude common binary/asset extensions
    binary_extensions = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.class', '.jar', '.exe',
        '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.svg',
        '.pdf', '.zip', '.tar', '.gz', '.whl', '.db', '.sqlite', '.parquet',
        '.eot', '.ttf', '.woff', '.woff2', '.mp3', '.mp4', '.avi'
    }

    _, ext = os.path.splitext(filepath)
    if ext.lower() in binary_extensions:
        return False

    # Heuristic: Read first chunk and check for null bytes
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(4096)
            if b'\x00' in chunk:
                return False

        # If it passes null byte check, try decoding as utf-8
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read(1024)
            return True
    except (UnicodeDecodeError, IOError):
        return False

def generate_context(output_file="llm_context.txt"):
    files = get_git_files()

    # Files to explicitly exclude (large lockfiles, auto-generated files that clutter context)
    exclude_files = {
        'package-lock.json',
        'uv.lock',
        'poetry.lock',
        'llm_context.txt', # Don't include self if present
        output_file
    }

    # Directories/Files to exclude based on path substrings
    exclude_paths = [
        'assets/',
        'site/',
        '.git/',
        'htmlcov/',
        '.mypy_cache/',
        '.pytest_cache/',
        '.ruff_cache/',
        '__pycache__/'
    ]

    count = 0
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(f"# Codebase Context\n")

        for filepath in sorted(files):
            # Check explicit excludes
            if os.path.basename(filepath) in exclude_files:
                continue

            # Check path excludes
            if any(ex in filepath for ex in exclude_paths):
                continue

            if not os.path.exists(filepath):
                continue

            if not is_text_file(filepath):
                continue

            # Write file content with XML-style tags for clarity
            out.write(f"\n<file path=\"{filepath}\">\n")

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    out.write(content)
                    if not content.endswith('\n'):
                        out.write('\n')
            except Exception as e:
                out.write(f"[Error reading file: {e}]\n")

            out.write(f"</file>\n")
            count += 1

    print(f"✅ Generated context in '{output_file}' with {count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate LLM context from codebase")
    parser.add_argument("-o", "--output", default="llm_context.txt", help="Output filename")
    args = parser.parse_args()

    generate_context(args.output)
