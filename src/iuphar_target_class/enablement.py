"""Controlled contour status. Production configs are not flipped here."""

from __future__ import annotations

from collections.abc import Mapping


def contour_status(evidence: Mapping[str, object] | None = None) -> dict[str, object]:
    """Report shadow, isolated enrich, and a refused main contour.

    ``biological_accuracy_accepted`` stays false unless the supplied evidence
    sets it explicitly. A missing CI SHA is ``NOT_RUN``, not a pass.
    """
    record = dict(evidence or {})
    sha = record.get("ci_sha")
    biological = record.get("biological_accuracy_accepted") is True
    gates = (
        biological,
        record.get("fk_closure") is True,
        record.get("xlsx_round_trip") is True,
        record.get("rehearsal_rollback_passed") is True,
        isinstance(sha, str) and bool(sha),
    )
    return {
        "shadow": "available",
        "enrich": "isolated_catalog_only",
        "main_contour": "ready" if all(gates) else "refused",
        "ci_status": "RECORDED" if isinstance(sha, str) and sha else "NOT_RUN",
        "biological_accuracy_accepted": biological,
        "production_configs": "unchanged",
    }


__all__ = ["contour_status"]
