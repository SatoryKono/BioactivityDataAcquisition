"""Content-addressed RF-001 baseline manifest.

Present repository materials are hashed. Original M, the saved Excel result
cache, and the IUPHAR snapshot payload are recorded as ``source_unavailable``
when this checkout does not contain their bytes. That status is not a
confirmed ``not_found``.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .baseline_semantics import (
    BASELINE_ID,
    ISSUE,
    RECORDED_ON,
    SNAPSHOT_ANNOTATION_CAPABILITY,
    contract_document,
)
from .gtopdb_2026_3_1 import (
    ARCHIVE_SHA256,
    RELEASE,
    SQL_SHA256,
    TARGETS_CSV_SHA256,
)
from .stage0.io import atomic_write_bytes, canonical_json_bytes, sha256_bytes

MANIFEST_RELATIVE_PATH = "data/iuphar_target_class/baseline/rf001/manifest.json"
BASELINE_REVISION = (
    "e01ca762a3ffc5f2a4bd4ea89f17fa807e49b9e2"  # pragma: allowlist secret
)
INCOMPLETE_HISTORY = "baseline revision is not in this checkout"
_SHA256_WIDTH = 64
_REVISION_PATTERN = r"[0-9a-f]{40}"

_M_NOTE = (
    "Исходный M в этом checkout отсутствует. Каталог stage0 не содержит "
    "version_id. Утверждения о семантике M не привязаны к версии. Это "
    "source_unavailable, а не подтверждённый not_found."
)
_CACHE_NOTE = (
    "Сохранённые таблицы Excel в этом checkout отсутствуют. Кэш результата "
    "не является свежим пересчётом M и не является биологическим эталоном. "
    "Это source_unavailable, а не подтверждённый not_found."
)
_SNAPSHOT_NOTE = (
    "Байты снимка в checkout отсутствуют. Выпуск опознаётся SHA-256 архива, "
    "SQL и CSV. Возможность снимка — family_only. Непредставленная мишень "
    "остаётся source_unavailable, а не not_found."
)


@dataclass(frozen=True, slots=True)
class MaterialSpec:
    """One manifest row. ``path`` is empty when the bytes are not in checkout."""

    material_id: str
    role: str
    path: str | None
    note: str
    availability: str = "present"


MATERIAL_SPECS: tuple[MaterialSpec, ...] = (
    MaterialSpec(
        "acceptance_stages",
        "acceptance",
        "data/iuphar_target_class/acceptance/stages_0_3_report.json",
        "Приёмка этапов 0–3. Биологическая точность не принята.",
    ),
    MaterialSpec(
        "acceptance_tc10_evidence",
        "acceptance",
        "data/iuphar_target_class/acceptance/tc10/engineering-evidence.md",
        "Инженерное свидетельство TC-10. Не эталон M.",
    ),
    MaterialSpec(
        "acceptance_tc10_receipt",
        "acceptance",
        "data/iuphar_target_class/acceptance/tc10/engineering-run-receipt.json",
        "Квитанция инженерного прогона TC-10.",
    ),
    MaterialSpec(
        "acceptance_tc10_trace",
        "acceptance",
        "data/iuphar_target_class/acceptance/tc10/traceability.json",
        "Трассировка контрпримеров TC-10, включая Distinct и Other.",
    ),
    MaterialSpec(
        "acceptance_volume_fixture",
        "acceptance",
        "data/iuphar_target_class/acceptance/volume_fixture.json",
        "Синтетический объёмный fixture. Не контрольная когорта.",
    ),
    MaterialSpec(
        "classifier_source",
        "classifier",
        "src/iuphar_target_class/resolution.py",
        "Текущая таблица решений классификатора до смены правил.",
    ),
    MaterialSpec(
        "composite_config",
        "configuration",
        "configs/composites/target.yaml",
        "Composite target. Полные признаки появляются после dependency joins.",
    ),
    MaterialSpec(
        "control_assay",
        "control_input",
        "data/input/assay.csv",
        "Контрольная выгрузка assay. Не результат M.",
    ),
    MaterialSpec(
        "control_target",
        "control_input",
        "data/input/target.csv",
        "Контрольная выгрузка target. Не результат M.",
    ),
    MaterialSpec(
        "domain_config",
        "configuration",
        "src/bioetl/domain/config/target_classification.py",
        "Девять полей V31. Словарь RF-001 их не расширяет.",
    ),
    MaterialSpec(
        "entity_config",
        "configuration",
        "configs/entities/chembl/target.yaml",
        "Зафиксированный mode off, контракт 3.0.0, таблицы V30.",
    ),
    MaterialSpec(
        "iuphar_release_pins",
        "iuphar_derivation",
        "src/iuphar_target_class/gtopdb_2026_3_1.py",
        "Производные семейства GtoPdb 2026.3.1 и пины исходных байтов.",
    ),
    MaterialSpec(
        "iuphar_snapshot_bytes",
        "iuphar_snapshot",
        None,
        _SNAPSHOT_NOTE,
        availability="source_unavailable",
    ),
    MaterialSpec(
        "m_catalog",
        "m_catalog",
        "data/iuphar_target_class/stage0/m_code_versions.csv",
        "Каталог версий M этапа 0. В репозитории есть только заголовок.",
    ),
    MaterialSpec(
        "m_source",
        "m_source",
        None,
        _M_NOTE,
        availability="source_unavailable",
    ),
    MaterialSpec(
        "manifest_source",
        "rf001_contract",
        "src/iuphar_target_class/baseline_manifest.py",
        "Построитель manifest RF-001.",
    ),
    MaterialSpec(
        "normalization_source",
        "normalization",
        "src/iuphar_target_class/normalization.py",
        "Нормализация входа. Версия missing_markers не утверждена.",
    ),
    MaterialSpec(
        "result_cache",
        "result_cache",
        None,
        _CACHE_NOTE,
        availability="source_unavailable",
    ),
    MaterialSpec(
        "rules_record",
        "rules",
        "data/iuphar_target_class/policy/policy.json",
        "Опубликованная запись правил этапа 1. Байты исторической записи.",
    ),
    MaterialSpec(
        "rules_source",
        "rules",
        "src/iuphar_target_class/policy.py",
        "Источник правил этапа 1. RF-001 не меняет policy_document.",
    ),
    MaterialSpec(
        "semantics_source",
        "rf001_contract",
        "src/iuphar_target_class/baseline_semantics.py",
        "Словарь полей и таблица решений RF-001.",
    ),
    MaterialSpec(
        "stage0_checks",
        "acceptance",
        "data/iuphar_target_class/stage0/content_checks.csv",
        "Проверка содержимого этапа 0. Источники M не выбраны.",
    ),
    MaterialSpec(
        "stage0_manifest",
        "acceptance",
        "data/iuphar_target_class/stage0/manifest.json",
        "Manifest этапа 0. Версия M не установлена.",
    ),
    MaterialSpec(
        "stage0_provenance",
        "acceptance",
        "data/iuphar_target_class/stage0/provenance_map.csv",
        "Происхождение L1, L2, G2P и target_all не установлено.",
    ),
    MaterialSpec(
        "stage0_report",
        "acceptance",
        "data/iuphar_target_class/stage0/stage_report.json",
        "Отчёт этапа 0 без биологической приёмки.",
    ),
    MaterialSpec(
        "stage0_survey",
        "acceptance",
        "data/iuphar_target_class/stage0/survey.json",
        "Обзор ожидаемых материалов. M и Excel в набор не выбраны.",
    ),
)


def build_baseline_manifest(repo_root: Path) -> dict[str, object]:
    """Hash the checkout against the pinned baseline revision."""
    root = repo_root.resolve()
    if not _commit_available(root, BASELINE_REVISION):
        raise RuntimeError(INCOMPLETE_HISTORY)
    semantics = contract_document()
    return {
        "artifact": "iuphar_rf001_baseline_manifest",
        "baseline_id": BASELINE_ID,
        "baseline_revision": BASELINE_REVISION,
        "biological_accuracy_accepted": False,
        "configuration": semantics["configuration"],
        "fresh_recalculation": False,
        "issue": ISSUE,
        "iuphar_release": {
            "annotation_capability": SNAPSHOT_ANNOTATION_CAPABILITY,
            "archive_sha256": ARCHIVE_SHA256,
            "release": RELEASE,
            "snapshot_bytes": "source_unavailable",
            "sql_sha256": SQL_SHA256,
            "targets_csv_sha256": TARGETS_CSV_SHA256,
        },
        "m_semantics_bound": False,
        "materials": [_material_row(root, spec) for spec in MATERIAL_SPECS],
        "recorded_on": RECORDED_ON,
        "semantics": semantics,
        "semantics_sha256": sha256_bytes(canonical_json_bytes(semantics)),
    }


def verify_baseline_manifest(
    repo_root: Path, document: dict[str, object]
) -> tuple[str, ...]:
    """Return completeness and hash problems. An empty tuple means the pin holds."""
    problems: list[str] = []
    _check_header(document, problems)
    materials = document.get("materials")
    if not isinstance(materials, list):
        return ("materials is missing",)
    _check_material_set(materials, problems)
    root = repo_root.resolve()
    present: list[Mapping[str, object]] = []
    for row in materials:
        if isinstance(row, dict):
            _check_material(row, problems)
            if row.get("availability") == "present":
                present.append(row)
        else:
            problems.append("material row is not an object")
    revision = document.get("baseline_revision")
    if isinstance(revision, str):
        problems.extend(historical_blob_problems(root, revision, present))
    else:
        problems.append(INCOMPLETE_HISTORY)
    return tuple(problems)


def write_baseline_manifest(repo_root: Path) -> Path:
    """Write the manifest atomically inside ``repo_root``."""
    root = repo_root.resolve()
    destination = root / MANIFEST_RELATIVE_PATH
    payload = canonical_json_bytes(build_baseline_manifest(root))
    atomic_write_bytes(destination, payload, root=root)
    return destination


def _material_row(root: Path, spec: MaterialSpec) -> dict[str, object]:
    if spec.availability == "source_unavailable":
        return _unavailable_row(spec)
    if spec.path is None:
        raise ValueError(f"{spec.material_id} is present but has no path")
    worktree = sha256_bytes((root / spec.path).read_bytes())
    baseline = _blob_sha256(root, BASELINE_REVISION, spec.path)
    return {
        "availability": "present",
        "baseline_sha256": baseline,
        "delta": _delta(baseline, worktree),
        "fresh_recalculation": False,
        "material_id": spec.material_id,
        "note": spec.note,
        "path": spec.path,
        "role": spec.role,
        "semantics_bound": False,
        "version_id": None,
        "worktree_sha256": worktree,
    }


def _unavailable_row(spec: MaterialSpec) -> dict[str, object]:
    return {
        "availability": "source_unavailable",
        "baseline_sha256": None,
        "confirmed_absence": False,
        "delta": "absent_from_checkout",
        "fresh_recalculation": False,
        "material_id": spec.material_id,
        "note": spec.note,
        "path": None,
        "role": spec.role,
        "semantics_bound": False,
        "version_id": None,
        "worktree_sha256": None,
    }


def _delta(baseline: str | None, worktree: str) -> str:
    if baseline is None:
        return "absent_on_baseline"
    if baseline == worktree:
        return "matches_baseline"
    return "content_changed_by_rf001"


def historical_blob_problems(
    root: Path,
    revision: str,
    rows: list[Mapping[str, object]],
) -> tuple[str, ...]:
    """Compare recorded baseline hashes to one git commit.

    A missing commit is incomplete history. It is not evidence that each path
    was absent, and it does not consult the live worktree.
    """
    if not _commit_available(root, revision):
        return (INCOMPLETE_HISTORY,)
    problems: list[str] = []
    for row in rows:
        if row.get("availability") != "present":
            continue
        material_id = str(row.get("material_id"))
        path = row.get("path")
        if not isinstance(path, str):
            problems.append(f"{material_id} path is missing")
            continue
        if row.get("baseline_sha256") != _blob_sha256(root, revision, path):
            problems.append(f"{material_id} baseline hash mismatch")
    return tuple(problems)


def _commit_available(root: Path, revision: str) -> bool:
    if re.fullmatch(_REVISION_PATTERN, revision) is None:
        return False
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return probe.returncode == 0


def _blob_sha256(root: Path, revision: str, path: str) -> str | None:
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}:{path}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0:
        return None
    blob = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{path}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if blob.returncode != 0:
        return None
    return sha256_bytes(blob.stdout)


_HEADER_CHECKS: tuple[tuple[str, object, str], ...] = (
    ("artifact", "iuphar_rf001_baseline_manifest", "artifact id mismatch"),
    ("baseline_id", BASELINE_ID, "baseline id mismatch"),
    ("baseline_revision", BASELINE_REVISION, "baseline revision mismatch"),
    ("m_semantics_bound", False, "M semantics must stay unbound"),
    ("fresh_recalculation", False, "baseline is not a recalculation"),
    (
        "biological_accuracy_accepted",
        False,
        "biological accuracy is not accepted",
    ),
)


def _check_header(document: dict[str, object], problems: list[str]) -> None:
    for key, expected, message in _HEADER_CHECKS:
        if document.get(key) != expected:
            problems.append(message)
    embedded = document.get("semantics")
    _check_embedded_semantics(document, embedded, problems)
    _check_release(document.get("iuphar_release"), embedded, problems)


def _check_embedded_semantics(
    document: dict[str, object], embedded: object, problems: list[str]
) -> None:
    if not isinstance(embedded, dict):
        problems.append("semantics document is missing")
        return
    digest = sha256_bytes(canonical_json_bytes(embedded))
    if document.get("semantics_sha256") != digest:
        problems.append("semantics hash mismatch")
    if document.get("configuration") != embedded.get("configuration"):
        problems.append("configuration claim mismatch")


def _check_release(release: object, embedded: object, problems: list[str]) -> None:
    if not isinstance(release, dict):
        problems.append("iuphar release is missing")
        return
    _check_release_pins(release, problems)
    if release.get("snapshot_bytes") != "source_unavailable":
        problems.append("missing snapshot bytes must stay source_unavailable")
    if not isinstance(embedded, dict):
        return
    recorded = release.get("annotation_capability")
    expected = embedded.get("snapshot_annotation_capability")
    if recorded != expected:
        problems.append("snapshot capability mismatch")


def _check_release_pins(release: dict[str, object], problems: list[str]) -> None:
    for key in ("archive_sha256", "sql_sha256", "targets_csv_sha256"):
        value = release.get(key)
        if isinstance(value, str) and len(value) == _SHA256_WIDTH:
            continue
        problems.append(f"IUPHAR {key} shape mismatch")


def _check_material_set(materials: list[object], problems: list[str]) -> None:
    expected = [spec.material_id for spec in MATERIAL_SPECS]
    found = [row.get("material_id") for row in materials if isinstance(row, dict)]
    if found != expected:
        problems.append("material id set mismatch")
    roles = {row.get("role") for row in materials if isinstance(row, dict)}
    required = {spec.role for spec in MATERIAL_SPECS}
    if roles != required:
        problems.append("material role set mismatch")


def _check_material(row: dict[str, object], problems: list[str]) -> None:
    material_id = str(row.get("material_id"))
    _check_spec_binding(material_id, row, problems)
    availability = row.get("availability")
    if availability == "not_found":
        problems.append(f"{material_id} uses confirmed not_found")
        return
    if availability == "source_unavailable":
        _check_unavailable(material_id, row, problems)
        return
    if availability != "present":
        problems.append(f"{material_id} has unknown availability")
        return
    _check_present(material_id, row, problems)


def _check_spec_binding(
    material_id: str, row: dict[str, object], problems: list[str]
) -> None:
    spec = next(
        (item for item in MATERIAL_SPECS if item.material_id == material_id),
        None,
    )
    if spec is None:
        problems.append(f"{material_id} is not a baseline material")
        return
    if row.get("role") != spec.role:
        problems.append(f"{material_id} role mismatch")
    if row.get("path") != spec.path:
        problems.append(f"{material_id} path mismatch")
    if row.get("availability") != spec.availability:
        problems.append(f"{material_id} availability mismatch")


def _check_unavailable(
    material_id: str, row: dict[str, object], problems: list[str]
) -> None:
    if row.get("path") is not None:
        problems.append(f"{material_id} unavailable row has a path")
    if row.get("baseline_sha256") is not None or row.get("worktree_sha256") is not None:
        problems.append(f"{material_id} unavailable row has a hash")
    if row.get("delta") != "absent_from_checkout":
        problems.append(f"{material_id} unavailable delta mismatch")
    if (
        row.get("semantics_bound") is not False
        or row.get("fresh_recalculation") is not False
    ):
        problems.append(f"{material_id} must not bind semantics or a recalculation")
    if row.get("confirmed_absence") is not False:
        problems.append(f"{material_id} is not a confirmed absence")


def _check_present(
    material_id: str,
    row: dict[str, object],
    problems: list[str],
) -> None:
    if not isinstance(row.get("path"), str):
        problems.append(f"{material_id} path is missing")
        return
    worktree = row.get("worktree_sha256")
    baseline = row.get("baseline_sha256")
    if not _delta_matches(row.get("delta"), baseline, worktree):
        problems.append(f"{material_id} delta does not match the hashes")
    if not _sha256_or_none(baseline) or not _sha256_or_none(worktree):
        problems.append(f"{material_id} hash shape mismatch")


def _delta_matches(delta: object, baseline: object, worktree: object) -> bool:
    if delta == "matches_baseline":
        return isinstance(baseline, str) and baseline == worktree
    if delta == "content_changed_by_rf001":
        return (
            isinstance(baseline, str)
            and isinstance(worktree, str)
            and baseline != worktree
        )
    if delta == "absent_on_baseline":
        return baseline is None and isinstance(worktree, str)
    return False


def _sha256_or_none(value: object) -> bool:
    if value is None:
        return True
    return isinstance(value, str) and len(value) == _SHA256_WIDTH and value.islower()


__all__ = [
    "BASELINE_REVISION",
    "INCOMPLETE_HISTORY",
    "MANIFEST_RELATIVE_PATH",
    "MATERIAL_SPECS",
    "MaterialSpec",
    "build_baseline_manifest",
    "historical_blob_problems",
    "verify_baseline_manifest",
    "write_baseline_manifest",
]
