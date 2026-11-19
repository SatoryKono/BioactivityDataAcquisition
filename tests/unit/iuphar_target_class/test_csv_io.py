"""Large CSV fields preserve bytes and restore the process-wide parser limit."""

from __future__ import annotations

import csv

import pytest

from iuphar_target_class.csv_io import read_csv_records

pytestmark = pytest.mark.unit


def test_large_field_is_read_without_changing_the_global_limit():
    previous = csv.field_size_limit()
    value = "x" * 200000
    headers, rows = read_csv_records(("payload\n" + value + "\n").encode())
    assert headers == ("payload",)
    assert rows == ({"payload": value},)
    assert csv.field_size_limit() == previous


@pytest.mark.parametrize("content", [b'payload\n"' + b"x" * 200000, b"\xff"])
def test_invalid_content_restores_the_global_limit(content):
    previous = csv.field_size_limit()
    with pytest.raises((csv.Error, UnicodeDecodeError)):
        read_csv_records(content)
    assert csv.field_size_limit() == previous


def test_existing_larger_limit_is_not_lowered(monkeypatch):
    real_limit = csv.field_size_limit
    previous = real_limit()
    observed = []

    def record_limit(value=None):
        if value is None:
            return real_limit()
        observed.append(value)
        return real_limit(value)

    monkeypatch.setattr(csv, "field_size_limit", record_limit)
    assert read_csv_records(b"key\nvalue\n")[1] == ({"key": "value"},)
    assert observed == [max(previous, len(b"key\nvalue\n")), previous]
