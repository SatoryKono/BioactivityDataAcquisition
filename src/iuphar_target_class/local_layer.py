"""Local layer. It does not write IUPHAR fields and does not call the network."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .models import Diagnostic, EcNumber, LocalInference
from .policy import WORKING_CLASSES, RuleRecord, validate_rules

_FORBIDDEN_TEXT = ("kinase", "channel", "zinc finger")


@dataclass(frozen=True, slots=True)
class Prediction:
    """One predicted label. Unknown provenance cannot support a class."""

    layer: str
    predicted_class: str | None
    provenance_known: bool
    derived_from_iuphar: bool
    evidence_id: str


@dataclass(frozen=True, slots=True)
class _Support:
    class_name: str
    rule_id: str
    evidence_id: str


@dataclass(frozen=True, slots=True)
class EcInference:
    """EC categories. Names are IUBMB categories, not IUPHAR classes."""

    numbers: tuple[EcNumber, ...]
    ec_categories: tuple[str, ...]
    confirmed_levels: tuple[str, ...]
    multiple_ec_categories: bool
    diagnostics: tuple[Diagnostic, ...]
    support: tuple[_Support, ...]


def validate_local_config(rules: tuple[RuleRecord, ...]) -> None:
    """Reject a broken rule before any row is processed."""
    validate_rules(rules)
    for rule in rules:
        if (
            rule.family in {"ec_class", "annotation"}
            and rule.output not in WORKING_CLASSES
        ):
            message = f"rule {rule.rule_id} output is outside the class dictionary"
            raise ValueError(message)


def infer_from_ec(
    numbers: tuple[EcNumber, ...],
    rules: tuple[RuleRecord, ...],
    *,
    organism: str | None = None,
) -> EcInference:
    """Keep every confirmed EC level. Category 7 stays Translocases."""
    validate_local_config(rules)
    diagnostics: list[Diagnostic] = []
    if organism is not None:
        diagnostics.append(
            Diagnostic(
                "organism_not_a_class_filter",
                "info",
                "organism does not add or remove an EC category",
            )
        )
    names: dict[int, str] = {}
    levels: set[str] = set()
    support: list[_Support] = []
    for number in numbers:
        if not number.valid or number.depth is None or not number.confirmed_levels:
            diagnostics.append(
                Diagnostic(
                    "invalid_ec",
                    "warning",
                    number.diagnostic or "EC is invalid",
                    evidence_id=f"ec:{number.raw}",
                )
            )
            continue
        top = int(number.confirmed_levels[0])
        if number.category_name:
            names[top] = number.category_name
        levels.update(number.confirmed_levels)
        support.extend(_ec_class_support(top, rules, number.raw))
    categories = tuple(names[key] for key in sorted(names))
    return EcInference(
        numbers=numbers,
        ec_categories=categories,
        confirmed_levels=tuple(sorted(levels, key=_level_key)),
        multiple_ec_categories=len(names) > 1,
        diagnostics=tuple(diagnostics),
        support=tuple(support),
    )


def infer_from_annotations(
    keyword_ids: tuple[str, ...],
    free_text: str | None,
    rules: tuple[RuleRecord, ...],
) -> tuple[tuple[_Support, ...], tuple[str, ...], tuple[Diagnostic, ...]]:
    """Exact keyword ids can support a class. Free text never does."""
    validate_local_config(rules)
    support = [
        _Support(rule.output, rule.rule_id, f"keyword:{keyword_id}")
        for keyword_id in keyword_ids
        for rule in rules
        if rule.family == "annotation"
        and rule.input_conditions == f"keyword_id={keyword_id}"
    ]
    candidates: list[str] = []
    diagnostics: list[Diagnostic] = []
    if free_text:
        candidates.append("free_text")
        diagnostics.append(
            Diagnostic(
                "free_text_manual_review",
                "info",
                "free text is a manual-review candidate",
            )
        )
        folded = free_text.casefold()
        if any(token in folded for token in _FORBIDDEN_TEXT):
            diagnostics.append(
                Diagnostic(
                    "free_text_substring_ignored",
                    "info",
                    "kinase, channel, and zinc finger do not assign a class",
                )
            )
    return tuple(support), tuple(candidates), tuple(diagnostics)


def collect_prediction_candidates(
    predictions: tuple[Prediction, ...],
) -> tuple[tuple[_Support, ...], tuple[str, ...], tuple[Diagnostic, ...]]:
    """Predictions cannot supply the explicit rule for Other Protein Target."""
    support: list[_Support] = []
    candidates: list[str] = []
    diagnostics: list[Diagnostic] = []
    for prediction in predictions:
        if not prediction.provenance_known:
            candidates.append("candidate_only")
            diagnostics.append(
                Diagnostic(
                    "candidate_only",
                    "warning",
                    f"{prediction.layer} provenance is unknown",
                    evidence_id=prediction.evidence_id,
                )
            )
            continue
        if prediction.derived_from_iuphar:
            diagnostics.append(
                Diagnostic(
                    "dependent_prediction",
                    "warning",
                    f"{prediction.layer} is derived from the IUPHAR result",
                    evidence_id=prediction.evidence_id,
                )
            )
            continue
        if prediction.predicted_class == "Other Protein Target":
            candidates.append("candidate_only")
            diagnostics.append(
                Diagnostic(
                    "prediction_requires_explicit_rule",
                    "info",
                    "Other Protein Target prediction stays candidate-only; "
                    "a matching explicit local rule must supply support",
                    evidence_id=prediction.evidence_id,
                )
            )
            continue
        if prediction.predicted_class in WORKING_CLASSES:
            support.append(
                _Support(
                    str(prediction.predicted_class),
                    f"prediction:{prediction.layer}",
                    prediction.evidence_id,
                )
            )
    return tuple(support), tuple(candidates), tuple(diagnostics)


def apply_local(
    numbers: tuple[EcNumber, ...],
    *,
    rules: tuple[RuleRecord, ...],
    keyword_ids: tuple[str, ...] = (),
    free_text: str | None = None,
    organism: str | None = None,
    predictions: tuple[Prediction, ...] = (),
    subclass_of: Mapping[str, str] | None = None,
) -> LocalInference:
    """Combine local evidence. Conflicting supported classes stay unresolved."""
    _reject_unknown_subclass_parents(subclass_of or {})
    validate_local_config(rules)
    ec = infer_from_ec(numbers, rules, organism=organism)
    keywords, text_candidates, text_diagnostics = infer_from_annotations(
        keyword_ids,
        free_text,
        rules,
    )
    predicted, prediction_candidates, prediction_diagnostics = (
        collect_prediction_candidates(predictions)
    )
    support = ec.support + keywords + predicted
    return _assemble(
        ec,
        support,
        text_candidates + prediction_candidates,
        ec.diagnostics + text_diagnostics + prediction_diagnostics,
        subclass_of or {},
    )


def _ec_class_support(
    category: int, rules: tuple[RuleRecord, ...], raw: str
) -> tuple[_Support, ...]:
    wanted = f"ec_category={category}"
    return tuple(
        _Support(rule.output, rule.rule_id, f"ec:{raw}")
        for rule in rules
        if rule.family == "ec_class" and rule.input_conditions == wanted
    )


def _assemble(
    ec: EcInference,
    support: tuple[_Support, ...],
    candidates: tuple[str, ...],
    diagnostics: tuple[Diagnostic, ...],
    subclass_of: Mapping[str, str],
) -> LocalInference:
    classes = tuple(sorted({item.class_name for item in support}))
    resolved = _resolved_class(classes, subclass_of)
    status = "not_supported"
    local_class: str | None = None
    if resolved is not None:
        status = "supported"
        local_class = resolved
    elif classes:
        status = "conflicting"
    extra = tuple(classes) if status == "conflicting" else ()
    return LocalInference(
        local_status=status,
        local_class=local_class,
        local_subclasses=(),
        local_rule_ids=tuple(sorted({item.rule_id for item in support})),
        local_evidence_ids=tuple(sorted({item.evidence_id for item in support})),
        ec_categories=ec.ec_categories,
        multiple_ec_categories=ec.multiple_ec_categories,
        local_candidates=tuple(sorted(set(candidates) | set(extra))),
        diagnostics=diagnostics,
    )


def _reject_unknown_subclass_parents(subclass_of: Mapping[str, str]) -> None:
    """A hierarchy parent must be a working class. Evidence is not consulted."""
    for parent in subclass_of.values():
        if parent not in WORKING_CLASSES:
            message = f"subclass parent {parent} is outside the class dictionary"
            raise ValueError(message)


def _resolved_class(
    classes: tuple[str, ...], subclass_of: Mapping[str, str]
) -> str | None:
    if not classes:
        return None
    parents = {subclass_of.get(name, name) for name in classes}
    if len(parents) == 1:
        return next(iter(parents))
    return None


def _level_key(level: str) -> tuple[int, ...]:
    return tuple(int(part) for part in level.split("."))
