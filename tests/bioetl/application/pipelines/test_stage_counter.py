"""Unit tests for StageCounter component."""

import pytest

from bioetl.application.pipelines.stage_counter import StageCounter


@pytest.mark.unit
def test_stage_counter_initializes_empty():
    """Test that counter starts with no counts."""
    counter = StageCounter()

    assert counter.get_count("extract") == 0
    assert counter.get_chunks("extract") == 0
    assert counter.get_counts() == {}
    assert counter.get_all_chunks() == {}


@pytest.mark.unit
def test_stage_counter_increments_records():
    """Test incrementing record counts."""
    counter = StageCounter()

    counter.increment("extract", 10)
    counter.increment("extract", 5)

    assert counter.get_count("extract") == 15


@pytest.mark.unit
def test_stage_counter_increments_chunks():
    """Test incrementing chunk counts."""
    counter = StageCounter()

    counter.increment_chunks("extract")
    counter.increment_chunks("extract", 2)

    assert counter.get_chunks("extract") == 3


@pytest.mark.unit
def test_stage_counter_tracks_multiple_stages():
    """Test tracking counts for multiple stages independently."""
    counter = StageCounter()

    counter.increment("extract", 100)
    counter.increment("transform", 90)
    counter.increment("validate", 85)
    counter.increment_chunks("extract", 2)
    counter.increment_chunks("transform", 2)
    counter.increment_chunks("validate", 2)

    assert counter.get_counts() == {
        "extract": 100,
        "transform": 90,
        "validate": 85,
    }
    assert counter.get_all_chunks() == {
        "extract": 2,
        "transform": 2,
        "validate": 2,
    }


@pytest.mark.unit
def test_stage_counter_marks_stage_start():
    """Test recording stage start times."""
    counter = StageCounter()

    assert counter.get_stage_start("extract") is None

    counter.mark_stage_start("extract")

    start_time = counter.get_stage_start("extract")
    assert start_time is not None


@pytest.mark.unit
def test_stage_counter_reset_clears_all():
    """Test that reset clears all state."""
    counter = StageCounter()

    counter.increment("extract", 100)
    counter.increment_chunks("extract", 2)
    counter.mark_stage_start("extract")

    counter.reset()

    assert counter.get_count("extract") == 0
    assert counter.get_chunks("extract") == 0
    assert counter.get_stage_start("extract") is None
    assert counter.get_counts() == {}


@pytest.mark.unit
def test_stage_counter_makes_stage_result():
    """Test creating StageResult from counter state."""
    counter = StageCounter()

    counter.mark_stage_start("extract")
    counter.increment("extract", 100)
    counter.increment_chunks("extract", 2)

    result = counter.make_stage_result("extract")

    assert result.stage_name.value == "extract"
    assert result.success is True
    assert result.records_processed == 100
    assert result.chunks_processed == 2
    assert result.duration_sec >= 0
    assert result.errors == []


@pytest.mark.unit
def test_stage_counter_makes_failed_stage_result():
    """Test creating failed StageResult."""
    counter = StageCounter()

    counter.mark_stage_start("extract")
    counter.increment("extract", 100)

    result = counter.make_stage_result(
        "extract", success=False, errors=["Error occurred"]
    )

    assert result.stage_name.value == "extract"
    assert result.success is False
    assert result.records_processed == 0
    assert result.chunks_processed == 0
    assert result.errors == ["Error occurred"]


@pytest.mark.unit
def test_stage_counter_makes_result_with_override():
    """Test creating StageResult with overridden counts."""
    counter = StageCounter()

    counter.mark_stage_start("extract")
    counter.increment("extract", 100)
    counter.increment_chunks("extract", 2)

    result = counter.make_stage_result("extract", override_count=50, override_chunks=1)

    assert result.records_processed == 50
    assert result.chunks_processed == 1


@pytest.mark.unit
def test_stage_counter_duration_without_start():
    """Test that duration is 0 when start was not recorded."""
    counter = StageCounter()

    result = counter.make_stage_result("extract")

    assert result.duration_sec == 0.0
