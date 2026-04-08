#!/usr/bin/env python3
"""Find functions longer than 100 lines."""

import ast
from pathlib import Path
import sys

def find_long_functions(directory: Path, min_lines: int = 100):
    """Find functions longer than min_lines."""
    long_functions = []
    
    for py_file in directory.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
            
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    func_lines = end_line - start_line + 1
                    
                    if func_lines > min_lines:
                        long_functions.append({
                            "file": str(py_file),
                            "function": node.name,
                            "lines": func_lines,
                            "start": start_line
                        })
                        
        except (SyntaxError, UnicodeDecodeError):
            continue
    
    return sorted(long_functions, key=lambda x: x["lines"], reverse=True)

if __name__ == "__main__":
    src_dir = Path("src/bioetl")
    long_functions = find_long_functions(src_dir)
    
    print(f"Found {len(long_functions)} functions longer than 100 lines:")
    for func in long_functions[:20]:  # Show top 20
        print(f"{func['file']}:{func['start']} - {func['function']}() - {func['lines']} lines")