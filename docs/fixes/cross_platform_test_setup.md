# Cross-Platform Test Setup Guide

## Issue Description

Tests are failing with `ModuleNotFoundError: No module named 'respx'` when run from Windows, even though the environment was set up in WSL.

## Root Cause

The project supports both Windows and WSL environments, but they require separate setup:
- **Windows PowerShell**: Uses `.venv-win` and Windows-specific scripts
- **WSL/Linux**: Uses external venv at `~/.venvs/bioetl` and bash scripts

The error occurs when trying to run Windows tests without the Windows environment properly set up.

## Solution

### For Windows PowerShell

```powershell
# Navigate to project root
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition2

# Set up Windows environment
.\scripts\engineering\dev\setup_env_windows.ps1

# This will create .venv-win and install all dependencies
```

### For WSL/Linux

```bash
# Navigate to project root
cd /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2

# Set up WSL environment
bash scripts/engineering/dev/setup_env_wsl.sh

# This creates venv at ~/.venvs/bioetl
```

## Environment Activation

### Windows
```powershell
# Activate Windows venv
.\.venv-win\Scripts\Activate.ps1

# Run tests
python -m pytest tests\unit\infrastructure\adapters\uniprot\test_adapter.py -v --asyncio-mode=auto
```

### WSL/Linux
```bash
# Activate WSL venv
source ~/.venvs/bioetl/bin/activate

# Run tests
python -m pytest tests/unit/infrastructure/adapters/uniprot/test_adapter.py -v --asyncio-mode=auto
```

## Key Differences

| Aspect | Windows | WSL/Linux |
|--------|----------|------------|
| **Environment location** | `.venv-win` (project-local) | `~/.venvs/bioetl` (external) |
| **Setup script** | `setup_env_windows.ps1` | `setup_env_wsl.sh` |
| **Activation** | `.\.venv-win\Scripts\Activate.ps1` | `source ~/.venvs/bioetl/bin/activate` |
| **Python path** | `.\.venv-win\Scripts\python.exe` | `~/.venvs/bioetl/bin/python` |
| **Test runner** | `.\scripts\engineering\dev\run_pytest.ps1` | `bash scripts/engineering/dev/run_pytest.sh` |

## Common Issues

### 1. "ModuleNotFoundError: No module named 'respx'"

**Cause:** Running tests without activating the correct virtual environment.

**Solution:**
- Windows: Activate `.venv-win` first
- WSL: Activate `~/.venvs/bioetl` first

### 2. "async def functions are not natively supported"

**Cause:** Missing pytest-asyncio plugin or incorrect asyncio mode.

**Solution:** Add `--asyncio-mode=auto` to pytest command.

### 3. "ModuleNotFoundError: No module named 'hotspot_family_metrics'"

**Cause:** Missing file that was removed from current branch.

**Solution:** Restored from git history (commit `b4c2d5abb`).

## Recommended Workflow

### For Windows Development
```powershell
# One-time setup
.\scripts\engineering\dev\setup_env_windows.ps1

# Daily work
.\.venv-win\Scripts\Activate.ps1
python -m pytest tests\... -v --asyncio-mode=auto
```

### For WSL Development
```bash
# One-time setup
bash scripts/engineering/dev/setup_env_wsl.sh

# Daily work
source ~/.venvs/bioetl/bin/activate
python -m pytest tests/... -v --asyncio-mode=auto
```

## Mixed Environment Considerations

If you work in both Windows and WSL:
1. **Keep environments separate** - Don't share `.venv` between OS
2. **Use OS-appropriate scripts** - Windows: `.ps1`, WSL: `.sh`
3. **Check current environment** - `uname -a` (WSL) vs `$env:OS` (Windows)
4. **File path differences** - Windows: `E:\...`, WSL: `/mnt/e/...`

## Verification Commands

### Check active environment (Windows)
```powershell
python -c "import sys; print(sys.executable)"
# Should show: .\.venv-win\Scripts\python.exe
```

### Check active environment (WSL)
```bash
python -c "import sys; print(sys.executable)"
# Should show: /home/fedor/.venvs/bioetl/bin/python
```

### Verify respx installation
```bash
python -c "import respx; print('respx version:', respx.__version__)"
# Should show version without errors
```

## Troubleshooting

### If tests still fail after setup:

1. **Verify activation:** Check that virtual environment is active
2. **Check Python path:** Ensure you're using venv Python, not system Python
3. **Reinstall dependencies:** Run setup script again
4. **Check file paths:** Ensure you're in correct OS environment
5. **Clean cache:** Remove `.pytest_cache` and `__pycache__` directories

### Common Windows-specific issues:

- **Execution policy:** Run PowerShell as Administrator for first setup
- **Path length:** Use short paths or enable long path support
- **Line endings:** Ensure git is configured for proper line ending handling

### Common WSL-specific issues:

- **Permission errors:** Use `chmod` to fix file permissions
- **Windows file access:** Use `/mnt/e/...` paths instead of `E:\...`
- **Locale warnings:** Set `export LC_ALL=C.UTF-8` if needed
