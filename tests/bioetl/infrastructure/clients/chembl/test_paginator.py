"""
Tests for ChemblPaginatorImpl.
"""

from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginatorImpl


def test_get_items():
    """Test extracting items from response."""
    paginator = ChemblPaginatorImpl()
    response = {"activities": [{"id": 1}, {"id": 2}], "page_meta": {}}
    items = paginator.get_items(response)
    assert len(items) == 2
    assert items[0]["id"] == 1


def test_get_next_marker_has_next():
    """Test getting next marker when pages exist."""
    paginator = ChemblPaginatorImpl()
    response = {
        "page_meta": {
            "next": "/url?offset=20&limit=20",
            "limit": 20,
            "offset": 0,
            "total_count": 100,
        }
    }
    marker = paginator.get_next_marker(response)
    assert marker == 20  # offset + limit
    assert paginator.has_more(response) is True


def test_get_next_marker_no_next():
    """Test getting next marker when no more pages."""
    paginator = ChemblPaginatorImpl()
    response = {
        "page_meta": {"next": None, "limit": 20, "offset": 80, "total_count": 100}
    }
    marker = paginator.get_next_marker(response)
    assert marker is None
    assert paginator.has_more(response) is False


def test_get_next_request_uses_next_link_relative():
    """Paginator should build absolute URL from relative next link."""
    paginator = ChemblPaginatorImpl()
    response = {
        "page_meta": {
            "next": "/api/data/activity?offset=20&limit=20",
            "limit": 20,
            "offset": 0,
            "total_count": 40,
        }
    }

    next_url = paginator.get_next_request(
        response, "https://example.org/api/data/activity?offset=0&limit=20"
    )

    assert next_url == "https://example.org/api/data/activity?offset=20&limit=20"


def test_get_next_request_builds_from_offset_when_no_next():
    """Paginator reconstructs URL using updated offset when next is missing."""
    paginator = ChemblPaginatorImpl()
    response = {
        "page_meta": {
            "next": None,
            "limit": 20,
            "offset": 0,
            "total_count": 40,
        }
    }

    next_url = paginator.get_next_request(
        response, "https://example.org/api/data/activity?offset=0&limit=20&foo=bar"
    )

    assert (
        next_url == "https://example.org/api/data/activity?offset=20&limit=20&foo=bar"
    )
