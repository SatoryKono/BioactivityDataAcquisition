"""Cache age is checked at the use site, including partial reuse."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.repo import scoped_checks as checks

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize("corrupt", [False, True])
def test_cache_invalidates_during_fresh_checks(tmp_path, monkeypatch, partial, corrupt):
    state = {"base_sha": "a" * 40}
    clock = [941.0]
    first = checks.Check("static-first", ("fixture", "first"), cacheable=True)
    last = checks.Check("static-last", ("fixture", "last"), cacheable=True)
    fresh = checks.Check("fresh", ("fixture", "fresh"))
    selected = [first, fresh, last] if partial else [last]
    static = [check for check in selected if check.cacheable]
    directory = tmp_path / "receipts"
    monkeypatch.setattr(checks.receipts, "receipt_directory", lambda *args: directory)
    monkeypatch.setattr(checks.receipts.time, "time", lambda: clock[0])
    cache = checks.receipts.write_receipt(
        tmp_path, state, [checks._row(check, "PASS", 0, 1) for check in static]
    )
    clock[0] = 1000.0  # Initially eligible, with one second remaining.
    monkeypatch.setattr(
        checks,
        "stable_plan",
        lambda *args: (
            {"unknown": [], "checks": selected, "base_sha": "a" * 40},
            state,
        ),
    )
    monkeypatch.setattr(checks, "resolve_revision", lambda *args: "a" * 40)
    monkeypatch.setattr(checks.receipts, "snapshot", lambda *args, **kwargs: state)
    monkeypatch.setattr(
        checks,
        "_core_checks",
        lambda *args: [checks.Check("tree", ("fixture", "tree"))],
    )
    executed = []

    def execute(check, *args):
        executed.append(check.id)
        if check.id == ("fresh" if partial else "tree"):
            if corrupt:
                cache.write_text("corrupt cache")
            else:
                clock[0] += 3  # Mandatory work crosses the original TTL.
        return checks._row(check, "PASS", 0, 1)

    monkeypatch.setattr(checks, "_execute", execute)
    if corrupt:
        with pytest.raises(ValueError, match="cache receipt changed"):
            checks.validate(tmp_path, reuse=cache)
        assert "static-last" not in executed
        assert list(directory.glob("*.json")) == [cache]
        return
    result = checks.validate(tmp_path, reuse=cache)
    assert result["status"] == "PASS"
    assert "static-last" in executed
    assert (
        next(row for row in result["checks"] if row["id"] == "static-last")["reused"]
        is False
    )
    assert json.loads(cache.read_text())["created_at_unix"] == 941
    if partial:
        assert "static-first" not in executed
        assert result["cache"] == "HIT"
        assert result["cache_receipt"] == str(cache)  # Never renew a borrowed result.
    else:
        assert result["cache"] == "MISS"
        assert result["cache_receipt"] != str(cache)
        assert (
            json.loads(Path(result["cache_receipt"]).read_text())["created_at_unix"]
            == 1003
        )
