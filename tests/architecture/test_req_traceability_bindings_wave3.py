from __future__ import annotations

"""Wave3 concrete REQ traceability bindings — issue #9805.

Binds remaining 35 concrete untraced REQ IDs (one CSV, serial).

Each docstring line cites its REQ ID so grep ``REQ-[A-Z]+-[0-9]{3}`` in
``tests/**/*.py`` covers the row.

Surfaces listed in ``WAVE3_CONCRETE_SURFACES`` must exist — the guard
below asserts existence only; semantic content is proved by the
co-located architecture/unit tests named in the CSV ``executable_surface``.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

_ROOT = Path(__file__).resolve().parents[2]

# REQ_ID -> tuple of surface paths that MUST exist.
WAVE3_CONCRETE_SURFACES: dict[str, tuple[str, ...]] = {
    # 1. Архитектура и Слои
    "REQ-ARCH-011": ("tests/unit/domain/exceptions/test_base_exceptions.py",),
    "REQ-ARCH-012": ("tests/unit/domain/exceptions/test_base_exceptions.py",),
    "REQ-ARCH-013": ("tests/unit/application/services/test_error_handler.py",),
    "REQ-ARCH-030": ("tests/architecture/test_no_random_in_writers.py",),
    "REQ-ARCH-031": (
        "tests/architecture/test_no_datetime_now_in_infrastructure.py",
        "tests/architecture/test_no_datetime_now_in_domain.py",
        "tests/architecture/test_replay_critical_time_seams.py",
    ),
    # 5. Операции и Control Plane
    "REQ-AUDIT-001": (
        "tests/unit/domain/ports/test_noop_audit.py",
        "tests/unit/infrastructure/audit/test_file_audit.py",
    ),
    "REQ-AUDIT-002": (
        "tests/unit/domain/ports/test_noop_audit.py",
        "tests/unit/infrastructure/audit/test_file_audit.py",
    ),
    # 2. Поток Данных
    "REQ-CONF-001": ("tests/unit/domain/test_runtime_config.py",),
    "REQ-DATA-002": ("tests/unit/infrastructure/storage/test_bronze_zstd_memory_policy.py",),
    "REQ-DATA-003": ("tests/unit/infrastructure/storage/test_bronze_zstd_memory_policy.py",),
    "REQ-DATA-005": ("src/bioetl/infrastructure/storage/bronze_writer.py",),
    "REQ-DATA-010": ("src/bioetl/infrastructure/storage/gold/io_mixin.py",),
    "REQ-DELTA-002": (
        ".github/workflows/vacuum.yml",
        "scripts/ops/data/vacuum_delta.py",
    ),
    "REQ-DELTA-003": ("scripts/ops/data/vacuum_delta.py",),
    # validation
    "REQ-VAL-001": ("tests/unit/infrastructure/storage/test_silver_writer_validation.py",),
    "REQ-VAL-002": ("tests/unit/application/core/test_batch_writer_io_mixin.py",),
    "REQ-VAL-003": ("tests/unit/application/core/test_quarantine_manager.py",),
    "REQ-VAL-004": ("tests/unit/infrastructure/schemas/test_dq_config.py",),
    "REQ-VAL-005": ("tests/integration/config/test_dq_config_loading.py",),
    "REQ-VAL-006": ("tests/benchmarks/test_json_serialization.py",),
    "REQ-VAL-007": ("tests/unit/infrastructure/storage/test_deterministic_serialization.py",),
    "REQ-VAL-008": ("tests/architecture/test_dq_contract_patterns.py",),
    # 2.7 / 2.9–2.10
    "REQ-BACKFILL-001": ("src/bioetl/infrastructure/storage/metadata_writer.py",),
    "REQ-BACKFILL-002": ("src/bioetl/domain/types/enums.py",),
    "REQ-BACKFILL-004": ("src/bioetl/application/core/lifecycle/lock_runtime.py",),
    "REQ-NULL-001": ("tests/unit/infrastructure/storage/test_silver_writer_key_nullability.py",),
    "REQ-QUARANTINE-001": ("tests/unit/infrastructure/quarantine/test_unified_quarantine.py",),
    # 3. Обработка Ошибок
    "REQ-ERR-015": ("tests/unit/infrastructure/adapters/http/test_health_monitor.py",),
    "REQ-RETRY-001": ("tests/unit/infrastructure/adapters/decorators/test_wrap_with_resilience.py",),
    "REQ-CB-001": ("tests/unit/infrastructure/test_circuit_breaker.py",),
    "REQ-OBS-010": ("tests/unit/infrastructure/adapters/http/test_health_monitor.py",),
    "REQ-LOCK-003": ("tests/unit/infrastructure/locking/test_memory_lock.py",),
    # 8 DX + Provider
    "REQ-DX-001": ("tests/architecture/test_ops_command_surfaces.py",),
    "REQ-DX-003": ("tests/architecture/test_code_formatting.py",),
    "REQ-PROVIDER-001": ("tests/unit/infrastructure/adapters/chembl/test_chembl_client.py",),
}


def test_wave3_concrete_req_surfaces_exist() -> None:
    """REQ-ARCH-011 REQ-ARCH-012 REQ-ARCH-013 REQ-ARCH-030 REQ-ARCH-031
    REQ-AUDIT-001 REQ-AUDIT-002 REQ-CONF-001 REQ-DATA-002 REQ-DATA-003
    REQ-DATA-005 REQ-DATA-010 REQ-DELTA-002 REQ-DELTA-003
    REQ-VAL-001 REQ-VAL-002 REQ-VAL-003 REQ-VAL-004 REQ-VAL-005 REQ-VAL-006
    REQ-VAL-007 REQ-VAL-008 REQ-BACKFILL-001 REQ-BACKFILL-002
    REQ-BACKFILL-004 REQ-NULL-001 REQ-QUARANTINE-001 REQ-ERR-015 REQ-RETRY-001
    REQ-CB-001 REQ-OBS-010 REQ-LOCK-003 REQ-DX-001 REQ-DX-003 REQ-PROVIDER-001
    — wave3 binds 35 concrete REQ IDs to existing surfaces.
    """
    assert len(WAVE3_CONCRETE_SURFACES) == 35

    missing: list[str] = []
    for req_id, surfaces in sorted(WAVE3_CONCRETE_SURFACES.items()):
        assert surfaces, f"{req_id} empty"
        for rel in surfaces:
            if not (_ROOT / rel).exists():
                missing.append(f"{req_id}: {rel}")

    assert not missing, "Wave3 surfaces missing:\n" + "\n".join(f"  - {m}" for m in missing)
