"""Category totals and workflow attribution for GitHub billing rows."""

from __future__ import annotations

from decimal import Decimal

from scripts.engineering.finances.github_billing_schema import GitHubBillingRecord

TOTAL_KEYS = (
    "actions_compute",
    "shared_storage",
    "copilot",
    "lfs",
    "other",
)
_RUNNER_SKU_MARKERS = ("linux", "windows", "macos")
_SHARED_STORAGE_SKUS = frozenset({"actions storage", "packages storage"})
_SEPARATE_STORAGE_SKUS = frozenset(
    {
        "actions cache storage",
        "actions custom image storage",
    }
)
WorkflowAttributionKey = tuple[str | None, str]


def _normalized_sku(sku: str) -> str:
    """Collapse report labels and API identifiers onto one SKU key."""
    return " ".join(sku.casefold().replace("_", " ").split())


def _require_report_currency(
    records: list[GitHubBillingRecord],
    report_currency: str,
) -> None:
    """Refuse an empty report or rows that do not match one explicit currency."""
    expected = report_currency.strip()
    if not expected:
        raise ValueError("report currency must be explicit")
    if not records:
        raise ValueError("billing report has no records")
    found = sorted({record.currency for record in records})
    if found != [expected]:
        raise ValueError(
            "billing records must use the report currency "
            f"{expected}; found {', '.join(found)}"
        )


def is_actions_compute(record: GitHubBillingRecord) -> bool:
    """Return whether the row is Actions runner usage rather than storage.

    Official usage-report SKUs look like ``Actions Linux``. Older normalized
    rows use a ``Compute - ...`` SKU. Storage SKUs stay out of this bucket.
    """
    product = record.product.casefold()
    sku = record.sku.casefold()
    if "actions" not in product or "storage" in sku:
        return False
    if "compute" in sku:
        return True
    return any(marker in sku for marker in _RUNNER_SKU_MARKERS)


def _is_shared_storage(record: GitHubBillingRecord) -> bool:
    """Return whether the row belongs in the shared artifact/package pool.

    Actions artifact storage and Packages storage share that pool. Actions
    cache storage and custom-image storage stay outside it.
    """
    if "shared storage" in record.product.casefold():
        return True
    sku = _normalized_sku(record.sku)
    if sku in _SEPARATE_STORAGE_SKUS:
        return False
    return sku in _SHARED_STORAGE_SKUS


def _category(record: GitHubBillingRecord) -> str:
    """Map one row onto a total bucket."""
    product = record.product.casefold()
    if is_actions_compute(record):
        return "actions_compute"
    if _is_shared_storage(record):
        return "shared_storage"
    if "copilot" in product:
        return "copilot"
    if "lfs" in product:
        return "lfs"
    return "other"


def calculate_totals(
    records: list[GitHubBillingRecord],
    report_currency: str,
) -> dict[str, Decimal]:
    """Sum net amounts by category for one explicit report currency."""
    _require_report_currency(records, report_currency)
    totals = {key: Decimal("0") for key in TOTAL_KEYS}
    for record in records:
        totals[_category(record)] += record.net_amount
    return totals


def extract_workflow_attribution(
    records: list[GitHubBillingRecord],
    report_currency: str,
) -> dict[WorkflowAttributionKey, Decimal]:
    """Attribute Actions compute net amount to ``(repository, workflow)``.

    A missing repository stays ``None`` and is not merged with a named
    repository that uses the same workflow path. Rows without a workflow path
    use the ``unattributed`` label.
    """
    _require_report_currency(records, report_currency)
    attribution: dict[WorkflowAttributionKey, Decimal] = {}
    for record in records:
        if not is_actions_compute(record):
            continue
        key = (record.repository, record.workflow_path or "unattributed")
        attribution[key] = attribution.get(key, Decimal("0")) + record.net_amount
    return attribution
