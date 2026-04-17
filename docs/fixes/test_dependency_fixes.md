# Test Dependency Fixes

## Issues Resolved

### 1. Missing `respx` Dependency

**Error:**
```
ModuleNotFoundError: No module named 'respx'
```

**Root Cause:** The test environment was not properly set up with development dependencies.

**Solution:**
- Ran `bash scripts/engineering/dev/setup_env_wsl.sh` to create a proper WSL virtual environment
- This installed all test dependencies including `respx>=0.21`
- Environment location: `/home/fedor/.venvs/bioetl`

**Verification:**
```bash
source /home/fedor/.venvs/bioetl/bin/activate
python -c "import respx; print('respx version:', respx.__version__)"
# Output: respx version: 0.22.0
```

### 2. Missing `hotspot_family_metrics.py` Module

**Error:**
```
ModuleNotFoundError: No module named 'hotspot_family_metrics'
```

**Root Cause:** The file `scripts/engineering/qa/hotspot_family_metrics.py` was missing from the current branch but existed in git history.

**Solution:**
- Restored the file from commit `b4c2d5abb`
- Command used: `git show b4c2d5abb:scripts/engineering/qa/hotspot_family_metrics.py > scripts/engineering/qa/hotspot_family_metrics.py`
- File restored with 10,684 bytes

**File Contents:** Shared hotspot-family metrics helpers for RF-06 governance and reporting, including:
- `HotspotFamilyMetrics` dataclass
- `load_scorecard()` function
- `collect_hotspot_family_metrics()` function
- Various metric collection utilities

### 3. Async Test Configuration

**Issue:** Tests were failing with "async def functions are not natively supported"

**Solution:** Added explicit asyncio mode flag to pytest commands:
```bash
python -m pytest ... --asyncio-mode=auto
```

## Verification Results

### UniProt Adapter Tests
```bash
pytest tests/unit/infrastructure/adapters/uniprot/test_adapter.py::test_fetch_protein_success -v --asyncio-mode=auto
# Result: PASSED
```

### Hotspot Family Baseline Tests
```bash
pytest tests/unit/scripts/engineering/qa/test_report_hotspot_family_baseline.py -v --asyncio-mode=auto
# Result: 2 passed
```

## Environment Setup

For future reference, the proper way to set up the development environment:

```bash
# For WSL/Linux
bash scripts/engineering/dev/setup_env_wsl.sh

# Activate environment
source /home/fedor/.venvs/bioetl/bin/activate

# Run tests with async support
python -m pytest tests/... -v --asyncio-mode=auto
```

## Files Modified/Created

1. **Restored:** `scripts/engineering/qa/hotspot_family_metrics.py` (from git history)
2. **Environment:** `/home/fedor/.venvs/bioetl` (created by setup script)

## Dependencies Installed

Key test dependencies now available:
- `respx==0.22.0` (HTTP mocking)
- `pytest-asyncio==0.26.0` (async test support)
- `pytest==8.4.2`
- `httpx==0.28.1`
- All other dependencies from `pyproject.toml`

## Recommendations

1. **Environment Activation:** Always activate the virtual environment before running tests:
   ```bash
   source /home/fedor/.venvs/bioetl/bin/activate
   ```

2. **Async Tests:** Use `--asyncio-mode=auto` flag for pytest when running async tests

3. **Dependency Management:** Use the project's setup scripts rather than manual pip installs

4. **Missing Files:** Check git history when encountering missing module errors - files may have been removed in recent commits