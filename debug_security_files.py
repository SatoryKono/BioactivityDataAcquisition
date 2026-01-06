from pathlib import Path
import os

PROJECT_ROOT = Path(".").resolve()

def get_all_files():
    excluded = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "data",
        "build",
        "dist",
        ".idea",
        ".vscode",
        "logs",
        "tmp",
        "node_modules",
        "site",
        "htmlcov",
    }
    
    # Extensions checked in the test
    checked_extensions = {
        ".py",
        ".txt",
        ".yaml",
        ".yml",
        ".json",
        ".md",
    }

    files = []
    skipped_count = 0
    
    # Use os.walk for better performance and control than rglob
    for root, dirs, filenames in os.walk(PROJECT_ROOT):
        # Modify dirs in-place to skip excluded directories
        # This is much faster than rglob which iterates everything then filters
        dirs[:] = [d for d in dirs if d not in excluded]
        
        # Also skip if any part of the path is excluded (for nested excluded folders not caught by immediate check)
        # But os.walk with modifying dirs handles the subtree pruning.
        # We just need to check if the current root is valid.
        # Actually, verifying against 'excluded' in parts is safer.
        rel_root = Path(root).relative_to(PROJECT_ROOT)
        if any(part in excluded for part in rel_root.parts):
            continue

        for filename in filenames:
            file_path = Path(root) / filename
            if file_path.suffix.lower() in checked_extensions:
                files.append(file_path)
            else:
                skipped_count += 1
                
    return files

files = get_all_files()
print(f"Found {len(files)} files to scan.")

# Check for large files
for f in files:
    try:
        size = f.stat().st_size
        if size > 1024 * 1024: # 1MB
            print(f"Large file: {f} ({size/1024/1024:.2f} MB)")
    except Exception as e:
        print(f"Error accessing {f}: {e}")

