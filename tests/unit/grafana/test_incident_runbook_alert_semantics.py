"""Guard incident-response alert names and the Gold procedure wording."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
RULES_PATH = ROOT / "grafana/prometheus-rules/bioetl_observability.yml"
OPERATOR_DOCS = (
    ROOT / "docs/05-operations/runbooks/incident-response.md",
    ROOT / "docs/05-operations/runbooks/stale-lock.md",
    ROOT / "docs/00-project/RULES.md",
)
ALERT_TOKEN = re.compile(r"`(BioETL[A-Za-z0-9]+)`")


def load_alert_names(rules_text: str) -> set[str]:
    """Return alert identifiers declared in a Prometheus rules document."""
    payload = yaml.safe_load(rules_text)
    names: set[str] = set()
    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            alert_name = rule.get("alert")
            if isinstance(alert_name, str):
                names.add(alert_name)
    return names


def unknown_alert_names(doc_text: str, known: set[str]) -> list[str]:
    """Return backtick alert tokens that are not declared rules."""
    return sorted({name for name in ALERT_TOKEN.findall(doc_text) if name not in known})


def gold_procedure_contradictions(section: str) -> list[str]:
    """Return wording that again treats schema drift as the Gold failure."""
    errors: list[str] = []
    if "GoldContractValidationError" not in section:
        errors.append("missing GoldContractValidationError")
    if "It is not the exception" not in section:
        errors.append("ValidationResult is not distinguished from the exception")
    if "is not a" not in section or "runtime type" not in section:
        errors.append("SchemaValidationError is not marked as a non-runtime name")
    if "schema-violations" in section or "new field or type change" in section:
        errors.append("schema-drift action returned")
    if "Pipeline fails with" in section and "SchemaValidationError" in section:
        errors.append("SchemaValidationError presented as the failure")
    if 'stage="gold"' not in section or 'stage="threshold"' not in section:
        errors.append("stage labels are not both stated")
    return errors


def _gold_section(text: str) -> str:
    start = text.index("### 3. Schema Mismatch (Gold Layer)")
    end = text.index("### 4. Lock Timeout")
    return text[start:end]


def test_operator_docs_use_only_real_alertnames() -> None:
    """Backtick BioETL tokens in the three operator docs are declared alerts."""
    known = load_alert_names(RULES_PATH.read_text(encoding="utf-8"))
    unknown = {
        path.relative_to(ROOT).as_posix(): unknown_alert_names(
            path.read_text(encoding="utf-8"),
            known,
        )
        for path in OPERATOR_DOCS
    }
    offenders = {path: names for path, names in unknown.items() if names}
    assert not offenders, offenders


def test_gold_procedure_distinguishes_exception_from_validation_result() -> None:
    """The Gold section names the thrown error and the returned result apart."""
    text = OPERATOR_DOCS[0].read_text(encoding="utf-8")
    assert gold_procedure_contradictions(_gold_section(text)) == []


def test_lock_instructions_do_not_name_a_fictional_alert() -> None:
    """Lock expiry is described without the absent alert name."""
    known = load_alert_names(RULES_PATH.read_text(encoding="utf-8"))
    assert "Lock expired" not in known
    for path in OPERATOR_DOCS:
        text = path.read_text(encoding="utf-8")
        assert "Lock expired" not in text, path.relative_to(ROOT).as_posix()
    incident = OPERATOR_DOCS[0].read_text(encoding="utf-8")
    stale = OPERATOR_DOCS[1].read_text(encoding="utf-8")
    assert "Failed to acquire lock" in incident
    assert "Failed to acquire lock" in stale
    assert "LockAcquisitionError" in incident
    assert "LockLostError" in stale


def test_stale_lock_docs_describe_retention_without_lease_renewal() -> None:
    """The TTL sweep retains a held entry without extending its deadline."""
    stale = OPERATOR_DOCS[1].read_text(encoding="utf-8")
    assert "is renewed" not in stale
    assert "does not extend `expires_at`" in stale


def test_unknown_alert_name_is_rejected() -> None:
    """A fictional backtick alertname fails the name check."""
    known = load_alert_names(RULES_PATH.read_text(encoding="utf-8"))
    sample = "See `BioETLInventedAlertNotInRules` before acting."
    assert unknown_alert_names(sample, known) == ["BioETLInventedAlertNotInRules"]


def test_contradictory_gold_symptom_is_rejected() -> None:
    """The retired symptom sentence is reported as a contradiction."""
    sample = (
        "### 3. Schema Mismatch (Gold Layer)\n"
        "Pipeline fails with `schema-violations > 0` and `SchemaValidationError`.\n"
        "Inspect the raw data to identify the new field or type change.\n"
    )
    errors = gold_procedure_contradictions(sample)
    assert "schema-drift action returned" in errors
    assert "SchemaValidationError presented as the failure" in errors
    assert "missing GoldContractValidationError" in errors
